@echo off
chcp 65001 >nul
echo 音频降噪服务测试脚本
echo ========================

echo 检查Python环境...
python --version
if %errorlevel% neq 0 (
    echo 错误: 未找到Python，请确保Python已安装并添加到PATH
    pause
    exit /b 1
)

echo.
echo 运行批量测试...
python run_tests.py

echo.
echo 测试完成，按任意键退出...
pause >nul
