# -*- coding: utf-8 -*-
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

#pip install loguru
model_file="/work/cjh/gtcrn/stream/onnx_models/pytorch_model_simple.onnx"
session = onnxruntime.InferenceSession(model_file, None, providers=['CPUExecutionProvider'])
basedir = os.path.abspath(os.path.dirname(__file__))
logger.add(os.path.join(os.path.join(basedir, 'logs'), "denoise.log"),
           level="INFO", rotation="50 MB", format="{time}-{level}={message}", encoding="utf-8", enqueue=True)
print('init SeparateSpeech ok.')



def inference(source_file, save_file, samplerate):
    T_list = []
    outputs = []

    x = torch.from_numpy(sf.read(source_file, dtype='float32')[0])
    x = torch.stft(x, 512, 256, 512, torch.hann_window(512).pow(0.5), return_complex=False)[None]

    conv_cache = np.zeros([2, 1, 16, 16, 33],  dtype="float32")
    tra_cache = np.zeros([2, 3, 1, 1, 16],  dtype="float32")
    inter_cache = np.zeros([2, 1, 33, 16],  dtype="float32")

    inputs = x.numpy()
    for i in tqdm(range(inputs.shape[-2])):
        tic = time.perf_counter()
        
        out_i,  conv_cache, tra_cache, inter_cache \
                = session.run([], {'mix': inputs[..., i:i+1, :],
                    'conv_cache': conv_cache,
                    'tra_cache': tra_cache,
                    'inter_cache': inter_cache})

        toc = time.perf_counter()
        T_list.append(toc-tic)
        outputs.append(out_i)

    outputs = np.concatenate(outputs, axis=2)
    enhanced = istft(outputs[...,0] + 1j * outputs[...,1], n_fft=512, hop_length=256, win_length=512, window=np.hanning(512)**0.5)
    sf.write(save_file, enhanced.squeeze(), samplerate)

    
def DenoiseWorker(input_file_path, output_file_path, client_addr, server):
    # 降噪操作，并把执行结果返回
    start_time = time.time()
    inference(input_file_path, output_file_path)
    cost_time = time.time() - start_time  
    err=0
    msg="success"
    server.sendto(f"{err}|{msg}".encode(), client_addr)  # UDP 是无状态连接，所以每次连接都需要给出目的地址 
    logger.info(f"文件[{input_file_path}]降噪完成，花费时间{cost_time}s")    
    return


def RecvUDP(server, executor):
    print('wait UDP...')
    while True:
        try:
            data, client_addr = server.recvfrom(65536)
            data = data.decode("utf8", "ignore")
            print('get UDP...')
        except Exception as e:
            logger.error(e)
        else:
            input_file_path, output_file_path = data.split("|")
            print(input_file_path)
            print(output_file_path)
            start_time = time.time()
            inference(input_file_path, output_file_path,samplerate=16000)
            cost_time = time.time() - start_time  
            err=0
            msg="success"
            server.sendto(f"{err}|{msg}".encode(), client_addr)  # UDP 是无状态连接，所以每次连接都需要给出目的地址 
            logger.info(f"文件[{input_file_path}]降噪完成，花费时间{cost_time}s")    
            print("文件降噪完成")    
            print(f"文件[{input_file_path}]降噪完成，花费时间{cost_time}s")    

 
    
if __name__ == '__main__':
    source_file="./wav/test1.wav"
    save_file="./wav/out.wav"
    inference(source_file=source_file,
              save_file=save_file,
              samplerate=16000)
    def on_exit(signo, frame):
        server.close()
        sys.exit(0)
    # 主进程退出信号监听
    """
        SIGINT ctrl+C终端
        SIGTERM kill终止
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