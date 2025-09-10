# -*- coding: utf-8 -*-
"""
音频降噪服务器
功能：基于ONNX模型的音频降噪处理，支持UDP协议接收客户端请求
所属：天聪语音智能软件公司
"""

import subprocess
import os
import time
import socket
import signal
import sys
from loguru import logger
from concurrent.futures import ProcessPoolExecutor
import torch
import argparse
 
import torch
import onnxruntime
import numpy as np
import soundfile as sf
from tqdm import tqdm
from librosa import istft

print('init SeparateSpeech...')

# 依赖安装说明：pip install loguru
# ONNX模型文件路径
model_file = "stream/onnx_models/pytorch_model_simple.onnx"
# 创建ONNX推理会话，使用CPU执行提供者
session = onnxruntime.InferenceSession(model_file, None, providers=['CPUExecutionProvider'])
# 获取项目根目录
basedir = os.path.abspath(os.path.dirname(__file__))
# 配置日志记录器，记录到logs目录下的denoise.log文件
logger.add(os.path.join(os.path.join(basedir, 'logs'), "denoise.log"),
           level="INFO", rotation="50 MB", format="{time}-{level}={message}", encoding="utf-8", enqueue=True)
print('init SeparateSpeech ok.')



def inference(source_file, save_file, samplerate):
    """
    音频降噪推理函数
    
    参数:
        source_file (str): 输入音频文件路径
        save_file (str): 输出音频文件路径  
        samplerate (int): 采样率
    """
    T_list = []  # 记录每帧处理时间
    outputs = []  # 存储每帧的输出结果

    # 读取音频文件并转换为张量
    x = torch.from_numpy(sf.read(source_file, dtype='float32')[0])
    # 对音频进行短时傅里叶变换(STFT)，转换为频域表示
    x = torch.stft(x, 512, 256, 512, torch.hann_window(512).pow(0.5), return_complex=False)[None]

    # 初始化模型缓存，用于流式处理
    conv_cache = np.zeros([2, 1, 16, 16, 33],  dtype="float32")  # 卷积层缓存
    tra_cache = np.zeros([2, 3, 1, 1, 16],  dtype="float32")     # Transformer缓存
    inter_cache = np.zeros([2, 1, 33, 16],  dtype="float32")     # 中间层缓存

    inputs = x.numpy()
    # 逐帧处理音频数据
    for i in tqdm(range(inputs.shape[-2])):
        tic = time.perf_counter()
        
        # 运行ONNX模型推理，输入当前帧和缓存状态
        out_i, conv_cache, tra_cache, inter_cache \
                = session.run([], {'mix': inputs[..., i:i+1, :],
                    'conv_cache': conv_cache,
                    'tra_cache': tra_cache,
                    'inter_cache': inter_cache})

        toc = time.perf_counter()
        T_list.append(toc-tic)  # 记录处理时间
        outputs.append(out_i)   # 保存输出结果

    # 将所有帧的输出结果拼接
    outputs = np.concatenate(outputs, axis=2)
    # 将频域结果转换回时域音频信号
    enhanced = istft(outputs[...,0] + 1j * outputs[...,1], n_fft=512, hop_length=256, win_length=512, window=np.hanning(512)**0.5)
    # 保存降噪后的音频文件
    sf.write(save_file, enhanced.squeeze(), samplerate)

    
def DenoiseWorker(input_file_path, output_file_path, client_addr, server):
    """
    降噪工作进程函数（未使用的多进程版本）
    
    参数:
        input_file_path (str): 输入音频文件路径
        output_file_path (str): 输出音频文件路径
        client_addr (tuple): 客户端地址
        server (socket): UDP服务器套接字
    """
    # 记录开始时间
    start_time = time.time()
    # 执行降噪处理（注意：这里缺少samplerate参数）
    inference(input_file_path, output_file_path, samplerate=16000)
    # 计算处理耗时
    cost_time = time.time() - start_time  
    # 设置返回状态
    err = 0
    msg = "success"
    # 向客户端发送处理结果（UDP是无状态连接，需要指定目标地址）
    server.sendto(f"{err}|{msg}".encode(), client_addr)
    # 记录日志
    logger.info(f"文件[{input_file_path}]降噪完成，花费时间{cost_time}s")    
    return


def RecvUDP(server, executor):
    """
    UDP服务器主循环，接收客户端请求并处理音频降噪任务
    
    参数:
        server (socket): UDP服务器套接字
        executor (ProcessPoolExecutor): 进程池执行器（当前未使用）
    """
    print('等待UDP连接...')
    while True:
        try:
            # 接收UDP数据包，最大65536字节
            data, client_addr = server.recvfrom(65536)
            # 解码接收到的数据
            data = data.decode("utf8", "ignore")
            print('get UDP...')
        except Exception as e:
            # 记录接收错误
            logger.error(e)
        else:
            # 解析客户端发送的文件路径（格式：输入文件路径|输出文件路径）
            input_file_path, output_file_path = data.split("|")
            print(f"输入文件: {input_file_path}")
            print(f"输出文件: {output_file_path}")
            
            # 记录开始时间
            start_time = time.time()
            # 执行音频降噪处理
            inference(input_file_path, output_file_path, samplerate=16000)
            # 计算处理耗时
            cost_time = time.time() - start_time  
            
            # 设置返回状态
            err = 0
            msg = "success"
            # 向客户端发送处理结果（UDP是无状态连接，需要指定目标地址）
            server.sendto(f"{err}|{msg}".encode(), client_addr)
            # 记录处理完成的日志
            logger.info(f"文件[{input_file_path}]降噪完成，花费时间{cost_time}s")    
            print("文件降噪完成")    
            print(f"文件[{input_file_path}]降噪完成，花费时间{cost_time}s")    

 
    
if __name__ == '__main__':
    # 测试模式：直接处理本地音频文件
    source_file = "./wav/test1.wav"
    save_file = "./wav/out.wav"
    inference(source_file=source_file,
              save_file=save_file,
              samplerate=16000)
    
    def on_exit(signo, frame):
        """
        程序退出处理函数
        
        参数:
            signo: 信号编号
            frame: 当前栈帧
        """
        server.close()
        sys.exit(0)
    # 主进程退出信号监听
    """
    信号说明:
        SIGINT: Ctrl+C终端信号
        SIGTERM: kill终止信号
    """
    signal.signal(signal.SIGINT, on_exit)
    signal.signal(signal.SIGTERM, on_exit)

    worker_process = 5
    with ProcessPoolExecutor(max_workers=worker_process) as executor:
        port = 7000
        ip_port = ('0.0.0.0', port)
        server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server.bind(ip_port)
        print('start listening...')
        RecvUDP(server, executor)              