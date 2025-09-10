# -*- coding: utf-8 -*-
"""
FastAPI音频降噪客户端测试程序
功能：测试音频降噪API服务的HTTP接口
作者：天聪语音智能软件公司
"""

import requests
import json
import time
import os
import sys
import argparse
from pathlib import Path
from typing import Optional

class AudioDenoiseAPIClient:
    """音频降噪API客户端"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        初始化客户端
        
        参数:
            base_url (str): API服务器基础URL
        """
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        # 设置超时时间
        self.session.timeout = 300  # 5分钟超时
        
    def health_check(self) -> dict:
        """
        健康检查
        
        返回:
            dict: 健康状态信息
        """
        try:
            response = self.session.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e), "status": "unhealthy"}
    
    def get_model_info(self) -> dict:
        """
        获取模型信息
        
        返回:
            dict: 模型信息
        """
        try:
            response = self.session.get(f"{self.base_url}/models/info")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}
    
    def denoise_file(self, input_file: str, output_file: Optional[str] = None, samplerate: int = 16000) -> dict:
        """
        通过文件路径进行音频降噪
        
        参数:
            input_file (str): 输入音频文件路径
            output_file (str, optional): 输出音频文件路径
            samplerate (int): 采样率
            
        返回:
            dict: 处理结果
        """
        if not os.path.exists(input_file):
            return {"error": f"输入文件不存在: {input_file}"}
        
        try:
            # 构造请求数据
            data = {
                "input_file": input_file,
                "samplerate": samplerate
            }
            if output_file:
                data["output_file"] = output_file
            
            # 发送请求
            response = self.session.post(
                f"{self.base_url}/denoise",
                json=data,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}
    
    def denoise_upload(self, file_path: str, samplerate: int = 16000) -> dict:
        """
        上传文件进行音频降噪
        
        参数:
            file_path (str): 要上传的音频文件路径
            samplerate (int): 采样率
            
        返回:
            dict: 处理结果
        """
        if not os.path.exists(file_path):
            return {"error": f"文件不存在: {file_path}"}
        
        try:
            # 准备文件上传
            with open(file_path, 'rb') as f:
                files = {'file': (os.path.basename(file_path), f, 'audio/wav')}
                data = {'samplerate': samplerate}
                
                # 发送请求
                response = self.session.post(
                    f"{self.base_url}/denoise/upload",
                    files=files,
                    data=data
                )
                response.raise_for_status()
                return response.json()
                
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}
    
    def download_file(self, file_id: str, save_path: str) -> bool:
        """
        下载处理后的文件
        
        参数:
            file_id (str): 文件ID
            save_path (str): 保存路径
            
        返回:
            bool: 下载是否成功
        """
        try:
            response = self.session.get(f"{self.base_url}/download/{file_id}")
            response.raise_for_status()
            
            # 确保保存目录存在
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            # 保存文件
            with open(save_path, 'wb') as f:
                f.write(response.content)
            
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"下载失败: {e}")
            return False

def test_server_connection(base_url: str) -> bool:
    """
    测试服务器连接
    
    参数:
        base_url (str): 服务器URL
        
    返回:
        bool: 连接是否成功
    """
    print(f"测试服务器连接: {base_url}")
    
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        response.raise_for_status()
        data = response.json()
        print(f"服务器响应: {data.get('message', 'Unknown')}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"服务器连接失败: {e}")
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='音频降噪API客户端测试程序')
    parser.add_argument('--url', default='http://localhost:8000', help='API服务器URL')
    parser.add_argument('--input', help='输入音频文件路径')
    parser.add_argument('--output', help='输出音频文件路径')
    parser.add_argument('--upload', action='store_true', help='使用上传模式')
    parser.add_argument('--samplerate', type=int, default=16000, help='采样率')
    parser.add_argument('--test-only', action='store_true', help='仅测试连接')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("音频降噪API客户端测试程序")
    print("=" * 60)
    
    # 创建客户端
    client = AudioDenoiseAPIClient(args.url)
    
    # 测试服务器连接
    if not test_server_connection(args.url):
        print("服务器连接测试失败，请检查服务器是否启动")
        return 1
    
    if args.test_only:
        # 仅测试连接
        print("\n" + "=" * 30)
        print("服务器信息:")
        print("=" * 30)
        
        # 健康检查
        health = client.health_check()
        print(f"健康状态: {health}")
        
        # 模型信息
        model_info = client.get_model_info()
        print(f"模型信息: {model_info}")
        
        return 0
    
    if not args.input:
        print("错误: 请指定输入文件路径 (--input)")
        return 1
    
    # 如果没有指定输出文件，自动生成
    if not args.output:
        input_path = Path(args.input)
        args.output = str(input_path.parent / f"{input_path.stem}_api_denoised{input_path.suffix}")
    
    print(f"\n输入文件: {args.input}")
    print(f"输出文件: {args.output}")
    print(f"采样率: {args.samplerate}")
    print(f"模式: {'上传' if args.upload else '文件路径'}")
    
    try:
        if args.upload:
            # 上传模式
            print("\n使用上传模式处理...")
            result = client.denoise_upload(args.input, args.samplerate)
        else:
            # 文件路径模式
            print("\n使用文件路径模式处理...")
            result = client.denoise_file(args.input, args.output, args.samplerate)
        
        print("\n" + "=" * 30)
        print("处理结果:")
        print("=" * 30)
        
        if "error" in result:
            print(f"❌ 处理失败: {result['error']}")
            return 1
        
        # 显示结果
        print(f"状态: {'✅ 成功' if result.get('success') else '❌ 失败'}")
        print(f"消息: {result.get('message', 'N/A')}")
        print(f"处理时间: {result.get('processing_time', 0):.2f}秒")
        print(f"输入文件: {result.get('input_file', 'N/A')}")
        print(f"输出文件: {result.get('output_file', 'N/A')}")
        
        if result.get('file_size'):
            print(f"输出文件大小: {result['file_size']} 字节")
        
        # 如果是上传模式，尝试下载文件
        if args.upload and result.get('success'):
            output_file = result.get('output_file', '')
            if output_file and os.path.basename(output_file) in output_file:
                # 提取文件ID
                file_id = os.path.basename(output_file)
                print(f"\n下载处理后的文件...")
                if client.download_file(file_id, args.output):
                    print(f"✅ 文件已下载到: {args.output}")
                else:
                    print("❌ 文件下载失败")
        
        return 0 if result.get('success') else 1
        
    except KeyboardInterrupt:
        print("\n用户中断操作")
        return 1
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
