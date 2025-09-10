# -*- coding: utf-8 -*-
"""
FastAPI服务器启动脚本
功能：启动音频降噪API服务
作者：天聪语音智能软件公司
"""

import os
import sys
import argparse
import uvicorn

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="启动音频降噪FastAPI服务器")
    parser.add_argument("--host", default="0.0.0.0", help="服务器地址 (默认: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="服务器端口 (默认: 8000)")
    parser.add_argument("--reload", action="store_true", help="开发模式（自动重载）")
    parser.add_argument("--workers", type=int, default=1, help="工作进程数 (默认: 1)")
    parser.add_argument("--log-level", default="info", choices=["debug", "info", "warning", "error"], help="日志级别")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("音频降噪FastAPI服务器")
    print("=" * 60)
    print(f"服务器地址: http://{args.host}:{args.port}")
    print(f"API文档: http://{args.host}:{args.port}/docs")
    print(f"ReDoc文档: http://{args.host}:{args.port}/redoc")
    print(f"健康检查: http://{args.host}:{args.port}/health")
    print("=" * 60)
    
    if args.reload:
        print("开发模式: 启用自动重载")
    else:
        print(f"生产模式: {args.workers} 个工作进程")
    
    print("\n正在启动服务器...")
    
    try:
        uvicorn.run(
            "api_server:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
            workers=args.workers if not args.reload else 1,
            log_level=args.log_level,
            access_log=True
        )
    except KeyboardInterrupt:
        print("\n服务器已停止")
    except Exception as e:
        print(f"服务器启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
