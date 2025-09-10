# 音频降噪服务测试

本目录包含用于测试音频降噪服务的客户端代码和测试工具，支持UDP和FastAPI两种服务模式。

## 文件说明

### UDP服务测试
- `udp_client.py` - UDP客户端测试程序
- `run_tests.py` - UDP服务批量测试脚本
- `run_tests.bat` - Windows批处理测试脚本

### FastAPI服务测试
- `api_client.py` - FastAPI客户端测试程序
- `test_api.py` - FastAPI服务批量测试脚本

### 通用工具
- `generate_test_audio.py` - 测试音频生成脚本
- `README.md` - 本说明文档

## 快速开始

### 1. 启动服务器

#### UDP服务模式
```bash
# 在项目根目录下运行
python server.py
```
服务器将在端口7000上监听UDP连接。

#### FastAPI服务模式
```bash
# 在项目根目录下运行
python api_server.py
# 或者使用启动脚本
python start_api_server.py
```
服务器将在端口8000上提供HTTP API服务。

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 生成测试音频

```bash
# 生成测试音频文件
python tests/generate_test_audio.py
```

这将在 `test_audio/` 目录下生成多个测试音频文件。

### 4. 运行客户端测试

#### UDP服务测试
```bash
# 测试连接
python tests/udp_client.py --test-only

# 发送降噪请求
python tests/udp_client.py --input test_audio/short_clean.wav

# 批量测试
python tests/run_tests.py
```

#### FastAPI服务测试
```bash
# 测试连接和健康检查
python tests/api_client.py --test-only

# 文件路径模式降噪
python tests/api_client.py --input test_audio/short_clean.wav

# 上传模式降噪
python tests/api_client.py --input test_audio/medium_noisy.wav --upload

# 批量测试
python tests/test_api.py
```

#### 完整参数测试
```bash
# UDP服务
python tests/udp_client.py --host 192.168.1.100 --port 7000 --input test_audio/long_very_noisy.wav

# FastAPI服务
python tests/api_client.py --url http://192.168.1.100:8000 --input test_audio/long_very_noisy.wav
```

## 客户端参数说明

### UDP客户端 (udp_client.py)
| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--host` | 服务器地址 | localhost |
| `--port` | 服务器端口 | 7000 |
| `--input` | 输入音频文件路径 | 必需 |
| `--output` | 输出音频文件路径 | 自动生成 |
| `--test-only` | 仅测试连接 | False |

### FastAPI客户端 (api_client.py)
| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--url` | API服务器URL | http://localhost:8000 |
| `--input` | 输入音频文件路径 | 必需 |
| `--output` | 输出音频文件路径 | 自动生成 |
| `--upload` | 使用上传模式 | False |
| `--samplerate` | 采样率 | 16000 |
| `--test-only` | 仅测试连接 | False |

## 测试流程

1. **连接测试**: 客户端首先测试与服务器的连接
2. **文件检查**: 验证输入文件是否存在
3. **发送请求**: 向服务器发送降噪请求
4. **等待响应**: 等待服务器处理完成并返回结果
5. **结果验证**: 检查输出文件是否生成

## 预期结果

### 成功情况
```
==================================================
音频降噪UDP客户端测试程序
==================================================
测试服务器连接: localhost:7000
服务器连接正常（无响应是正常的，因为测试消息格式不正确）
客户端已初始化，目标服务器: localhost:7000
发送降噪请求...
输入文件: test_audio/short_clean.wav
输出文件: test_audio/short_clean_denoised.wav

==============================
处理结果:
==============================
状态: 成功
消息: success
耗时: 2.34秒
降噪完成！输出文件: test_audio/short_clean_denoised.wav
输出文件大小: 160044 字节
客户端连接已关闭
```

### 失败情况
```
状态: 失败
消息: 输入文件不存在: nonexistent.wav
耗时: 0.00秒
降噪失败，请检查错误信息
```

## 故障排除

### 常见问题

1. **连接超时**
   - 检查服务器是否启动
   - 确认端口7000未被占用
   - 检查防火墙设置

2. **文件不存在**
   - 确认输入文件路径正确
   - 检查文件权限

3. **服务器无响应**
   - 检查服务器日志
   - 确认ONNX模型文件存在
   - 检查音频文件格式是否支持

### 调试模式

可以通过修改客户端代码中的超时时间来调试：

```python
# 在 udp_client.py 中修改
self.client_socket.settimeout(60.0)  # 增加超时时间
```

## 性能测试

可以使用不同大小的音频文件测试服务器性能：

```bash
# 测试短音频
python udp_client.py --input test_audio/short_clean.wav

# 测试长音频
python udp_client.py --input test_audio/long_very_noisy.wav
```

## FastAPI服务API文档

### 主要端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 服务信息 |
| `/health` | GET | 健康检查 |
| `/docs` | GET | Swagger API文档 |
| `/redoc` | GET | ReDoc API文档 |
| `/denoise` | POST | 文件路径模式降噪 |
| `/denoise/upload` | POST | 上传文件降噪 |
| `/download/{file_id}` | GET | 下载处理后的文件 |
| `/models/info` | GET | 模型信息 |

### 请求示例

#### 文件路径模式
```bash
curl -X POST "http://localhost:8000/denoise" \
     -H "Content-Type: application/json" \
     -d '{
       "input_file": "test_audio/short_clean.wav",
       "samplerate": 16000
     }'
```

#### 上传模式
```bash
curl -X POST "http://localhost:8000/denoise/upload" \
     -F "file=@test_audio/short_clean.wav" \
     -F "samplerate=16000"
```

## 注意事项

1. 确保服务器有足够的内存处理音频文件
2. 大文件可能需要较长的处理时间
3. 输出目录会自动创建
4. 支持WAV、MP3、FLAC、M4A格式的音频文件
5. 建议采样率为16kHz
6. FastAPI服务提供自动生成的API文档
7. 上传模式支持临时文件自动清理

## 扩展测试

可以创建更多测试用例：

```python
# 在 generate_test_audio.py 中添加更多测试场景
test_cases = [
    ("silence.wav", 3.0, 16000, 0.0),      # 静音测试
    ("pure_noise.wav", 5.0, 16000, 1.0),   # 纯噪声测试
    # ... 更多测试用例
]
```
