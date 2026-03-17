# DisSecKill — 分布式商品库存与秒杀系统

基于 Python 的分布式微服务架构秒杀系统，实现了完整的商品管理、库存管理、秒杀抢购、订单处理等功能。

![系统概览](docs/diagrams/system_overview.png)

## 技术栈

| 层次    | 技术                                      |
|---------|-------------------------------------------|
| 语言    | Python 3.11+                              |
| 框架    | FastAPI + Uvicorn                         |
| ORM     | SQLAlchemy 2.0 (async)                    |
| 数据库  | MySQL 8.0                                 |
| 缓存    | Redis 7 (Lua脚本/分布式锁/缓存三防)       |
| 消息队列| RabbitMQ 3.12 (持久化/死信队列)            |
| 网关    | Nginx (负载均衡/动静分离/限流)             |
| 前端    | Vue 3 + TypeScript + Pinia                |
| 容器化  | Docker + Docker Compose                   |
| 认证    | JWT (python-jose + passlib/bcrypt)        |
| 压测    | Locust (替代JMeter)                       |

## 系统架构

```
┌──────────── 客户端 ────────────┐
│  Vue 3 SPA / 浏览器 / 移动端   │
└──────────────┬─────────────────┘
               ▼
┌──────── Nginx 网关 (:80) ──────┐
│ 限流 | 负载均衡 | 动静分离      │
└──┬───────┬───────┬───────┬─────┘
   ▼       ▼       ▼       ▼
用户服务  商品服务  订单服务  库存服务
 x2实例   x2实例   x2实例   x2实例
 :8001    :8002    :8003    :8004
   │       │       │       │
   ▼       ▼       ▼       ▼
 MySQL    Redis   RabbitMQ
 :3306    :6379    :5672
```

### 负载均衡策略

| 服务     | 算法         | 说明                              |
|----------|-------------|-----------------------------------|
| 用户服务 | 轮询(默认)   | 无状态认证，均等分配                |
| 商品服务 | 加权轮询 3:1 | 模拟异构节点性能差异                |
| 订单服务 | 最少连接     | 订单处理耗时不均匀                  |
| 库存服务 | IP Hash      | 利用本地sold_out_map缓存            |

### 秒杀核心：五层防超卖

```
1. Nginx限流 → 2. 本地内存标记 → 3. Redis Lua原子扣减
   → 4. RabbitMQ异步削峰 → 5. MySQL乐观锁兜底
```

### 分布式缓存三防

| 问题     | 方案                                    |
|----------|----------------------------------------|
| 缓存穿透 | 空值缓存(TTL=60s)                       |
| 缓存击穿 | Redis SETNX 分布式互斥锁                |
| 缓存雪崩 | TTL随机偏移(±30s)                       |

## 快速启动

```bash
# 1. 复制环境变量配置
cp .env.example .env

# 2. 启动所有服务
docker-compose up -d --build

# 3. 查看服务状态
docker-compose ps

# 4. 访问 API 文档
# 用户服务: http://localhost:8001/docs
# 商品服务: http://localhost:8002/docs
# 订单服务: http://localhost:8003/docs
# 库存服务: http://localhost:8004/docs
# RabbitMQ 管理: http://localhost:15672
```

## 本地开发（不使用 Docker）

```bash
# 确保 MySQL、Redis、RabbitMQ 已在本地运行

# 安装依赖（以用户服务为例）
cd services/user_service
pip install -r requirements.txt

# 启动服务
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

## API 速览

### 用户注册
```bash
curl -X POST http://localhost:8001/api/user/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"123456","email":"test@example.com"}'
```

### 用户登录
```bash
curl -X POST http://localhost:8001/api/user/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"123456"}'
```

### 获取用户信息
```bash
curl http://localhost:8001/api/user/profile \
  -H "Authorization: Bearer <your_token>"
```

## 目录结构

```
├── docs/                        # 设计文档
│   └── DESIGN.md
├── docker-compose.yml           # 容器编排
├── gateway/                     # Nginx 网关配置
│   └── nginx.conf
├── scripts/                     # 工具脚本
│   └── init_db.sql              # 数据库初始化
├── services/
│   ├── user_service/            # 用户服务
│   ├── goods_service/           # 商品服务
│   ├── order_service/           # 订单服务
│   └── inventory_service/       # 库存服务
└── .env.example                 # 环境变量模板
```

## 设计文档

详见 [docs/DESIGN.md](docs/DESIGN.md) | [docs/SECKILL_DESIGN.md](docs/SECKILL_DESIGN.md)

## 压力测试

推荐使用 k6（现代化、低资源开销、结果结构化），Locust 保留用于复杂用户行为建模。

### k6 秒杀压测（推荐）

```bash
# 一键运行（自动初始化库存 + 执行压测 + 导出 summary json）
powershell -ExecutionPolicy Bypass -File tests/run_k6.ps1 \
  -K6BaseUrl http://host.docker.internal \
  -GoodsId 1 \
  -Stock 100 \
  -Profile smoke \
  -OutPrefix results/k6_seckill_latest

# 结果文件
# results/k6_seckill_latest.json
```

使用 Locust (Python版压力测试工具) 替代 JMeter：

```bash
# 安装 Locust
pip install locust

# 秒杀场景（1000并发，每秒100增长）
locust -f tests/locustfile.py SeckillUser --host=http://localhost \
  --users 1000 --spawn-rate 100 --run-time 60s --headless

# 静态资源压测（验证动静分离效果）
locust -f tests/locustfile.py StaticFileUser --host=http://localhost \
  --users 500 --spawn-rate 50 --run-time 30s --headless

# API接口压测（对比动态请求延迟）
locust -f tests/locustfile.py ApiUser --host=http://localhost \
  --users 200 --spawn-rate 20 --run-time 30s --headless

# 负载均衡验证
locust -f tests/locustfile.py LoadBalanceUser --host=http://localhost \
  --users 200 --spawn-rate 20 --run-time 60s --headless

# 检查各后端实例处理的请求数
docker logs disseckill-goods-1 2>&1 | grep -c "GET /api/goods"
docker logs disseckill-goods-2 2>&1 | grep -c "GET /api/goods"
```

### 防超卖验证

```bash
python tests/test_oversell.py --stock 100 --users 500 --host http://localhost
```
