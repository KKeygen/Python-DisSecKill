# 分布式商品库存与秒杀系统 — 系统设计文档

## 1. 系统架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                        客户端 (Web/App)                      │
└────────────────────────────┬────────────────────────────────┘
                             │ HTTP/HTTPS
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                   API Gateway (Nginx)                        │
│              负载均衡 / 路由转发 / 限流                        │
│         /api/user → user_service:8001                        │
│         /api/goods → goods_service:8002                      │
│         /api/order → order_service:8003                      │
│         /api/inventory → inventory_service:8004              │
└───┬──────────┬──────────┬──────────┬────────────────────────┘
    │          │          │          │
    ▼          ▼          ▼          ▼
┌────────┐┌────────┐┌────────┐┌──────────┐
│  用户  ││  商品  ││  订单  ││   库存   │
│  服务  ││  服务  ││  服务  ││   服务   │
│ :8001  ││ :8002  ││ :8003  ││  :8004   │
└───┬────┘└───┬────┘└───┬────┘└────┬─────┘
    │         │         │          │
    ▼         ▼         ▼          ▼
┌─────────────────────────────────────────────────────────────┐
│                     数据层                                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                   │
│  │  MySQL   │  │  Redis   │  │ RabbitMQ │                   │
│  │ 持久存储 │  │ 缓存/库存│  │ 消息队列 │                    │
│  │  :3306   │  │  :6379   │  │  :5672   │                   │
│  └──────────┘  └──────────┘  └──────────┘                   │
└─────────────────────────────────────────────────────────────┘
```

### 1.1 服务拆分说明

| 服务         | 职责                          | 端口 |
|--------------|-------------------------------|------|
| 用户服务     | 注册、登录、JWT认证、用户信息管理 | 8001 |
| 商品服务     | 商品CRUD、分类、搜索、详情      | 8002 |
| 订单服务     | 下单、订单查询、订单状态管理     | 8003 |
| 库存服务     | 库存查询、库存扣减、秒杀逻辑     | 8004 |

### 1.2 服务间通信

- **同步调用**: 服务间通过 HTTP REST 调用（如订单服务调用库存服务扣减库存）
- **异步通信**: 通过 RabbitMQ 消息队列处理秒杀订单异步下单
- **数据缓存**: Redis 缓存热点商品信息和库存预扣减

---

## 2. 各服务 API 接口定义（RESTful）

### 2.1 用户服务 (User Service) — `/api/user`

| 方法   | 路径                | 说明           | 请求体                                          | 响应                              |
|--------|---------------------|----------------|------------------------------------------------|-----------------------------------|
| POST   | `/register`         | 用户注册       | `{username, password, email}`                  | `{id, username, email}`           |
| POST   | `/login`            | 用户登录       | `{username, password}`                         | `{access_token, token_type}`      |
| GET    | `/profile`          | 获取用户信息   | Header: `Authorization: Bearer <token>`         | `{id, username, email, ...}`      |
| PUT    | `/profile`          | 更新用户信息   | `{email?, phone?}`                             | `{id, username, email, ...}`      |

### 2.2 商品服务 (Goods Service) — `/api/goods`

| 方法   | 路径                | 说明           | 请求体/参数                                     | 响应                              |
|--------|---------------------|----------------|------------------------------------------------|-----------------------------------|
| GET    | `/`                 | 商品列表       | `?page=1&size=20&category_id=`                 | `{items: [...], total, page}`     |
| GET    | `/{goods_id}`       | 商品详情       | -                                              | `{id, name, price, stock, ...}`   |
| POST   | `/`                 | 创建商品(管理) | `{name, desc, price, category_id, stock}`      | `{id, name, ...}`                 |
| PUT    | `/{goods_id}`       | 更新商品(管理) | `{name?, desc?, price?}`                       | `{id, name, ...}`                 |
| DELETE | `/{goods_id}`       | 删除商品(管理) | -                                              | `{message}`                       |
| GET    | `/categories`       | 商品分类列表   | -                                              | `[{id, name}, ...]`               |

### 2.3 订单服务 (Order Service) — `/api/order`

| 方法   | 路径                | 说明           | 请求体/参数                                     | 响应                              |
|--------|---------------------|----------------|------------------------------------------------|-----------------------------------|
| POST   | `/`                 | 创建订单       | `{goods_id, count, address_id}`                | `{order_id, status, ...}`         |
| GET    | `/`                 | 订单列表       | `?page=1&size=10&status=`                      | `{items: [...], total}`           |
| GET    | `/{order_id}`       | 订单详情       | -                                              | `{order_id, goods, status, ...}`  |
| PUT    | `/{order_id}/pay`   | 订单支付       | `{pay_method}`                                 | `{order_id, status}`              |
| PUT    | `/{order_id}/cancel`| 取消订单       | -                                              | `{order_id, status}`              |

### 2.4 库存服务 (Inventory Service) — `/api/inventory`

| 方法   | 路径                      | 说明           | 请求体/参数                              | 响应                              |
|--------|---------------------------|----------------|----------------------------------------|-----------------------------------|
| GET    | `/{goods_id}`             | 查询库存       | -                                      | `{goods_id, stock}`               |
| POST   | `/deduct`                 | 扣减库存       | `{goods_id, count}`                    | `{success, remaining}`            |
| POST   | `/revert`                 | 回滚库存       | `{goods_id, count}`                    | `{success, remaining}`            |
| POST   | `/seckill`                | 秒杀抢购       | `{goods_id, user_id}`                  | `{success, order_id/message}`     |
| POST   | `/init/{goods_id}`        | 初始化秒杀库存 | `{stock}`                              | `{success}`                       |

---

## 3. 数据库 ER 图

```
┌──────────────────────┐       ┌──────────────────────────┐
│       df_user        │       │      df_goods_category   │
├──────────────────────┤       ├──────────────────────────┤
│ PK id         BIGINT │       │ PK id           BIGINT   │
│    username   VARCHAR│       │    name         VARCHAR   │
│    password   VARCHAR│       │    description  TEXT      │
│    email      VARCHAR│       │    sort_order   INT       │
│    phone      VARCHAR│       │    is_active    BOOLEAN   │
│    is_active  BOOLEAN│       │    create_time  DATETIME  │
│    is_admin   BOOLEAN│       │    update_time  DATETIME  │
│    create_time DATETIME      │                          │
│    update_time DATETIME      └──────────┬───────────────┘
└──────────┬───────────┘                  │
           │                              │ 1:N
           │ 1:N                          │
           ▼                              ▼
