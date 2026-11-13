@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 投递领航 - Job Pilot
echo 打开 http://127.0.0.1:8765
python -c "import flask, requests, pypdf, playwright" 2>nul
if errorlevel 1 (
  echo.
  echo [缺少依赖] 当前 python 解释器没有安装项目的依赖包。
  echo 当前 python：
  where python
  echo.
  echo 请执行：python -m pip install -r requirements.txt
  echo 如果机器上有多个 Python，用装好依赖的那个解释器启动，例如：
  echo    D:\Python\python.exe app.py
  pause
  exit /b 1
)
python app.py
pause
