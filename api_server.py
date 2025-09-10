# -*- coding: utf-8 -*-
"""
音频降噪FastAPI服务器
功能：基于ONNX模型的音频降噪处理，提供RESTful API接口
作者：天聪语音智能软件公司
"""

import os
import time
import tempfile
import shutil
from pathlib import Path
from typing import Optional, List
import uuid

import torch
import onnxruntime
import numpy as np
import soundfile as sf
from tqdm import tqdm
from librosa import istft
from loguru import logger

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# 全局变量
app = FastAPI(
    title="音频降噪API服务",
    description="基于ONNX模型的音频降噪处理服务",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境中应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局变量
session = None
basedir = None
temp_dir = None

# 请求/响应模型
class DenoiseRequest(BaseModel):
    """降噪请求模型"""
    input_file: str = Field(..., description="输入音频文件路径")
    output_file: Optional[str] = Field(None, description="输出音频文件路径")
    samplerate: int = Field(16000, description="采样率")

class DenoiseResponse(BaseModel):
    """降噪响应模型"""
    success: bool = Field(..., description="处理是否成功")
    message: str = Field(..., description="处理消息")
    input_file: str = Field(..., description="输入文件路径")
    output_file: str = Field(..., description="输出文件路径")
    processing_time: float = Field(..., description="处理时间（秒）")
    file_size: Optional[int] = Field(None, description="输出文件大小（字节）")

class HealthResponse(BaseModel):
    """健康检查响应模型"""
    status: str = Field(..., description="服务状态")
    model_loaded: bool = Field(..., description="模型是否已加载")
    uptime: float = Field(..., description="服务运行时间（秒）")

# 启动时间记录
start_time = time.time()

def init_model():
    """初始化ONNX模型"""
    global session, basedir, temp_dir
    
    print('正在初始化音频分离模块...')
    
    # 模型文件路径
    model_file = "stream/onnx_models/pytorch_model_simple.onnx"
    
    if not os.path.exists(model_file):
        raise FileNotFoundError(f"模型文件不存在: {model_file}")
    
    # 创建ONNX推理会话
    session = onnxruntime.InferenceSession(model_file, None, providers=['CPUExecutionProvider'])
    
    # 获取项目根目录
    basedir = os.path.abspath(os.path.dirname(__file__))
    
    # 创建临时目录
    temp_dir = os.path.join(basedir, "temp")
    os.makedirs(temp_dir, exist_ok=True)
    
    # 配置日志记录器
    logs_dir = os.path.join(basedir, 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    logger.add(
        os.path.join(logs_dir, "api_denoise.log"),
        level="INFO", 
        rotation="50 MB", 
        format="{time}-{level}={message}", 
        encoding="utf-8", 
        enqueue=True
    )
    
    print('音频分离模块初始化完成.')

def inference(source_file: str, save_file: str, samplerate: int = 16000) -> dict:
    """
    音频降噪推理函数
    
    参数:
        source_file (str): 输入音频文件路径
        save_file (str): 输出音频文件路径  
        samplerate (int): 采样率
        
    返回:
        dict: 处理结果信息
    """
    if session is None:
        raise RuntimeError("模型未初始化")
    
    T_list = []  # 记录每帧处理时间
    outputs = []  # 存储每帧的输出结果

    try:
        # 读取音频文件并转换为张量
        x = torch.from_numpy(sf.read(source_file, dtype='float32')[0])
        # 对音频进行短时傅里叶变换(STFT)，转换为频域表示
        x = torch.stft(x, 512, 256, 512, torch.hann_window(512).pow(0.5), return_complex=False)[None]

        # 初始化模型缓存，用于流式处理
        conv_cache = np.zeros([2, 1, 16, 16, 33], dtype="float32")  # 卷积层缓存
        tra_cache = np.zeros([2, 3, 1, 1, 16], dtype="float32")     # Transformer缓存
        inter_cache = np.zeros([2, 1, 33, 16], dtype="float32")     # 中间层缓存

        inputs = x.numpy()
        # 逐帧处理音频数据
        for i in tqdm(range(inputs.shape[-2]), desc="处理音频帧"):
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
        
        # 确保输出目录存在
        output_dir = os.path.dirname(save_file)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            
        # 保存降噪后的音频文件
        sf.write(save_file, enhanced.squeeze(), samplerate)
        
        return {
            "success": True,
            "message": "降噪处理完成",
            "processing_times": T_list,
            "total_frames": len(T_list)
        }
        
    except Exception as e:
        logger.error(f"音频降噪处理失败: {e}")
        return {
            "success": False,
            "message": f"处理失败: {str(e)}",
            "processing_times": [],
            "total_frames": 0
        }

def cleanup_temp_file(file_path: str):
    """清理临时文件"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"已清理临时文件: {file_path}")
    except Exception as e:
        logger.warning(f"清理临时文件失败: {e}")

# API路由
@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    try:
        init_model()
        logger.info("FastAPI服务器启动成功")
    except Exception as e:
        logger.error(f"服务器启动失败: {e}")
        raise

@app.get("/", response_model=dict)
async def root():
    """根路径"""
    return {
        "message": "音频降噪API服务",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查"""
    uptime = time.time() - start_time
    return HealthResponse(
        status="healthy" if session is not None else "unhealthy",
        model_loaded=session is not None,
        uptime=uptime
    )

@app.post("/denoise", response_model=DenoiseResponse)
async def denoise_audio(request: DenoiseRequest):
    """
    音频降噪处理接口
    
    参数:
        request: 降噪请求参数
        
    返回:
        DenoiseResponse: 处理结果
    """
    if session is None:
        raise HTTPException(status_code=500, detail="模型未初始化")
    
    # 检查输入文件是否存在
    if not os.path.exists(request.input_file):
        raise HTTPException(status_code=404, detail=f"输入文件不存在: {request.input_file}")
    
    # 生成输出文件路径
    if request.output_file is None:
        input_path = Path(request.input_file)
        output_file = str(input_path.parent / f"{input_path.stem}_denoised{input_path.suffix}")
    else:
        output_file = request.output_file
    
    # 记录开始时间
    start_time = time.time()
    
    try:
        # 执行降噪处理
        result = inference(request.input_file, output_file, request.samplerate)
        
        # 计算处理时间
        processing_time = time.time() - start_time
        
        if result["success"]:
            # 获取输出文件大小
            file_size = os.path.getsize(output_file) if os.path.exists(output_file) else None
            
            logger.info(f"音频降噪完成: {request.input_file} -> {output_file}, 耗时: {processing_time:.2f}s")
            
            return DenoiseResponse(
                success=True,
                message=result["message"],
                input_file=request.input_file,
                output_file=output_file,
                processing_time=processing_time,
                file_size=file_size
            )
        else:
            raise HTTPException(status_code=500, detail=result["message"])
            
    except Exception as e:
        processing_time = time.time() - start_time
        error_msg = f"音频降噪处理失败: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@app.post("/denoise/upload", response_model=DenoiseResponse)
async def denoise_upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="音频文件"),
    samplerate: int = 16000
):
    """
    上传音频文件进行降噪处理
    
    参数:
        file: 上传的音频文件
        samplerate: 采样率
        
    返回:
        DenoiseResponse: 处理结果
    """
    if session is None:
        raise HTTPException(status_code=500, detail="模型未初始化")
    
    # 检查文件类型
    if not file.filename.lower().endswith(('.wav', '.mp3', '.flac', '.m4a')):
        raise HTTPException(status_code=400, detail="不支持的文件格式，请上传WAV、MP3、FLAC或M4A文件")
    
    # 生成临时文件路径
    temp_id = str(uuid.uuid4())
    temp_input = os.path.join(temp_dir, f"input_{temp_id}_{file.filename}")
    temp_output = os.path.join(temp_dir, f"output_{temp_id}_{file.filename}")
    
    try:
        # 保存上传的文件
        with open(temp_input, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 记录开始时间
        start_time = time.time()
        
        # 执行降噪处理
        result = inference(temp_input, temp_output, samplerate)
        
        # 计算处理时间
        processing_time = time.time() - start_time
        
        if result["success"]:
            # 获取输出文件大小
            file_size = os.path.getsize(temp_output) if os.path.exists(temp_output) else None
            
            logger.info(f"上传文件降噪完成: {file.filename}, 耗时: {processing_time:.2f}s")
            
            # 添加后台任务清理临时文件
            # 仅清理输入临时文件，输出文件保留用于后续下载
            background_tasks.add_task(cleanup_temp_file, temp_input)
            
            return DenoiseResponse(
                success=True,
                message=result["message"],
                input_file=file.filename,
                output_file=temp_output,
                processing_time=processing_time,
                file_size=file_size
            )
        else:
            raise HTTPException(status_code=500, detail=result["message"])
            
    except Exception as e:
        processing_time = time.time() - start_time
        error_msg = f"上传文件降噪处理失败: {str(e)}"
        logger.error(error_msg)
        
        # 清理临时文件（在失败情况下同时清理输入与输出）
        background_tasks.add_task(cleanup_temp_file, temp_input)
        background_tasks.add_task(cleanup_temp_file, temp_output)
        
        raise HTTPException(status_code=500, detail=error_msg)

@app.get("/download/{file_id}")
async def download_file(file_id: str):
    """
    下载处理后的音频文件
    
    参数:
        file_id: 文件ID（临时文件名）
        
    返回:
        FileResponse: 音频文件
    """
    # 防御性检查
    if temp_dir is None:
        raise HTTPException(status_code=500, detail="临时目录未初始化")
    
    file_path = os.path.join(temp_dir, file_id)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在或已过期")
    
    return FileResponse(
        path=file_path,
        filename=os.path.basename(file_path),
        media_type="audio/wav"
    )

@app.get("/models/info")
async def model_info():
    """获取模型信息"""
    if session is None:
        raise HTTPException(status_code=500, detail="模型未初始化")
    
    return {
        "model_loaded": True,
        "providers": session.get_providers(),
        "input_names": [input.name for input in session.get_inputs()],
        "output_names": [output.name for output in session.get_outputs()]
    }

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="音频降噪FastAPI服务器")
    parser.add_argument("--host", default="0.0.0.0", help="服务器地址")
    parser.add_argument("--port", type=int, default=8000, help="服务器端口")
    parser.add_argument("--reload", action="store_true", help="开发模式（自动重载）")
    
    args = parser.parse_args()
    
    print(f"启动音频降噪API服务器...")
    print(f"地址: http://{args.host}:{args.port}")
    print(f"文档: http://{args.host}:{args.port}/docs")
    
    uvicorn.run(
        "api_server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info"
    )
