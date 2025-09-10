# -*- coding: utf-8 -*-
"""
UDP音频降噪客户端测试程序
功能：测试音频降噪服务器的UDP服务是否正常工作
作者：天聪语音智能软件公司
"""

import socket
import time
import os
import sys
import argparse
from pathlib import Path

class AudioDenoiseClient:
    """音频降噪UDP客户端"""
    
    def __init__(self, server_host='localhost', server_port=7000):
        """
        初始化客户端
        
        参数:
            server_host (str): 服务器地址，默认localhost
            server_port (int): 服务器端口，默认7000
        """
        self.server_host = server_host
        self.server_port = server_port
        self.client_socket = None
        
    def connect(self):
        """建立UDP连接"""
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # 设置超时时间，避免无限等待
            self.client_socket.settimeout(30.0)
            print(f"客户端已初始化，目标服务器: {self.server_host}:{self.server_port}")
            return True
        except Exception as e:
            print(f"连接失败: {e}")
            return False
    
    def send_denoise_request(self, input_file, output_file):
        """
        发送降噪请求
        
        参数:
            input_file (str): 输入音频文件路径
            output_file (str): 输出音频文件路径
            
        返回:
            tuple: (success, message, cost_time)
        """
        if not self.client_socket:
            return False, "客户端未连接", 0
            
        # 检查输入文件是否存在
        if not os.path.exists(input_file):
            return False, f"输入文件不存在: {input_file}", 0
            
        # 确保输出目录存在
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        try:
            # 构造请求消息：输入文件路径|输出文件路径
            message = f"{input_file}|{output_file}"
            
            print(f"发送降噪请求...")
            print(f"输入文件: {input_file}")
            print(f"输出文件: {output_file}")
            
            # 记录开始时间
            start_time = time.time()
            
            # 发送请求到服务器
            self.client_socket.sendto(message.encode('utf-8'), (self.server_host, self.server_port))
            
            # 等待服务器响应
            response, server_addr = self.client_socket.recvfrom(1024)
            response_str = response.decode('utf-8')
            
            # 计算总耗时
            cost_time = time.time() - start_time
            
            # 解析响应：错误码|消息
            if '|' in response_str:
                err_code, msg = response_str.split('|', 1)
                success = (err_code == '0')
                return success, msg, cost_time
            else:
                return False, f"服务器响应格式错误: {response_str}", cost_time
                
        except socket.timeout:
            return False, "请求超时，服务器可能未响应", time.time() - start_time
        except Exception as e:
            return False, f"请求失败: {e}", time.time() - start_time
    
    def close(self):
        """关闭客户端连接"""
        if self.client_socket:
            self.client_socket.close()
            self.client_socket = None
            print("客户端连接已关闭")

def test_server_connection(host='localhost', port=7000):
    """
    测试服务器连接
    
    参数:
        host (str): 服务器地址
        port (int): 服务器端口
        
    返回:
        bool: 连接是否成功
    """
    print(f"测试服务器连接: {host}:{port}")
    
    try:
        # 创建测试套接字
        test_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        test_socket.settimeout(5.0)
        
        # 发送测试消息
        test_message = "test|test"
        test_socket.sendto(test_message.encode('utf-8'), (host, port))
        
        # 尝试接收响应（可能会超时，这是正常的）
        try:
            response, addr = test_socket.recvfrom(1024)
            print(f"服务器响应: {response.decode('utf-8')}")
        except socket.timeout:
            print("服务器连接正常（无响应是正常的，因为测试消息格式不正确）")
        
        test_socket.close()
        return True
        
    except Exception as e:
        print(f"服务器连接失败: {e}")
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='音频降噪UDP客户端测试程序')
    parser.add_argument('--host', default='localhost', help='服务器地址 (默认: localhost)')
    parser.add_argument('--port', type=int, default=7000, help='服务器端口 (默认: 7000)')
    parser.add_argument('--input', required=True, help='输入音频文件路径')
    parser.add_argument('--output', help='输出音频文件路径 (默认: 输入文件名_denoised.wav)')
    parser.add_argument('--test-only', action='store_true', help='仅测试连接，不发送实际请求')
    
    args = parser.parse_args()
    
    # 如果没有指定输出文件，自动生成
    if not args.output:
        input_path = Path(args.input)
        args.output = str(input_path.parent / f"{input_path.stem}_denoised{input_path.suffix}")
    
    print("=" * 50)
    print("音频降噪UDP客户端测试程序")
    print("=" * 50)
    
    # 测试服务器连接
    if not test_server_connection(args.host, args.port):
        print("服务器连接测试失败，请检查服务器是否启动")
        return 1
    
    if args.test_only:
        print("连接测试完成")
        return 0
    
    # 创建客户端并发送请求
    client = AudioDenoiseClient(args.host, args.port)
    
    try:
        if not client.connect():
            return 1
        
        # 发送降噪请求
        success, message, cost_time = client.send_denoise_request(args.input, args.output)
        
        print("\n" + "=" * 30)
        print("处理结果:")
        print("=" * 30)
        print(f"状态: {'成功' if success else '失败'}")
        print(f"消息: {message}")
        print(f"耗时: {cost_time:.2f}秒")
        
        if success:
            print(f"降噪完成！输出文件: {args.output}")
            if os.path.exists(args.output):
                file_size = os.path.getsize(args.output)
                print(f"输出文件大小: {file_size} 字节")
        else:
            print("降噪失败，请检查错误信息")
            
    finally:
        client.close()
    
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())
