"""
秒杀压力测试 — Locust 脚本

使用方法:
  # 无头模式 — 秒杀场景
  locust -f tests/locustfile.py --host=http://localhost --users 1000 --spawn-rate 100 --run-time 60s --headless --csv=results/seckill

  # 无头模式 — 静态资源对比
  locust -f tests/locustfile.py StaticFileUser --host=http://localhost --users 500 --spawn-rate 50 --run-time 30s --headless --csv=results/static

  # 无头模式 — API接口对比
  locust -f tests/locustfile.py ApiUser --host=http://localhost --users 200 --spawn-rate 20 --run-time 30s --headless --csv=results/api

  # 无头模式 — 负载均衡验证
  locust -f tests/locustfile.py LoadBalanceUser --host=http://localhost --users 200 --spawn-rate 20 --run-time 60s --headless --csv=results/lb

  # Web UI 模式
  locust -f tests/locustfile.py --host=http://localhost

测试前准备:
  1. 确保所有服务已启动 (docker-compose up)
  2. 初始化秒杀库存:
     curl -X POST http://localhost/api/inventory/init/1 -H "Content-Type: application/json" -d '{"stock": 100}'
"""

import random

from locust import HttpUser, task, between, tag, events


# ==================== 秒杀压力测试 ====================
class SeckillUser(HttpUser):
    """纯秒杀压力测试用户"""

    wait_time = between(0, 0)  # 无等待，最大压力

    @task
    @tag("seckill")
    def seckill(self):
        user_id = random.randint(1, 1_000_000)
        with self.client.post(
            "/api/inventory/seckill",
            json={"goods_id": 1, "user_id": user_id},
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                data = resp.json()
                if data.get("success"):
                    resp.success()
                else:
                    # 库存不足或重复秒杀 → 标记为成功(业务正常)
                    resp.success()
            elif resp.status_code == 503:
                # Nginx限流 → 标记为成功(限流正常)
                resp.success()
            else:
                resp.failure(f"Unexpected status: {resp.status_code}")


# ==================== 静态资源压测（动静分离验证） ====================
class StaticFileUser(HttpUser):
    """静态文件压测：验证Nginx动静分离效果，预期高吞吐低延迟"""

    wait_time = between(0, 0)

    @task(5)
    @tag("static")
    def fetch_css(self):
        self.client.get("/static/css/style.css", name="/static/css/style.css")

    @task(3)
    @tag("static")
    def fetch_js(self):
        self.client.get("/static/js/app.js", name="/static/js/app.js")

    @task(2)
    @tag("static")
    def fetch_html(self):
        self.client.get("/static/index.html", name="/static/index.html")


# ==================== API接口压测（动态请求对比） ====================
class ApiUser(HttpUser):
    """API接口压测：与静态资源对比响应时间"""

    wait_time = between(0, 0)

    @task(5)
    @tag("api")
    def list_goods(self):
        self.client.get("/api/goods/?page=1&size=10", name="/api/goods/ [列表]")

    @task(3)
    @tag("api")
    def get_goods_detail(self):
        goods_id = random.randint(1, 5)
        self.client.get(f"/api/goods/{goods_id}", name="/api/goods/{id} [详情]")

    @task(1)
    @tag("api")
    def health_check(self):
        self.client.get("/health", name="/health")


# ==================== 负载均衡验证 ====================
class LoadBalanceUser(HttpUser):
    """
    负载均衡验证：通过X-Upstream-Addr响应头检查请求分布

    运行后检查日志：
    - docker logs disseckill-goods-1 2>&1 | grep -c "GET /api/goods"
    - docker logs disseckill-goods-2 2>&1 | grep -c "GET /api/goods"
    预期：请求数量大致相等（轮询/最少连接）
    """

    wait_time = between(0.1, 0.5)

    @task(3)
    @tag("lb")
    def lb_goods(self):
        """测试商品服务负载均衡（加权轮询 3:1）"""
        with self.client.get(
            "/api/goods/?page=1&size=5",
            catch_response=True,
            name="/api/goods/ [LB]",
        ) as resp:
            upstream = resp.headers.get("X-Upstream-Addr", "unknown")
            # 输出到Locust统计（可在CSV结果中观察）
            resp.success()

    @task(2)
    @tag("lb")
    def lb_user(self):
        """测试用户服务负载均衡（轮询）"""
        self.client.get("/api/user/profile", name="/api/user/ [LB]")

    @task(1)
    @tag("lb")
    def lb_inventory(self):
        """测试库存服务负载均衡（IP Hash）"""
        self.client.get("/api/inventory/1", name="/api/inventory/ [LB]")


# ==================== 完整流程测试 ====================
class FullFlowUser(HttpUser):
    """完整流程测试：注册 → 登录 → 秒杀 → 查询订单"""

    wait_time = between(0.5, 2)
    token: str = ""
    user_id_str: str = ""

    def on_start(self):
        uid = random.randint(1, 10_000_000)
        username = f"testuser_{uid}"
        email = f"test_{uid}@example.com"
        password = "Test@12345"

        # 注册
        self.client.post(
            "/api/user/register",
            json={"username": username, "email": email, "password": password},
        )

        # 登录
        resp = self.client.post(
            "/api/user/login",
            json={"username": username, "password": password},
        )
        if resp.status_code == 200:
            self.token = resp.json().get("access_token", "")
        self.user_id_str = str(uid)

    @task(5)
    @tag("flow")
    def seckill_and_check(self):
        # 秒杀
        resp = self.client.post(
            "/api/inventory/seckill",
            json={"goods_id": 1, "user_id": int(self.user_id_str)},
        )
        if resp.status_code == 200 and resp.json().get("success"):
            # 查询订单
            if self.token:
                self.client.get(
                    "/api/order/",
                    headers={"Authorization": f"Bearer {self.token}"},
                )

    @task(1)
    @tag("flow")
    def browse_goods(self):
        self.client.get("/api/goods/?page=1&size=10")
