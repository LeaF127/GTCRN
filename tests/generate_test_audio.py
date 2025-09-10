# -*- coding: utf-8 -*-
"""
测试音频生成脚本
功能：生成用于测试的音频文件
作者：天聪语音智能软件公司
"""

import numpy as np
import soundfile as sf
import os
from pathlib import Path

def generate_test_audio(filename, duration=5.0, sample_rate=16000, noise_level=0.1):
    """
    生成测试音频文件
    
    参数:
        filename (str): 输出文件名
        duration (float): 音频时长（秒）
        sample_rate (int): 采样率
        noise_level (float): 噪声水平 (0.0-1.0)
    """
    # 生成时间轴
    t = np.linspace(0, duration, int(sample_rate * duration))
    
    # 生成主信号（正弦波 + 谐波）
    signal = np.sin(2 * np.pi * 440 * t)  # 440Hz 基频
    signal += 0.5 * np.sin(2 * np.pi * 880 * t)  # 二次谐波
    signal += 0.3 * np.sin(2 * np.pi * 1320 * t)  # 三次谐波
    
    # 添加噪声
    noise = np.random.normal(0, noise_level, len(signal))
    noisy_signal = signal + noise
    
    # 归一化到 [-1, 1] 范围
    max_val = np.max(np.abs(noisy_signal))
    if max_val > 0:
        noisy_signal = noisy_signal / max_val * 0.8
    
    # 确保输出目录存在
    output_dir = Path(filename).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 保存音频文件
    sf.write(filename, noisy_signal, sample_rate)
    print(f"测试音频已生成: {filename}")
    print(f"时长: {duration}秒, 采样率: {sample_rate}Hz, 噪声水平: {noise_level}")

def generate_multiple_test_files():
    """生成多个测试音频文件"""
    test_dir = Path("test_audio")
    test_dir.mkdir(exist_ok=True)
    
    # 生成不同参数的测试文件
    test_cases = [
        ("short_clean.wav", 2.0, 16000, 0.05),    # 短音频，低噪声
        ("medium_noisy.wav", 5.0, 16000, 0.2),    # 中等长度，中等噪声
        ("long_very_noisy.wav", 10.0, 16000, 0.4), # 长音频，高噪声
        ("high_freq.wav", 3.0, 16000, 0.15),      # 高频信号
    ]
    
    for filename, duration, sample_rate, noise_level in test_cases:
        filepath = test_dir / filename
        generate_test_audio(str(filepath), duration, sample_rate, noise_level)
    
    print(f"\n所有测试音频文件已生成到: {test_dir.absolute()}")

if __name__ == '__main__':
    print("生成测试音频文件...")
    generate_multiple_test_files()
    print("完成！")
