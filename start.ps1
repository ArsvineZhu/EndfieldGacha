[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$Host.UI.RawUI.WindowTitle = "终末地卡池模拟器"

Write-Host "========================================"
Write-Host "        终末地卡池模拟器 启动中..."
Write-Host "========================================"

Set-Location $PSScriptRoot

Write-Host ""
Write-Host "[1/3] 检查并安装依赖..."
pip install -r requirements.txt -q

Write-Host ""
Write-Host "[2/3] 压缩静态文件..."
python -c "from app.utils.compress import main; main()"

Write-Host ""
Write-Host "[3/3] 启动服务器..."
Write-Host ""
Write-Host "访问地址: http://127.0.0.1:5000"
Write-Host "按 Ctrl+C 停止服务器"
Write-Host ""

python -c "from server import app; from waitress import serve; serve(app, host='127.0.0.1', port=5000)"
