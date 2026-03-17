param(
  [string]$K6BaseUrl = "http://host.docker.internal",
  [int]$GoodsId = 1,
  [int]$SeckillStock = 50000,
  [int]$OversellStock = 100,
  [string]$OutDir = "results"
)

$ErrorActionPreference = "Stop"
$workspace = (Get-Location).Path

function Run-K6 {
  param(
    [string]$Script,
    [string]$SummaryFile,
    [string]$RawOutFile = ""
  )

  $cmd = @(
    "run", "/work/tests/k6/$Script",
    "-e", "BASE_URL=$K6BaseUrl",
    "-e", "GOODS_ID=$GoodsId",
    "-e", "STOCK=$SeckillStock",
    "--summary-export", "/work/$SummaryFile"
  )

  if ($RawOutFile -ne "") {
    $cmd += @("--out", "json=/work/$RawOutFile")
  }

  docker run --rm -i `
    -v "${workspace}:/work" `
    -w /work `
    grafana/k6 @cmd
}

Write-Host "[1/6] static 200vu 30s"
Run-K6 -Script "static.js" -SummaryFile "$OutDir/k6_static_summary.json"

Write-Host "[2/6] api 200vu 30s"
Run-K6 -Script "api.js" -SummaryFile "$OutDir/k6_api_summary.json"

Write-Host "[3/6] seckill 500vu 30s"
Run-K6 -Script "seckill_benchmark.js" -SummaryFile "$OutDir/k6_seckill_summary.json" -RawOutFile "$OutDir/k6_seckill_raw.json"

Write-Host "[4/6] lb 200vu 60s"
# Reset gateway access log to isolate this round.
docker exec disseckill-gateway sh -c "truncate -s 0 /var/log/nginx/access.log"
Run-K6 -Script "lb.js" -SummaryFile "$OutDir/k6_lb_summary.json"

Write-Host "[5/6] oversell 1000vu x 1 iter"
# oversell uses dedicated stock value.
docker run --rm -i `
  -v "${workspace}:/work" `
  -w /work `
  grafana/k6 run /work/tests/k6/oversell.js `
  -e BASE_URL=$K6BaseUrl `
  -e GOODS_ID=$GoodsId `
  -e STOCK=$OversellStock `
  --summary-export "/work/$OutDir/k6_oversell_summary.json"

Write-Host "[6/6] collect lb distribution"
docker exec disseckill-gateway sh -c "cat /var/log/nginx/access.log" > "$OutDir/nginx_lb_access.log"

python tests/k6/summarize_k6.py

Write-Host "Done. Summary at $OutDir/k6_summary.json"
