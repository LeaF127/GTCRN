# -*- coding: utf-8 -*-
"""
音频预处理模块
功能：使用ffmpeg将音频转换为16kHz采样率
作者：天聪语音智能软件公司
"""

import os
import tempfile
import subprocess
from pathlib import Path
from loguru import logger


def convert_audio_to_16k(input_file: str, output_file: str = None) -> str:
    """
    使用ffmpeg将音频文件转换为16kHz采样率
    
    参数:
        input_file (str): 输入音频文件路径
        output_file (str, optional): 输出音频文件路径，如果为None则生成临时文件
        
    返回:
        str: 转换后的音频文件路径
        
    异常:
        RuntimeError: ffmpeg转换失败时抛出
    """
    try:
        # 检查输入文件是否存在
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"输入文件不存在: {input_file}")
        
        # 如果没有指定输出文件，创建临时文件
        if output_file is None:
            input_path = Path(input_file)
            temp_dir = os.path.dirname(input_file)
            output_file = os.path.join(temp_dir, f"temp_16k_{input_path.stem}.wav")
        
        # 确保输出目录存在
        output_dir = os.path.dirname(output_file)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        # 构建ffmpeg命令
        # -i: 输入文件
        # -ar 16000: 设置采样率为16kHz
        # -ac 1: 设置为单声道（如果需要）
        # -y: 覆盖输出文件
        cmd = [
            'ffmpeg',
            '-i', input_file,
            '-ar', '16000',
            '-ac', '1',  # 单声道
            '-y',  # 覆盖输出文件
            output_file
        ]
        
        logger.info(f"开始转换音频: {input_file} -> {output_file}")
        
        # 执行ffmpeg命令
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        
        # 检查输出文件是否成功创建
        if not os.path.exists(output_file):
            raise RuntimeError(f"ffmpeg转换失败，输出文件未创建: {output_file}")
        
        logger.info(f"音频转换完成: {output_file}")
        return output_file
        
    except subprocess.CalledProcessError as e:
        error_msg = f"ffmpeg转换失败: {e.stderr}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    except Exception as e:
        error_msg = f"音频预处理失败: {str(e)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)


def check_ffmpeg_available() -> bool:
    """
    检查ffmpeg是否可用
    
    返回:
        bool: ffmpeg是否可用
    """
    try:
        result = subprocess.run(
            ['ffmpeg', '-version'],
            capture_output=True,
            text=True,
            check=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def get_audio_info(input_file: str) -> dict:
    """
    获取音频文件信息
    
    参数:
        input_file (str): 音频文件路径
        
    返回:
        dict: 音频信息，包含采样率、声道数、时长等
    """
    try:
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            input_file
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        
        import json
        info = json.loads(result.stdout)
        
        # 提取音频流信息
        audio_stream = None
        for stream in info.get('streams', []):
            if stream.get('codec_type') == 'audio':
                audio_stream = stream
                break
        
        if audio_stream:
            return {
                'sample_rate': int(audio_stream.get('sample_rate', 0)),
                'channels': int(audio_stream.get('channels', 0)),
                'duration': float(audio_stream.get('duration', 0)),
                'codec': audio_stream.get('codec_name', 'unknown')
            }
        else:
            return {}
            
    except Exception as e:
        logger.warning(f"获取音频信息失败: {e}")
        return {}


def preprocess_audio_if_needed(input_file: str, target_sample_rate: int = 16000) -> tuple:
    """
    如果需要，预处理音频文件到目标采样率
    
    参数:
        input_file (str): 输入音频文件路径
        target_sample_rate (int): 目标采样率，默认16000
        
    返回:
        tuple: (processed_file_path, is_temp_file)
            - processed_file_path: 处理后的文件路径
            - is_temp_file: 是否为临时文件（需要后续清理）
    """
    try:
        # 检查ffmpeg是否可用
        if not check_ffmpeg_available():
            logger.warning("ffmpeg不可用，跳过音频预处理")
            return input_file, False
        
        # 获取音频信息
        audio_info = get_audio_info(input_file)
        current_sample_rate = audio_info.get('sample_rate', 0)
        
        # 如果当前采样率已经是目标采样率，直接返回原文件
        if current_sample_rate == target_sample_rate:
            logger.info(f"音频采样率已经是{target_sample_rate}Hz，跳过转换")
            return input_file, False
        
        # 需要转换采样率
        logger.info(f"音频采样率为{current_sample_rate}Hz，需要转换为{target_sample_rate}Hz")
        
        # 创建临时文件进行转换
        input_path = Path(input_file)
        temp_dir = os.path.dirname(input_file)
        temp_file = os.path.join(temp_dir, f"temp_16k_{input_path.stem}.wav")
        
        # 执行转换
        converted_file = convert_audio_to_16k(input_file, temp_file)
        
        return converted_file, True
        
    except Exception as e:
        logger.error(f"音频预处理失败: {e}")
        # 如果预处理失败，返回原文件
        return input_file, False


def cleanup_temp_file(file_path: str):
    """
    清理临时文件
    
    参数:
        file_path (str): 要清理的文件路径
    """
    try:
        if os.path.exists(file_path) and 'temp_16k_' in os.path.basename(file_path):
            os.remove(file_path)
            logger.info(f"已清理临时文件: {file_path}")
    except Exception as e:
        logger.warning(f"清理临时文件失败: {e}")
