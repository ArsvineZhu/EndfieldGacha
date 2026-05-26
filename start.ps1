[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$Host.UI.RawUI.WindowTitle = "终末地卡池模拟器"

function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    $colors = @{
        "Green"  = @{Before = ""; After = ""}
        "Yellow" = @{Before = ""; After = ""}
        "Red"    = @{Before = ""; After = ""}
        "Cyan"   = @{Before = ""; After = ""}
    }
    Write-Host "$($colors[$Color].Before)$Message$($colors[$Color].After)" -ForegroundColor $Color
}

function Test-Command {
    param([string]$Cmd)
    try { Get-Command $Cmd -ErrorAction Stop | Out-Null; return $true } catch { return $false }
}

function Test-Port {
    param([int]$Port)
    $tcp = New-Object System.Net.Sockets.TcpClient
    try {
        $tcp.Connect("127.0.0.1", $Port)
        $tcp.Close()
        return $true
    } catch { return $false }
}

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host ""
Write-ColorOutput "========================================" "Cyan"
Write-ColorOutput "        终末地卡池模拟器 启动中..." "Cyan"
Write-ColorOutput "========================================" "Cyan"
Write-Host ""

if (-not (Test-Command "uv")) {
    Write-ColorOutput "[错误] 未找到 uv，请先安装 uv（https://docs.astral.sh/uv/）" "Red"
    exit 1
}
Write-Host "[信息] uv版本: $(uv --version)"

Write-Host ""
Write-ColorOutput "[1/5] 检查并安装依赖..." "Yellow"
if (Test-Path "pyproject.toml") {
    Write-ColorOutput "      正在同步依赖（uv sync --frozen）..." "Cyan"
    uv sync --frozen 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-ColorOutput "[错误] 依赖同步失败，请检查 pyproject.toml/网络环境" "Red"
        exit 1
    }
    Write-ColorOutput "      依赖同步完成" "Green"
} else {
    Write-ColorOutput "[错误] 未找到 pyproject.toml" "Red"
    exit 1
}

Write-Host ""
Write-ColorOutput "[2/5] 检查端口占用..." "Yellow"
$port = 5000
if (Test-Port $port) {
    Write-ColorOutput "[警告] 端口 $port 已被占用，尝试关闭现有进程..." "Yellow"
    Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | 
        ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 1
    if (Test-Port $port) {
        Write-ColorOutput "[错误] 无法释放端口 $port，请手动关闭占用进程" "Red"
        exit 1
    }
    Write-ColorOutput "      端口已释放" "Green"
}

Write-Host ""
Write-ColorOutput "[3/5] 压缩静态文件..." "Yellow"
Write-ColorOutput "      将在启动服务器时自动压缩" "Green"

Write-Host ""
Write-ColorOutput "[4/5] 初始化日志..." "Yellow"
$logDir = Join-Path $PSScriptRoot "logs"
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}
$logFile = Join-Path $logDir "server_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
Write-ColorOutput "      日志文件: $logFile" "Green"

Write-Host ""
Write-ColorOutput "[5/5] 启动服务器..." "Yellow"
Write-Host ""
Write-ColorOutput "访问地址: http://127.0.0.1:$port" "Cyan"
Write-ColorOutput "按 Ctrl+C 停止服务器" "Cyan"
Write-Host ""

$startInfo = New-Object System.Diagnostics.ProcessStartInfo
$startInfo.FileName = "uv"
$startInfo.Arguments = "run python server.py --waitress"
$startInfo.WorkingDirectory = $PSScriptRoot
$startInfo.RedirectStandardOutput = $false
$startInfo.RedirectStandardError = $false
$startInfo.UseShellExecute = $false
$startInfo.CreateNoWindow = $false

try {
    $process = [System.Diagnostics.Process]::Start($startInfo)
    $process.WaitForExit()
} catch {
    Write-ColorOutput "[错误] 服务器启动失败: $_" "Red"
    exit 1
}
