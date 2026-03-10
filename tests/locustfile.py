"""
秒杀压力测试 — Locust 脚本

使用方法:
  # 无头模式
  locust -f tests/locustfile.py --host=http://localhost --users 1000 --spawn-rate 100 --run-time 60s --headless --csv=results/seckill

  # Web UI 模式
  locust -f tests/locustfile.py --host=http://localhost

测试前准备:
  1. 确保所有服务已启动 (docker-compose up)
  2. 初始化秒杀库存:
     curl -X POST http://localhost/api/inventory/init/1 -H "Content-Type: application/json" -d '{"stock": 100}'
"""

import random

from locust import HttpUser, task, between, events


class SeckillUser(HttpUser):
    """纯秒杀压力测试用户"""

    wait_time = between(0, 0)  # 无等待，最大压力

    @task
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
    def browse_goods(self):
        self.client.get("/api/goods/?page=1&size=10")
