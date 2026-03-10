"""Initialize test data for seckill testing"""
import urllib.request
import json

HOST = "http://localhost"

def post(url, data):
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    resp = urllib.request.urlopen(req, timeout=10)
    return json.loads(resp.read().decode())


# 1. Create test goods
print("Creating test goods...")
goods = post(f"{HOST}:8002/api/goods/", {
    "name": "Test Seckill Phone",
    "desc": "秒杀测试商品 - 限量100台",
    "price": 5999.00,
    "unit": "台",
    "category_id": 1,
    "is_seckill": True,
    "seckill_price": 3999.00,
})
goods_id = goods["id"]
print(f"  Created goods_id={goods_id}")

# 2. Insert inventory record via MySQL (through docker exec)
import subprocess
sql = f"INSERT INTO df_inventory (goods_id, stock, locked_stock, version) VALUES ({goods_id}, 100, 0, 0) ON DUPLICATE KEY UPDATE stock=100, version=0;"
print(f"Inserting inventory for goods_id={goods_id}...")
result = subprocess.run(
    ["docker", "exec", "disseckill-mysql", "mysql", "-uroot",
     "-pdisseckill_root_2026", "disseckill", "-e", sql],
    capture_output=True, text=True
)
if result.returncode == 0:
    print("  Inventory record created in DB")
else:
    print(f"  Error: {result.stderr}")

# 3. Init Redis seckill stock
print("Initializing Redis seckill stock...")
resp = post(f"{HOST}:8004/api/inventory/init/{goods_id}", {"stock": 100})
print(f"  Redis stock initialized: {resp}")

# 4. Verify
print("\nVerification:")
req = urllib.request.Request(f"{HOST}:8004/api/inventory/{goods_id}")
resp = urllib.request.urlopen(req, timeout=10)
inv = json.loads(resp.read().decode())
print(f"  DB inventory: stock={inv['stock']}")

# Quick seckill test
print("\nSingle seckill test:")
resp = post(f"{HOST}:8004/api/inventory/seckill", {"goods_id": goods_id, "user_id": 88888})
print(f"  Result: success={resp['success']}, message={resp['message']}")

print(f"\n=== Test data ready. goods_id={goods_id} ===")
