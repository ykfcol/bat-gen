@echo off
chcp 65001 >nul
echo ========================================
echo   角色文件替换工具 - 打包脚本
echo ========================================
echo.

REM 检查是否安装了 pyinstaller
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo 正在安装 PyInstaller...
    pip install pyinstaller
)

echo 开始打包...
pyinstaller --onefile --windowed --name "角色文件替换工具" --clean main.py

echo.
echo 打包完成！exe文件在 dist 目录下。
echo 请将 dist\角色文件替换工具.exe 复制到你想要的目录运行。
pause
