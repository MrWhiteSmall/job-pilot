@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 投递领航正在启动。打开 http://127.0.0.1:8765
echo 如首次运行缺少依赖，请执行 python -m pip install -r requirements.txt
python app.py
pause
