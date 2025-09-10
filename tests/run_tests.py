# -*- coding: utf-8 -*-
"""
批量测试脚本
功能：自动运行多个测试用例
作者：天聪语音智能软件公司
"""

import subprocess
import sys
import time
import os
from pathlib import Path

def run_command(cmd, description=""):
    """
    运行命令并返回结果
    
    参数:
        cmd (list): 命令列表
        description (str): 命令描述
        
    返回:
        tuple: (success, output)
    """
    print(f"\n{'='*50}")
    print(f"执行: {description}")
    print(f"命令: {' '.join(cmd)}")
    print('='*50)
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=300,
        )
        success = result.returncode == 0
        
        if result.stdout:
            print("输出:")
            print(result.stdout)
        
        if result.stderr:
            print("错误:")
            print(result.stderr)
            
        return success, (result.stdout or "") + (result.stderr or "")
        
    except subprocess.TimeoutExpired:
        print("命令执行超时")
        return False, "超时"
    except Exception as e:
        print(f"命令执行失败: {e}")
        return False, str(e)

def check_server_running(host='localhost', port=7000):
    """检查服务器是否运行"""
    print(f"检查服务器状态: {host}:{port}")
    
    try:
        import socket
        test_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        test_socket.settimeout(2.0)
        test_socket.sendto(b"test", (host, port))
        test_socket.close()
        return True
    except:
        return False

def main():
    """主测试函数"""
    print("音频降噪服务批量测试")
    print("="*60)
    
    # 检查当前目录
    current_dir = Path.cwd()
    print(f"当前目录: {current_dir}")
    
    # 检查是否在正确的目录
    if not (current_dir / "server.py").exists():
        print("错误: 请在项目根目录下运行此脚本")
        return 1
    
    # 检查服务器是否运行
    if not check_server_running():
        print("警告: 服务器似乎未运行，请先启动服务器:")
        print("python server.py")
        print("\n是否继续测试? (y/n): ", end="")
        if input().lower() != 'y':
            return 1
    
    # 测试结果统计
    test_results = []
    
    # 1. 生成测试音频
    print("\n步骤 1: 生成测试音频")
    success, output = run_command(
        [sys.executable, "tests/generate_test_audio.py"],
        "生成测试音频文件"
    )
    test_results.append(("生成测试音频", success))
    
    if not success:
        print("生成测试音频失败，无法继续测试")
        return 1
    
    # 2. 测试连接
    print("\n步骤 2: 测试服务器连接")
    success, output = run_command(
        [sys.executable, "tests/udp_client.py", "--test-only"],
        "测试服务器连接"
    )
    test_results.append(("测试连接", success))
    
    # 3. 测试短音频
    print("\n步骤 3: 测试短音频降噪")
    success, output = run_command(
        [sys.executable, "tests/udp_client.py", 
         "--input", "test_audio/short_clean.wav"],
        "短音频降噪测试"
    )
    test_results.append(("短音频降噪", success))
    
    # 4. 测试中等长度音频
    print("\n步骤 4: 测试中等长度音频降噪")
    success, output = run_command(
        [sys.executable, "tests/udp_client.py", 
         "--input", "test_audio/medium_noisy.wav"],
        "中等长度音频降噪测试"
    )
    test_results.append(("中等长度音频降噪", success))
    
    # 5. 测试高噪声音频
    print("\n步骤 5: 测试高噪声音频降噪")
    success, output = run_command(
        [sys.executable, "tests/udp_client.py", 
         "--input", "test_audio/long_very_noisy.wav"],
        "高噪声音频降噪测试"
    )
    test_results.append(("高噪声音频降噪", success))
    
    # 6. 测试自定义输出路径
    print("\n步骤 6: 测试自定义输出路径")
    success, output = run_command(
        [sys.executable, "tests/udp_client.py", 
         "--input", "test_audio/high_freq.wav",
         "--output", "test_output/custom_denoised.wav"],
        "自定义输出路径测试"
    )
    test_results.append(("自定义输出路径", success))
    
    # 输出测试结果汇总
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    
    passed = 0
    total = len(test_results)
    
    for test_name, success in test_results:
        status = "✓ 通过" if success else "✗ 失败"
        print(f"{test_name:<20} {status}")
        if success:
            passed += 1
    
    print("-"*60)
    print(f"总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("🎉 所有测试通过！")
        return 0
    else:
        print("❌ 部分测试失败，请检查错误信息")
        return 1

if __name__ == '__main__':
    sys.exit(main())
