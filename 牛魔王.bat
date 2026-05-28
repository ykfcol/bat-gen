@echo off
chcp 65001 >nul
echo.
echo ========================================
echo   正在将【牛魔王】的文件覆盖到目标路径
echo ========================================
echo.
echo 源路径: %~dp0牛魔王\
echo 目标路径: /Users/yangkaifeng/Desktop/测试exe/userdata\
echo.

if not exist "%~dp0牛魔王\" (
    echo [错误] 角色文件夹不存在！
    pause
    exit /b 1
)

if not exist "/Users/yangkaifeng/Desktop/测试exe/userdata\" (
    echo [错误] 目标路径不存在！
    pause
    exit /b 1
)

xcopy "%~dp0牛魔王\*" "/Users/yangkaifeng/Desktop/测试exe/userdata\" /E /Y /Q
echo.
echo [完成] 【牛魔王】文件替换成功！
pause
