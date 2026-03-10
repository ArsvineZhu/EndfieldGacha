# -*- coding: utf-8 -*-
"""
Web 服务器入口

使用 server 包提供的应用工厂创建 Flask 应用
"""

import os
import sys
import argparse
from server import create_app, compress_static_files


def is_reloader_process():
    """检查是否是 Flask reloader 子进程"""
    # Flask debug 模式会设置此环境变量为 "true"
    return os.environ.get("WERKZEUG_RUN_MAIN") == "true"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="终末地抽卡模拟器服务器")
    parser.add_argument(
        "--dev", action="store_true", help="开发模式：不压缩静态资源，使用源文件调试"
    )
    parser.add_argument(
        "--waitress", action="store_true", help="使用Waitress生产服务器"
    )
    parser.add_argument("--port", type=int, default=5000, help="服务端口，默认5000")
    args = parser.parse_args()

    # 非开发模式且不是reloader子进程时压缩静态文件
    if not args.dev and not is_reloader_process():
        compress_static_files()

    # 创建应用，传入开发模式参数
    app = create_app(dev_mode=args.dev)

    if args.waitress:
        from waitress import serve

        print(f"使用 Waitress 生产服务器启动，端口：{args.port}")
        serve(app, host="0.0.0.0", port=args.port, threads=16)
    else:
        if args.dev:
            print(f"开发模式启动，端口：{args.port}，静态资源不压缩，便于调试")
        app.run(debug=True, host="0.0.0.0", port=args.port)
