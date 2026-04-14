param(
    [string]$NacosAddr = "http://localhost:8848"
)

$ErrorActionPreference = "Stop"

$gatewayConfig = @'
{
  "routes": {
    "user": "user-service",
    "goods": "goods-service",
    "order": "order-service",
    "inventory": "inventory-service"
  },
  "governance": {
    "rate_limit_rps": 80,
    "rate_limit_burst": 40,
    "circuit_fail_threshold": 5,
    "circuit_open_seconds": 15
  },
  "timeout": {
    "connect_timeout_sec": 1.0,
    "read_timeout_sec": 3.0
  }
}
'@

$inventoryConfig = @'
{
  "default_limit_per_user": 1,
  "degrade_message": "系统繁忙，请稍后重试"
}
'@

Invoke-WebRequest -Method Post -Uri "$NacosAddr/nacos/v1/cs/configs" -Body @{
  dataId = "gateway-config.json"
  group = "DEFAULT_GROUP"
  content = $gatewayConfig
  type = "json"
} | Out-Null

Invoke-WebRequest -Method Post -Uri "$NacosAddr/nacos/v1/cs/configs" -Body @{
  dataId = "inventory-config.json"
  group = "DEFAULT_GROUP"
  content = $inventoryConfig
  type = "json"
} | Out-Null

Write-Host "Nacos配置已发布：gateway-config.json, inventory-config.json"
