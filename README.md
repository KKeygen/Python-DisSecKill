# DisSecKill — 分布式商品库存与秒杀系统

基于 Python 的分布式微服务架构秒杀系统。

## 技术栈

| 层次    | 技术                                      |
|---------|-------------------------------------------|
| 语言    | Python 3.11+                              |
| 框架    | FastAPI + Uvicorn                         |
| ORM     | SQLAlchemy 2.0 (async)                    |
| 数据库  | MySQL 8.0                                 |
| 缓存    | Redis 7                                   |
| 消息队列| RabbitMQ 3.12                             |
| 网关    | Nginx                                     |
| 容器化  | Docker + Docker Compose                   |
| 认证    | JWT (python-jose + passlib/bcrypt)        |

## 服务架构

```
Nginx Gateway (:80)
  ├── 用户服务   (:8001)  /api/user/
  ├── 商品服务   (:8002)  /api/goods/
  ├── 订单服务   (:8003)  /api/order/
  └── 库存服务   (:8004)  /api/inventory/
```

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

详见 [docs/DESIGN.md](docs/DESIGN.md)
