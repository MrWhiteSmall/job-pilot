@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "PY="
where python >nul 2>nul && set "PY=python"
if not defined PY ( where py >nul 2>nul && set "PY=py -3" )
if not defined PY ( if exist "D:\Anaconda3\python.exe" set "PY=D:\Anaconda3\python.exe" )
if not defined PY (
  echo [错误] 没找到 Python。请先安装 Python 3.10+ 并勾选 Add to PATH。
  pause
  exit /b 1
)
echo == 启动服务 ==
%PY% tools\launcher.py start
echo.
pause
