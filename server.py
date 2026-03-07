# -*- coding: utf-8 -*-
"""
Web 服务器入口

使用 server 包提供的应用工厂创建 Flask 应用
"""

import os
import sys
from server import create_app, compress_static_files


def is_reloader_process():
    """检查是否是 Flask reloader 子进程"""
    # Flask debug 模式会设置此环境变量为 "true"
    return os.environ.get("WERKZEUG_RUN_MAIN") == "true"


if __name__ == "__main__":
    # 只在主进程（非 reloader 子进程）时压缩静态文件
    if not is_reloader_process():
        compress_static_files()

    app = create_app()
    
    # 检查是否使用 waitress
    if len(sys.argv) > 1 and sys.argv[1] == "--waitress":
        from waitress import serve
        print("使用 Waitress 生产服务器启动...")
        serve(app, host="127.0.0.1", port=5000, threads=4)
    else:
        app.run(debug=True, port=5000)
