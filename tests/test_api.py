# -*- coding: utf-8 -*-
"""
FastAPI音频降噪服务测试脚本
功能：自动化测试API服务的各种功能
作者：天聪语音智能软件公司
"""

import subprocess
import sys
import time
import os
import requests
from pathlib import Path

def run_command(cmd, description="", timeout=300):
    """
    运行命令并返回结果
    
    参数:
        cmd (list): 命令列表
        description (str): 命令描述
        timeout (int): 超时时间（秒）
        
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
            timeout=timeout,
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

def check_api_server(base_url="http://localhost:8000"):
    """检查API服务器是否运行"""
    print(f"检查API服务器状态: {base_url}")
    
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        response.raise_for_status()
        data = response.json()
        print(f"服务器响应: {data.get('message', 'Unknown')}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"API服务器连接失败: {e}")
        return False

def test_api_endpoints(base_url="http://localhost:8000"):
    """测试API端点"""
    print("\n测试API端点...")
    
    endpoints = [
        ("/", "根路径"),
        ("/health", "健康检查"),
        ("/models/info", "模型信息"),
        ("/docs", "API文档"),
    ]
    
    results = []
    
    for endpoint, description in endpoints:
        try:
            url = f"{base_url}{endpoint}"
            response = requests.get(url, timeout=10)
            success = response.status_code == 200
            print(f"  {description}: {'✅' if success else '❌'} (状态码: {response.status_code})")
            results.append((description, success))
        except Exception as e:
            print(f"  {description}: ❌ (错误: {e})")
            results.append((description, False))
    
    return results

def main():
    """主测试函数"""
    print("FastAPI音频降噪服务测试")
    print("="*60)
    
    # 检查当前目录
    current_dir = Path.cwd()
    print(f"当前目录: {current_dir}")
    
    # 检查是否在正确的目录
    if not (current_dir / "api_server.py").exists():
        print("错误: 请在项目根目录下运行此脚本")
        return 1
    
    # 检查API服务器是否运行
    base_url = "http://localhost:8000"
    if not check_api_server(base_url):
        print("警告: API服务器似乎未运行，请先启动服务器:")
        print("python api_server.py")
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
    
    # 2. 测试API端点
    print("\n步骤 2: 测试API端点")
    endpoint_results = test_api_endpoints(base_url)
    test_results.extend(endpoint_results)
    
    # 3. 测试健康检查
    print("\n步骤 3: 测试健康检查")
    success, output = run_command(
        [sys.executable, "tests/api_client.py", "--test-only"],
        "API健康检查测试"
    )
    test_results.append(("健康检查", success))
    
    # 4. 测试文件路径模式
    print("\n步骤 4: 测试文件路径模式")
    success, output = run_command(
        [sys.executable, "tests/api_client.py", 
         "--input", "test_audio/short_clean.wav"],
        "文件路径模式降噪测试"
    )
    test_results.append(("文件路径模式", success))
    
    # 5. 测试上传模式
    print("\n步骤 5: 测试上传模式")
    success, output = run_command(
        [sys.executable, "tests/api_client.py", 
         "--input", "test_audio/medium_noisy.wav",
         "--upload"],
        "上传模式降噪测试"
    )
    test_results.append(("上传模式", success))
    
    # 6. 测试长音频处理
    print("\n步骤 6: 测试长音频处理")
    success, output = run_command(
        [sys.executable, "tests/api_client.py", 
         "--input", "test_audio/long_very_noisy.wav",
         "--output", "test_output/long_denoised.wav"],
        "长音频降噪测试"
    )
    test_results.append(("长音频处理", success))
    
    # 7. 测试错误处理
    print("\n步骤 7: 测试错误处理")
    success, output = run_command(
        [sys.executable, "tests/api_client.py", 
         "--input", "nonexistent.wav"],
        "错误处理测试"
    )
    # 对于错误处理测试，我们期望返回非零退出码
    test_results.append(("错误处理", not success))
    
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
        print("\nAPI服务功能正常，可以正常使用。")
        print(f"API文档地址: {base_url}/docs")
        return 0
    else:
        print("❌ 部分测试失败，请检查错误信息")
        return 1

if __name__ == '__main__':
    sys.exit(main())
