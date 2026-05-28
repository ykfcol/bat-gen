@echo off
chcp 65001 >nul
echo.
echo ========================================
echo   正在将【猪】的文件覆盖到目标路径
echo ========================================
echo.
echo 源路径: %~dp0猪\
echo 目标路径: /Users/yangkaifeng/Desktop/测试exe/userdata\
echo.

if not exist "%~dp0猪\" (
    echo [错误] 角色文件夹不存在！
    pause
    exit /b 1
)

if not exist "/Users/yangkaifeng/Desktop/测试exe/userdata\" (
    echo [错误] 目标路径不存在！
    pause
    exit /b 1
)

xcopy "%~dp0猪\*" "/Users/yangkaifeng/Desktop/测试exe/userdata\" /E /Y /Q
echo.
echo [完成] 【猪】文件替换成功！
pause