┌──────────────────────────────────────────────────────┐
│                     df_goods                          │
├──────────────────────────────────────────────────────┤
│ PK id              BIGINT                             │
│ FK category_id     BIGINT  → df_goods_category.id     │
│    name            VARCHAR                            │
│    desc            TEXT                                │
│    price           DECIMAL(10,2)                      │
│    unit            VARCHAR                            │
│    image           VARCHAR                            │
│    is_seckill      BOOLEAN                            │
│    seckill_price   DECIMAL(10,2)                      │
│    seckill_start   DATETIME                           │
│    seckill_end     DATETIME                           │
│    status          SMALLINT  (0:下架 1:上架)            │
│    create_time     DATETIME                           │
│    update_time     DATETIME                           │
└──────────┬───────────────────────────────────────────┘
           │ 1:1
           ▼
┌──────────────────────────────────────────────────────┐
│                   df_inventory                        │
├──────────────────────────────────────────────────────┤
│ PK id              BIGINT                             │
│ FK goods_id        BIGINT  → df_goods.id (UNIQUE)     │
│    stock           INT                                │
│    locked_stock    INT   (已锁定待支付)                  │
│    version         INT   (乐观锁版本号)                  │
│    create_time     DATETIME                           │
│    update_time     DATETIME                           │
└──────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│                   df_order                            │
├──────────────────────────────────────────────────────┤
│ PK id              VARCHAR(32) (订单号)                │
│ FK user_id         BIGINT  → df_user.id               │
│ FK goods_id        BIGINT  → df_goods.id              │
│    count           INT                                │
│    total_price     DECIMAL(10,2)                      │
│    pay_method      SMALLINT                           │
│    order_status    SMALLINT (1待支付 2待发货 3已完成...)  │
│    address         VARCHAR                            │
│    trade_no        VARCHAR                            │
│    is_seckill      BOOLEAN                            │
│    create_time     DATETIME                           │
│    update_time     DATETIME                           │
└──────────────────────────────────────────────────────┘
```

### 3.1 表关系说明

- **df_user ↔ df_order**: 一对多，一个用户可有多个订单
- **df_goods_category ↔ df_goods**: 一对多，一个分类下有多个商品
- **df_goods ↔ df_inventory**: 一对一，每个商品对应一条库存记录
- **df_goods ↔ df_order**: 一对多，一个商品可出现在多个订单中

---

## 4. 技术栈选型说明

### 4.1 编程语言与框架

| 组件          | 选型           | 理由                                                        |
|---------------|----------------|-------------------------------------------------------------|
| 编程语言      | **Python 3.11+** | 团队技术栈要求，生态丰富                                     |
| Web框架       | **FastAPI**      | 异步高性能、自动OpenAPI文档、类型提示、适合微服务              |
| ORM           | **SQLAlchemy 2.0**| 成熟稳定，支持异步（async），与FastAPI配合良好                 |
| 数据校验      | **Pydantic v2**  | FastAPI内置支持，类型安全                                     |

### 4.2 中间件

| 组件          | 选型           | 理由                                                        |
|---------------|----------------|-------------------------------------------------------------|
| 关系数据库    | **MySQL 8.0**    | 成熟稳定，适合事务性业务数据                                  |
| 缓存/库存     | **Redis 7**      | 高性能内存存储，Lua脚本原子扣减库存，支持分布式锁              |
| 消息队列      | **RabbitMQ 3.12** | 可靠消息投递，支持死信队列处理超时订单                         |
| API网关       | **Nginx**        | 反向代理、负载均衡、限流                                      |

### 4.3 基础设施

| 组件          | 选型           | 理由                                                        |
|---------------|----------------|-------------------------------------------------------------|
| 容器化        | **Docker + Docker Compose** | 标准化部署，环境一致性                              |
| 认证方式      | **JWT (jose)**   | 无状态认证，适合分布式服务                                    |
| 异步驱动      | **asyncio + uvicorn** | 充分利用Python协程处理高并发                            |
| DB驱动        | **aiomysql**     | MySQL异步驱动，配合SQLAlchemy async                           |

### 4.4 秒杀核心方案

> **详细设计见 [SECKILL_DESIGN.md](./SECKILL_DESIGN.md)**

1. **Redis预扣库存**: 秒杀开始前将库存加载到Redis，使用Lua脚本原子扣减
2. **RabbitMQ异步下单**: 扣减成功后发送消息到队列，订单服务异步消费创建订单
3. **乐观锁兜底**: 数据库层面使用version字段进行乐观锁校验，防止超卖
4. **限流防刷**: Nginx层面限制请求频率，服务层面校验用户重复秒杀
5. **本地售罄标记**: 库存耗尽后进程内缓存拒绝，不再访问Redis
6. **幂等去重**: 全链路 request_id + df_seckill_processed 表防止重复消费
7. **Saga补偿**: MQ/DB失败时自动回滚Redis库存

---

## 5. 项目目录结构

```
Python-DisSecKill/
├── docs/                        # 文档
│   └── DESIGN.md
├── docker-compose.yml           # 容器编排
├── .env.example                 # 环境变量模板
├── gateway/                     # API网关
│   └── nginx.conf
├── services/                    # 微服务
│   ├── user_service/            # 用户服务
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── app/
│   │       ├── main.py          # 入口
│   │       ├── config.py        # 配置
│   │       ├── database.py      # 数据库连接
│   │       ├── models.py        # ORM模型
│   │       ├── schemas.py       # Pydantic模型
│   │       └── routers/
│   │           └── auth.py      # 认证路由
│   ├── goods_service/           # 商品服务
│   ├── order_service/           # 订单服务
│   └── inventory_service/       # 库存服务
└── scripts/                     # 工具脚本
    └── init_db.sql              # 数据库初始化
```
