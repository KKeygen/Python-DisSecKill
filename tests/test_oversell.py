"""
防超卖正确性验证脚本

验证逻辑:
  1. 初始化 N 件库存
  2. 发起 M >> N 个并发秒杀请求
  3. 断言成功数 == N (不超卖)
  4. 验证 Redis 库存 == 0
  5. 等待 MQ 消费后验证 DB 订单数 == N

使用方法:
  python tests/test_oversell.py [--host http://localhost] [--stock 100] [--users 10000]
"""

import argparse
import asyncio
import sys
import time

import httpx


async def run_test(host: str, stock: int, users: int):
    print(f"\n{'='*60}")
    print(f"  防超卖正确性验证")
    print(f"  Host:   {host}")
    print(f"  库存:   {stock}")
    print(f"  并发数: {users}")
    print(f"{'='*60}\n")

    # Step 1: 初始化库存
    print("[1/5] 初始化秒杀库存...")
    async with httpx.AsyncClient(timeout=10) as c:
        resp = await c.post(f"{host}/api/inventory/init/1", json={"stock": stock, "seckill_price": 99.9})
        assert resp.status_code == 200, f"初始化失败: {resp.text}"
    print(f"      库存已设置为 {stock}")

    # Step 2: 并发秒杀
    print(f"[2/5] 发起 {users} 个并发秒杀请求...")
    success_count = 0
    fail_reasons: dict[str, int] = {}
    lock = asyncio.Lock()

    semaphore = asyncio.Semaphore(200)  # 控制最大并发连接数

    async def do_seckill(uid: int):
        nonlocal success_count
        async with semaphore:
            async with httpx.AsyncClient(timeout=30) as c:
                try:
                    resp = await c.post(
                        f"{host}/api/inventory/seckill",
                        json={"goods_id": 1, "user_id": uid},
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        if data.get("success"):
                            async with lock:
                                success_count += 1
                        else:
                            msg = data.get("message", "unknown")
                            async with lock:
                                fail_reasons[msg] = fail_reasons.get(msg, 0) + 1
                    else:
                        msg = f"HTTP {resp.status_code}"
                        async with lock:
                            fail_reasons[msg] = fail_reasons.get(msg, 0) + 1
                except Exception as e:
                    msg = type(e).__name__
                    async with lock:
                        fail_reasons[msg] = fail_reasons.get(msg, 0) + 1

    t0 = time.perf_counter()
    tasks = [do_seckill(i) for i in range(1, users + 1)]
    await asyncio.gather(*tasks)
    elapsed = time.perf_counter() - t0

    print(f"      完成，耗时 {elapsed:.2f}s")
    print(f"      TPS: {users / elapsed:.0f} req/s")

    # Step 3: 验证结果
    print(f"\n[3/5] 验证秒杀成功数...")
    print(f"      成功: {success_count}")
    print(f"      失败分布: {fail_reasons}")

    if success_count == stock:
        print(f"      ✅ 成功数 == 库存 ({stock})，未超卖")
    elif success_count > stock:
        print(f"      ❌ 超卖！成功数 {success_count} > 库存 {stock}")
    else:
        print(f"      ⚠️  成功数 {success_count} < 库存 {stock}，可能存在漏卖")

    # Step 4: 验证 Redis
    print(f"\n[4/5] 验证 Redis 库存...")
    try:
        import redis
        r = redis.Redis(host="localhost", port=6379, db=2, decode_responses=True)
        redis_stock = r.get("seckill:stock:1")
        redis_users = r.scard("seckill:users:1")
        print(f"      Redis 剩余库存: {redis_stock}")
        print(f"      Redis 已秒杀用户数: {redis_users}")
        if int(redis_stock or 0) == 0 and redis_users == stock:
            print(f"      ✅ Redis 数据一致")
        else:
            print(f"      ⚠️  Redis 数据可能不一致")
    except ImportError:
        print("      ⏭️  跳过（需要 redis 包: pip install redis）")
    except Exception as e:
        print(f"      ⏭️  跳过（{e}）")

    # Step 5: 等待 MQ 消费后验证（需要 DB 访问，此处仅给出提示）
    print(f"\n[5/5] 等待异步订单创建...")
    print(f"      请等待 3~5 秒后执行以下 SQL 验证:")
    print(f"      SELECT COUNT(*) FROM df_order WHERE is_seckill = 1 AND goods_id = 1;")
    print(f"      预期结果: {stock}")

    # 最终判定
    print(f"\n{'='*60}")
    if success_count == stock:
        print(f"  ✅ 测试通过：{users} 并发 / {stock} 库存 / {success_count} 成功 / 0 超卖")
    else:
        print(f"  {'❌ 超卖' if success_count > stock else '⚠️  漏卖'}：期望 {stock}，实际 {success_count}")
    print(f"{'='*60}\n")

    return success_count == stock


def main():
    parser = argparse.ArgumentParser(description="防超卖正确性验证")
    parser.add_argument("--host", default="http://localhost", help="服务地址")
    parser.add_argument("--stock", type=int, default=100, help="初始库存")
    parser.add_argument("--users", type=int, default=10000, help="并发请求数")
    args = parser.parse_args()

    passed = asyncio.run(run_test(args.host, args.stock, args.users))
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
