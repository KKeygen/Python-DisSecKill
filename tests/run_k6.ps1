param(
  [string]$K6BaseUrl = "http://host.docker.internal",
    [int]$GoodsId = 1,
    [int]$Stock = 100,
  [string]$OutPrefix = "results/k6_seckill_latest",
  [ValidateSet("smoke", "stress")]
  [string]$Profile = "smoke"
)

$ErrorActionPreference = "Stop"

Write-Host "[1/3] Init stock..."
Write-Host "k6 setup() will init stock on target service"

Write-Host "[2/3] Run k6 load test..."
$workspace = (Get-Location).Path
$scriptPath = "/work/tests/k6/seckill.js"

# Use official k6 image, no local installation required.
docker run --rm -i `
  -v "${workspace}:/work" `
  -w /work `
  grafana/k6 run $scriptPath `
  -e BASE_URL=$K6BaseUrl `
  -e GOODS_ID=$GoodsId `
  -e STOCK=$Stock `
  -e INIT_STOCK=true `
  -e PROFILE=$Profile `
  --summary-export "${OutPrefix}.json"

Write-Host "[3/3] Done"
Write-Host "Summary JSON: ${OutPrefix}.json"
