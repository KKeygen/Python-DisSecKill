param(
    [string]$Host = "localhost",
    [int]$Port = 80
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$plan = Join-Path $PSScriptRoot "jmeter\seckill-governance.jmx"
$resultDir = Join-Path $PSScriptRoot "jmeter\results"

if (!(Test-Path $resultDir)) {
    New-Item -ItemType Directory -Path $resultDir | Out-Null
}

docker run --rm `
  -v "${root}:/work" `
  -w /work `
  docker.snakekiss.com/justb4/jmeter:5.6.3 `
  -n -t /work/tests/jmeter/seckill-governance.jmx `
  -JHOST=$Host -JPORT=$Port `
  -l /work/tests/jmeter/results/seckill-governance.jtl `
  -e -o /work/tests/jmeter/results/html
