# 秒杀流程详细设计 — 分布式实践方案

> 本文档详细描述秒杀系统的完整流程设计，基于经过生产验证的分布式/微服务实践，  
> 涵盖从请求入口到订单落库的全链路，以及性能测试方法和预期结果。

---

## 目录

1. [秒杀业务流程总览](#1-秒杀业务流程总览)
2. [分层架构与职责划分](#2-分层架构与职责划分)
3. [秒杀全链路时序图](#3-秒杀全链路时序图)
4. [各层详细设计](#4-各层详细设计)
5. [关键分布式模式](#5-关键分布式模式)
6. [数据一致性保障](#6-数据一致性保障)
7. [容错与降级策略](#7-容错与降级策略)
8. [性能测试方案](#8-性能测试方案)
9. [测试结果预期分析](#9-测试结果预期分析)

---

## 1. 秒杀业务流程总览

秒杀系统的核心挑战：**瞬时高并发（写热点）、严格防超卖、用户体验流畅**。

完整生命周期划分为三个阶段：

```
  ┌─────────────┐      ┌──────────────┐      ┌─────────────┐
  │   预热阶段   │ ───▷ │   秒杀进行   │ ───▷ │  后处理阶段  │
  │  (T-30min)  │      │ (T ~ T+Δ)   │      │ (T+Δ ~ ...)  │
  └─────────────┘      └──────────────┘      └─────────────┘
```

| 阶段 | 时间点 | 核心操作 |
|------|--------|----------|
| **预热** | 秒杀开始前30分钟 | 库存加载到Redis、页面静态化、CDN预热 |
| **进行** | 秒杀开始 ~ 库存耗尽 | Nginx限流 → Redis Lua扣减 → MQ投递 → 异步落单 |
| **后处理** | 秒杀结束后 | 超时未支付订单回滚、Redis与DB库存对账 |

---

## 2. 分层架构与职责划分

```
┌────────────────────────────────────────────────────────────────────┐
│ 第1层：接入层 (Nginx Gateway)                                       │
│ ● 静态资源缓存（秒杀页HTML/JS/CSS）                                  │
│ ● IP级限流（令牌桶: 50 req/s per IP）                                │
│ ● 黑名单拦截（封禁异常IP）                                           │
│ ● 请求路由到库存服务                                                 │
├────────────────────────────────────────────────────────────────────┤
│ 第2层：应用层 (Inventory Service)                                   │
│ ● 本地内存标记（sold_out_map）快速拒绝                               │
│ ● Redis Lua原子操作（扣减库存 + 用户去重）                            │
│ ● 成功后投递MQ消息                                                   │
│ ● 返回排队结果给用户                                                 │
├────────────────────────────────────────────────────────────────────┤
│ 第3层：消息层 (RabbitMQ)                                            │
│ ● seckill_order_queue 接收秒杀消息                                  │
│ ● 消息持久化 + 手动ACK确保不丢                                       │
│ ● 死信队列(DLQ)处理失败消息                                          │
├────────────────────────────────────────────────────────────────────┤
│ 第4层：订单处理层 (Order Consumer)                                   │
│ ● 消费MQ消息，创建订单                                               │
│ ● MySQL乐观锁二次扣减（防超卖兜底）                                   │
│ ● 写入df_order (is_seckill=True, order_status=1)                   │
│ ● 失败时回滚Redis库存                                                │
├────────────────────────────────────────────────────────────────────┤
│ 第5层：数据层 (MySQL + Redis)                                       │
│ ● MySQL: 持久化库存、订单（单点事实来源）                              │
│ ● Redis: 秒杀库存预扣减 + 用户去重Set + 结果缓存                     │
└────────────────────────────────────────────────────────────────────┘
```

---

## 3. 秒杀全链路时序图

```
 用户          Nginx         库存服务(App)        Redis           RabbitMQ        订单消费者         MySQL
  │              │               │                 │                │               │                │
  │──POST /seckill──▶│           │                 │                │               │                │
  │              │──限流检查──▶   │                 │                │               │                │
  │              │   (通过)       │                 │                │               │                │
  │              │───proxy───▶   │                 │                │               │                │
  │              │               │                 │                │               │                │
  │              │               │──sold_out?──┐   │                │               │                │
  │              │               │ (本地内存判断) │   │                │               │                │
  │              │               │◀─ No ───────┘   │                │               │                │
  │              │               │                 │                │               │                │
  │              │               │──EVAL Lua──────▶│                │               │                │
  │              │               │                 │── SISMEMBER    │               │                │
  │              │               │                 │── GET stock    │               │                │
  │              │               │                 │── DECR stock   │               │                │
  │              │               │                 │── SADD user    │               │                │
  │              │               │◀── result=1 ────│                │               │                │
  │              │               │                 │                │               │                │
  │              │               │──publish msg──────────────────▶  │               │                │
  │              │               │   {user_id, goods_id, ts}        │               │                │
  │              │               │                 │                │               │                │
  │◀── 200 "秒杀成功,订单创建中" ─│                 │                │               │                │
  │              │               │                 │                │               │                │
  │              │               │                 │                │──consume──▶   │                │
  │              │               │                 │                │               │──BEGIN TX──▶   │
  │              │               │                 │                │               │ SELECT...FOR UPDATE
  │              │               │                 │                │               │ UPDATE stock   │
  │              │               │                 │                │               │ INSERT order   │
  │              │               │                 │                │               │──COMMIT──────▶ │
  │              │               │                 │                │◀── ACK ───────│                │
  │              │               │                 │                │               │                │
  │──GET /order/result?──▶       │                 │                │               │                │
  │◀── {order_id, status} ───────│                 │                │               │                │
```

---

## 4. 各层详细设计

### 4.1 预热阶段

秒杀活动开始前，管理员调用初始化接口：

```
POST /api/inventory/init/{goods_id}
Body: { "stock": 100 }
```

**操作内容：**

| 步骤 | Redis 操作 | 说明 |
|------|-----------|------|
| 1 | `SET seckill:stock:{goods_id} 100` | 库存写入Redis |
| 2 | `DEL seckill:users:{goods_id}` | 清空去重集合 |
| 3 | `SET seckill:info:{goods_id} {json}` | 缓存商品信息(名称/价格)，减少DB查询 |
| 4 | 应用层清除 `sold_out_map[goods_id]` | 重置本地失败标记 |

### 4.2 接入层（Nginx）

```nginx
# 令牌桶限流：每IP每秒50请求，突发允许10个
limit_req_zone $binary_remote_addr zone=seckill_limit:10m rate=50r/s;

location /api/inventory/seckill {
    limit_req zone=seckill_limit burst=10 nodelay;
    proxy_pass http://inventory_service;
    # 超时快速失败
    proxy_connect_timeout 3s;
    proxy_read_timeout 5s;
}
```

**限流策略分析：**
- `rate=50r/s` → 每20ms 放行1个请求 (令牌桶)
- `burst=10` → 最多10个请求排队
- `nodelay` → 超出burst的请求立即返回503
- 10万并发用户，每个IP 50r/s，绝大部分在此层被拦截

### 4.3 应用层（库存服务）

#### 4.3.1 本地内存标记（快速拒绝）

```python
# 进程级内存标记：商品ID → 是否售罄
sold_out_map: dict[int, bool] = {}

async def seckill(req: SeckillRequest):
    # 第1关：本地内存快速拒绝
    if sold_out_map.get(req.goods_id, False):
        return SeckillResponse(success=False, message="库存不足，秒杀结束")
    
    # 第2关：Redis Lua原子操作
    result = await redis.eval(LUA_SCRIPT, ...)
    
    if result == 0:  # 库存耗尽
        sold_out_map[req.goods_id] = True  # 标记售罄，后续请求不再访问Redis
    ...
```

**设计依据：** 秒杀库存通常在秒级耗尽，耗尽后大量请求仍会涌入。本地标记避免这些请求到达Redis，减少Redis压力约90%+。

#### 4.3.2 Redis Lua 原子脚本

```lua
local stock_key    = KEYS[1]           -- seckill:stock:{goods_id}
local user_set_key = KEYS[2]           -- seckill:users:{goods_id}
local user_id      = ARGV[1]

-- 步骤1: 去重检查（O(1)）
if redis.call('sismember', user_set_key, user_id) == 1 then
    return -1   -- 重复秒杀
end

-- 步骤2: 库存检查（O(1)）
local stock = tonumber(redis.call('get', stock_key) or '0')
if stock <= 0 then
    return 0    -- 库存不足
end

-- 步骤3: 原子扣减 + 记录用户
redis.call('decr', stock_key)
redis.call('sadd', user_set_key, user_id)
return 1        -- 扣减成功
```

**为什么用Lua脚本而非Redis事务(MULTI/EXEC):**

| 对比项 | Lua脚本 | MULTI/EXEC |
|--------|---------|------------|
| 原子性 | 脚本整体原子执行 | 仅保证命令按序执行，不支持中间逻辑判断 |
| 条件逻辑 | ✅ 支持 if/else | ❌ 无法根据中间结果分支 |
| 性能 | 1次网络往返 | 多次网络往返 |
| 超卖风险 | 无（原子检查+扣减） | 有（WATCH可能retry风暴） |

**时间复杂度：** GET + SISMEMBER + DECR + SADD = O(1)×4  
**Redis单线程吞吐：** 约 8~12万 ops/s（取决于硬件）

#### 4.3.3 MQ 消息投递

Redis扣减成功后，将秒杀消息发送到RabbitMQ：

```python
message = {
    "user_id": req.user_id,
    "goods_id": req.goods_id,
    "seckill_price": goods_info["seckill_price"],
    "timestamp": time.time(),
    "request_id": str(uuid.uuid4()),   # 幂等键
}
await channel.default_exchange.publish(
    aio_pika.Message(
        body=json.dumps(message).encode(),
        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,  # 持久化
        message_id=message["request_id"],                  # 幂等ID
    ),
    routing_key="seckill_order_queue",
)
```

**关键配置：**
- `delivery_mode=PERSISTENT` → 消息写入磁盘，RabbitMQ重启不丢
- `message_id` → 消费者幂等去重
- `durable=True` (队列) → 队列元数据持久化

### 4.4 消息层（RabbitMQ）

#### 队列拓扑结构

```
                          ┌─────────────────────────────┐
  inventory_service ────▶ │ seckill_exchange (direct)    │
                          │ routing_key: seckill_order   │
                          └─────────┬───────────────────┘
                                    │
                        ┌───────────▼────────────┐
                        │ seckill_order_queue    │ ← durable, prefetch=1
                        │ x-dead-letter-exchange │ → seckill_dlx
                        │ x-message-ttl: 30000   │
                        └───────────┬────────────┘
                                    │
                          order_consumer (手动ACK)
                                    │
                        ┌───────────▼────────────┐
                        │ seckill_dlq (死信队列)  │ ← 处理失败的消息
                        └────────────────────────┘
```

**设计要点：**

| 配置 | 值 | 理由 |
|------|-----|------|
| `prefetch_count` | 1 | 每次只取1条消息处理，保证顺序性和背压控制 |
| `x-message-ttl` | 30000ms | 消息在队列中最多存活30秒，超时进DLQ |
| `x-dead-letter-exchange` | seckill_dlx | 消费失败/超时的消息路由到死信队列人工排查 |
| `manual ack` | True | 只有订单成功创建后才ACK，失败时reject进DLQ |

### 4.5 订单处理层（Consumer）

消费者是一个独立的长驻进程，运行在 order_service 容器内：

```python
async def process_seckill_order(message: aio_pika.IncomingMessage):
    async with message.process(requeue=False):  # 失败不重入队列，进DLQ
        data = json.loads(message.body.decode())
        
        # 幂等检查：同一request_id只处理一次
        if await is_processed(data["request_id"]):
            return  # 静默跳过
        
        async with db_session() as db:
            # 数据库层乐观锁扣减（防超卖兜底）
            stmt = (
                update(Inventory)
                .where(
                    Inventory.goods_id == data["goods_id"],
                    Inventory.stock > 0,
                    Inventory.version == current_version,
                )
                .values(stock=Inventory.stock - 1, version=Inventory.version + 1)
            )
            result = await db.execute(stmt)
            
            if result.rowcount == 0:
                # DB库存已耗尽 → 回滚Redis
                await redis.incr(f"seckill:stock:{data['goods_id']}")
                await redis.srem(f"seckill:users:{data['goods_id']}", str(data["user_id"]))
                raise Exception("DB库存不足，已回滚Redis")
            
            # 创建订单
            order = Order(
                id=generate_order_id(),
                user_id=data["user_id"],
                goods_id=data["goods_id"],
                count=1,
                total_price=data["seckill_price"],
                is_seckill=True,
                order_status=1,  # 待支付
            )
            db.add(order)

            # 记录幂等标记
            await mark_processed(data["request_id"], order.id)
            
            await db.commit()
```

**为什么需要DB层二次扣减？**

Redis是内存数据库，存在以下风险：
1. Redis宕机重启后数据丢失（即使有AOF/RDB，也可能丢最后几个操作）
2. 极端并发下Lua脚本结果和实际库存的微小偏差
3. 运维误操作直接修改Redis Key

MySQL乐观锁作为最终一致性的保障，是**兜底层**而非主要扣减层。

### 4.6 支付超时处理

```
订单创建(status=1) ──30分钟──▶ 延迟队列/定时扫描 ──▶ 超时未支付?
                                                         │
                                    ┌────────────────────┼────────────────────┐
                                    ▼                                         ▼
                            status → 5(已取消)                          恢复库存:
                                                                  Redis INCR stock
                                                                  Redis SREM user
                                                                  MySQL stock + 1
```

**实现方式对比：**

| 方案 | 优点 | 缺点 | 本项目选择 |
|------|------|------|-----------|
| RabbitMQ延迟队列(x-delayed-message) | 精确、无轮询 | 需要插件、RQ依赖 | ✅ 首选 |
| 定时扫描DB (每60秒) | 实现简单 | 有延迟、DB压力 | 备选 |
| Redis过期事件 | 无额外组件 | 不可靠(不保证投递) | ❌ |

---

## 5. 关键分布式模式

### 5.1 幂等性保障

**场景：** 网络重试、MQ重复投递导致同一消息被消费多次。

**方案：** 全链路唯一ID + 去重表

```
┌──────────────┐     ┌──────────────────────────┐
│   request_id │ ──▶ │ df_seckill_processed     │
│ (UUID v4)    │     │ PK request_id VARCHAR(36) │
│              │     │    order_id   VARCHAR(32) │
│              │     │    created_at DATETIME     │
└──────────────┘     └──────────────────────────┘
```

消费者在处理前查询该表，存在则跳过；不存在则处理并插入。  
使用MySQL唯一键约束作为最终防线。

### 5.2 分布式一致性（最终一致性）

本系统采用 **BASE（基本可用、软状态、最终一致）** 而非 ACID 强一致：

```
Redis扣减成功  ──▶  MQ投递  ──▶  DB落单
   (快)              (保障)       (一致)
```

- **Redis → MQ 失败：** 通过补偿机制回滚Redis（INCR + SREM）
- **MQ → DB 失败：** 消息进入DLQ，人工或自动重试；同时回滚Redis
- **DB事务失败：** 回滚Redis + reject消息到DLQ

**一致性对账（定时任务，每5分钟）：**

```python
async def reconcile(goods_id: int):
    redis_stock = await redis.get(f"seckill:stock:{goods_id}")
    db_stock = (await db.execute(
        select(Inventory.stock).where(Inventory.goods_id == goods_id)
    )).scalar()
    
    if redis_stock != db_stock:
        logger.warning(f"库存不一致: Redis={redis_stock}, DB={db_stock}")
        # 以DB为准修正Redis（DB是单点事实来源）
        await redis.set(f"seckill:stock:{goods_id}", db_stock)
```

### 5.3 防超卖多重保障链

```
第1层: Nginx限流      ──▶ 过滤90%+无效请求
第2层: 本地sold_out标记 ──▶ 库存耗尽后0延迟拒绝
第3层: Redis Lua原子扣减 ──▶ 严格的原子库存扣减 + 用户去重
第4层: MQ削峰         ──▶ 异步解耦，DB不直接承受洪峰
第5层: MySQL乐观锁     ──▶ 最终一致性兜底
```

每一层都可以独立防止超卖，5层级联使超卖概率接近于零。

### 5.4 流量漏斗分析

假设: 10万用户同时点击秒杀，库存100件

```
请求总量:  100,000
    │
    ▼ Nginx限流 (50r/s/IP, ~2000不同IP)
通过约:    50,000  (假设1秒内全部到达，每IP限50)
    │
    ▼ 本地sold_out标记 (库存耗尽后生效)
到达Redis:  ~5,000  (前100个+延迟窗口内的请求)
    │
    ▼ Redis Lua扣减
成功:         100   (精确等于库存)
    │
    ▼ MQ投递
消息数:       100
    │
    ▼ DB落单
订单数:       100   (乐观锁确保不超)
```

---

## 6. 数据一致性保障

### 6.1 秒杀事务边界

秒杀不使用分布式事务（太重），而是使用 **Saga 补偿模式**：

| 步骤 | 操作 | 补偿操作 |
|------|------|----------|
| T1 | Redis扣减库存 + 记录用户 | Redis INCR + SREM |
| T2 | 投递MQ消息 | 执行T1补偿 |
| T3 | 消费消息，MySQL扣减+创建订单 | 执行T1补偿 + reject消息 |
| T4 | 用户支付 | 取消订单 + 恢复MySQL/Redis库存 |

### 6.2 Redis 数据结构设计

| Key | 类型 | 说明 | TTL |
|-----|------|------|-----|
| `seckill:stock:{goods_id}` | String | 剩余库存量 | 活动结束+1h |
| `seckill:users:{goods_id}` | Set | 已秒杀用户ID集合 | 活动结束+1h |
| `seckill:info:{goods_id}` | Hash | 商品名/价格缓存 | 活动结束+1h |
| `seckill:result:{user_id}:{goods_id}` | String | 秒杀结果(order_id) | 30min |
| `seckill:processed:{request_id}` | String | 幂等标记 | 1h |

---

## 7. 容错与降级策略

### 7.1 Redis 不可用

```
检测: 库存服务启动时 + 每次操作catch ConnectionError
降级: 回退到MySQL直接扣减（乐观锁），吞吐量下降但不影响正确性
告警: 触发运维告警，人工介入
```

### 7.2 RabbitMQ 不可用

```
检测: publish时catch AMQPConnectionError
降级: 同步调用order_service创建订单（HTTP调用）
代价: 响应时间从5ms增加到50~100ms
告警: 立即告警
```

### 7.3 MySQL 不可用

```
检测: Consumer端catch OperationalError
处理: 消息reject，进入DLQ等待MySQL恢复后重新消费
Redis库存不在此时回滚（等待人工确认或MySQL恢复后自动处理）
```

### 7.4 服务实例宕机

```
库存服务宕机:
  - Nginx health check失败 → 摘除实例
  - 本地sold_out_map丢失 → 新实例重新从Redis判断
  - 影响: 短暂503，自动恢复

消费者宕机:
  - 未ACK的消息自动requeue
  - prefetch_count=1 保证最多1条消息受影响
  - 新实例启动后继续消费
```

---

## 8. 性能测试方案

### 8.1 测试工具选型

| 工具 | 用途 | 理由 |
|------|------|------|
| **Locust** | HTTP压力测试 | Python生态、支持分布式压测、代码即配置 |
| **redis-benchmark** | Redis基准测试 | Redis自带、直接测量Lua脚本吞吐 |
| **wrk** | HTTP微基准测试(可选) | 超高性能、补充验证 |

### 8.2 测试环境规格

```
推荐最低配置:
├── 压测机:    4核/8GB, 与被测机同一局域网
├── 应用服务器: 4核/8GB, Docker部署
├── Redis:     2核/4GB (独立或同机)
├── MySQL:     2核/4GB (独立或同机)
└── RabbitMQ:  2核/4GB (独立或同机)

开发环境(本机Docker):
├── 单机 8核/16GB 或以上
└── docker-compose 全栈部署
```

### 8.3 测试场景设计

#### 场景1：Redis Lua 脚本吞吐量基准

**目的：** 测量Redis Lua脚本每秒可处理的秒杀请求数上限。

```bash
# 预置100000库存
redis-cli SET seckill:stock:1 100000
redis-cli DEL seckill:users:1

# 使用redis-benchmark模拟EVAL（近似）
redis-benchmark -n 100000 -c 100 -q EVAL "local s=tonumber(redis.call('get',KEYS[1]) or '0'); if s<=0 then return 0 end; redis.call('decr',KEYS[1]); return 1" 1 seckill:stock:1
```

**预期：** 单Redis实例约 6~10万 ops/s（依赖CPU单核性能）

#### 场景2：秒杀接口端到端吞吐量

**Locust 测试脚本：**

```python
# tests/locustfile.py
from locust import HttpUser, task, between
import random

class SeckillUser(HttpUser):
    wait_time = between(0, 0)  # 无等待，最大压力
    
    @task
    def seckill(self):
        user_id = random.randint(1, 1000000)
        self.client.post(
            "/api/inventory/seckill",
            json={"goods_id": 1, "user_id": user_id},
        )
```

**执行命令：**

```bash
# 启动Locust (无头模式)
locust -f tests/locustfile.py \
    --host=http://localhost \
    --users 1000 \
    --spawn-rate 100 \
    --run-time 60s \
    --headless \
    --csv=results/seckill_test
```

**测试参数矩阵：**

| 并发用户 | 持续时间 | 库存量 | 测试目标 |
|---------|---------|--------|---------|
| 100 | 30s | 100 | 正确性验证：恰好100个成功 |
| 500 | 60s | 1000 | 稳态吞吐量测量 |
| 1000 | 60s | 100 | 高竞争场景：99.9%应被拒绝 |
| 2000 | 120s | 500 | 峰值压力测试 |
| 5000 | 60s | 100 | 极限压力 + 限流效果验证 |

#### 场景3：订单创建端到端链路

**目的：** 验证 Redis→MQ→DB 全链路的延迟和可靠性。

```python
class FullFlowUser(HttpUser):
    wait_time = between(0.1, 0.5)
    
    def on_start(self):
        # 注册并登录获取token
        self.client.post("/api/user/register", json={...})
        resp = self.client.post("/api/user/login", json={...})
        self.token = resp.json()["access_token"]
    
    @task
    def seckill_and_check(self):
        # 秒杀
        resp = self.client.post(
            "/api/inventory/seckill",
            json={"goods_id": 1, "user_id": self.user_id},
        )
        if resp.json().get("success"):
            # 等待2秒后查询订单
            import time; time.sleep(2)
            self.client.get(
                "/api/order/",
                headers={"Authorization": f"Bearer {self.token}"},
            )
```

#### 场景4：防超卖正确性验证

**目的：** 绝对验证不发生超卖。

```python
# tests/test_oversell.py
import asyncio, httpx

async def test_no_oversell():
    """100库存，10000并发请求，最终只有100个成功"""
    # 初始化库存
    async with httpx.AsyncClient() as c:
        await c.post("http://localhost/api/inventory/init/1", json={"stock": 100})
    
    # 10000个并发秒杀请求
    success_count = 0
    async def do_seckill(uid: int):
        nonlocal success_count
        async with httpx.AsyncClient() as c:
            resp = await c.post(
                "http://localhost/api/inventory/seckill",
                json={"goods_id": 1, "user_id": uid},
            )
            if resp.json().get("success"):
                success_count += 1
    
    tasks = [do_seckill(i) for i in range(10000)]
    await asyncio.gather(*tasks)
    
    assert success_count == 100, f"超卖！成功数={success_count}"
    
    # 验证Redis库存为0
    # 验证DB库存为0
    # 验证订单数=100
```

### 8.4 监控指标采集

测试期间需要采集的指标：

| 指标 | 采集方式 | 关注阈值 |
|------|---------|---------|
| 秒杀接口TPS | Locust统计 | 目标 > 3000 |
| P50延迟 | Locust统计 | < 20ms |
| P99延迟 | Locust统计 | < 100ms |
| 失败率 | Locust统计 | < 0.1%（排除正常的库存不足） |
| Redis ops/s | redis-cli INFO | < 80%容量 |
| Redis内存 | redis-cli INFO memory | < 70%可用 |
| MySQL QPS | SHOW GLOBAL STATUS | 消费者层 < 500 |
| RabbitMQ队列深度 | Management API | < 10000 |
| CPU使用率 | docker stats | < 80% |
| 网络IO | docker stats | 不应瓶颈 |

---

## 9. 测试结果预期分析

### 9.1 单机 Docker 环境预期

基于 8核/16GB 开发机，Docker Compose 部署：

| 指标 | 预期值 | 说明 |
|------|--------|------|
| Redis Lua TPS | 60,000~80,000 | 单Redis实例，4字节操作 |
| 秒杀API TPS | 3,000~5,000 | 受Nginx/FastAPI/网络开销限制 |
| 秒杀API P50延迟 | 5~15ms | Redis + 网络 |
| 秒杀API P99延迟 | 30~80ms | 含Nginx排队 |
| MQ消费速度 | 500~1000 msg/s | 含DB写入 |
| 全链路延迟(秒杀→订单可查) | 1~3秒 | MQ投递+消费+DB写入 |
| 超卖事件 | 0 | 多层保障下不应出现 |

### 9.2 预期瓶颈分析

```
瓶颈排序(由上到下):
1. FastAPI/Uvicorn 协程调度        ← 单worker约2000~3000 TPS
   解决: 多worker (--workers=4)
   
2. Nginx ↔ 应用层网络延迟           ← Docker内部桥接网络
   解决: host网络模式(性能测试时)
   
3. Redis单线程执行                  ← ~8万ops/s上限
   解决: 6.0+ IO线程 / 分片
   
4. MySQL写入(Consumer层)            ← 单表INSERT约500~1000/s
   解决: 批量INSERT / 分表
```

### 9.3 测试报告模板

测试完成后，结果将记录为以下格式：

```markdown
## 秒杀性能测试报告

### 测试环境
- 硬件: [CPU/内存/磁盘]
- Docker版本: [version]
- 服务配置: [workers, Redis config, MySQL config]

### 测试结果

| 场景 | 并发 | 库存 | TPS | P50 | P99 | 成功数 | 失败数 | 超卖 |
|------|------|------|-----|-----|-----|--------|--------|------|
| 正确性 | 100 | 100 | ... | ... | ... | 100 | 0 | 0 |
| 基准 | 500 | 1000 | ... | ... | ... | 1000 | ... | 0 |
| 压力 | 1000 | 100 | ... | ... | ... | 100 | ... | 0 |
| 极限 | 5000 | 100 | ... | ... | ... | 100 | ... | 0 |

### 结论
- [通过/未通过] 防超卖验证
- [达标/未达标] TPS目标
- [符合/不符合] 延迟要求
- 瓶颈定位: [具体组件]
- 优化建议: [具体措施]
```

---

## 附录A：相关文件索引

| 文件 | 说明 |
|------|------|
| `services/inventory_service/app/routers/inventory.py` | 秒杀核心逻辑(Lua脚本/接口) |
| `services/order_service/app/routers/orders.py` | 订单创建逻辑 |
| `services/order_service/app/consumer.py` | MQ消费者(待实现) |
| `gateway/nginx.conf` | Nginx限流配置 |
| `tests/locustfile.py` | 压力测试脚本(待实现) |
| `tests/test_oversell.py` | 防超卖验证脚本(待实现) |
| `docker-compose.yml` | 全栈部署编排 |

## 附录B：技术选型对比备注

### 为什么不用分布式锁(Redlock)？

| 方案 | TPS | 复杂度 | 适用场景 |
|------|-----|--------|---------|
| Redis Lua原子脚本 | 8万+ | 低 | 单Key热点写入 ✅ |
| Redlock分布式锁 | 5000~8000 | 高 | 多资源互斥操作 |
| MySQL行锁(SELECT FOR UPDATE) | 800~1500 | 低 | 低并发、强一致 |

秒杀场景是**单Key热点写入**（一个商品的库存），Lua脚本是最优解。  
Redlock适合需要跨多个资源互斥的场景（如分布式定时任务），此处不适用。

### 为什么不用Kafka替代RabbitMQ？

| 对比项 | RabbitMQ | Kafka |
|--------|----------|-------|
| 延迟 | ~1ms | ~5ms |
| 消息确认 | 单条ACK ✅ | 批量offset |
| 死信处理 | 原生DLQ ✅ | 需自行实现 |
| 部署复杂度 | 单节点可用 ✅ | 需ZK/KRaft集群 |
| 适用吞吐量 | ~5万 msg/s | ~百万 msg/s |

秒杀订单量级（千~万级/活动）不需要Kafka的超高吞吐，RabbitMQ的可靠消息投递和原生DLQ更适合此场景。
