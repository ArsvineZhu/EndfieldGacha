# -*- coding: utf-8 -*-
"""统一入口：快速运行演示、策略评估、概率验证或启动 Web 服务。"""
import os
import sys


def _show_help():
    print(__doc__)
    print()
    print("用法:")
    print("  uv run run.py                   显示帮助")
    print("  uv run run.py demo              抽卡演示与统计")
    print("  uv run run.py eval              策略评估（批量模拟多种策略）")
    print("  uv run run.py exam              概率验证")
    print("  uv run run.py server            启动 Web 服务 (http://localhost:5000)")
    print("  uv run run.py server --dev      开发模式，跳过静态资源压缩")
    print("  uv run run.py server --waitress --port 5000  使用 Waitress 生产服务器")


def _run_server():
    """解析 server 子命令参数并启动 Web 服务。"""
    dev_mode = "--dev" in sys.argv
    use_waitress = "--waitress" in sys.argv

    port = 5000
    for i, arg in enumerate(sys.argv):
        if arg == "--port" and i + 1 < len(sys.argv):
            try:
                port = int(sys.argv[i + 1])
            except ValueError:
                pass

    from web import compress_static_files, create_app

    if not dev_mode and not _is_reloader_process():
        compress_static_files()

    app = create_app(dev_mode=dev_mode)

    if use_waitress:
        from waitress import serve

        print(f"使用 Waitress 生产服务器启动，端口：{port}")
        app.debug = False
        serve(
            app,
            host="0.0.0.0",
            port=port,
            threads=16,
            connection_limit=64,
            asyncore_use_poll=os.name != "nt",
            max_request_body_size=10 * 1024 * 1024,
            ident="GachaSimServer",
            expose_tracebacks=False,
            channel_timeout=60,
        )
    else:
        if dev_mode:
            print(f"开发模式启动，端口：{port}，静态资源不压缩，便于调试")
        app.run(debug=True, host="0.0.0.0", port=port)


def _is_reloader_process():
    """检查是否是 Flask reloader 子进程"""
    return os.environ.get("WERKZEUG_RUN_MAIN") == "true"


def main():
    if len(sys.argv) < 2:
        _show_help()
        return

    cmd = sys.argv[1].lower()

    if cmd == "demo":
        import runpy

        runpy.run_path(
            os.path.join(os.path.dirname(__file__), "cli", "demo.py"),
            run_name="__main__",
        )
    elif cmd == "eval":
        import runpy

        runpy.run_path(
            os.path.join(os.path.dirname(__file__), "cli", "evaluation.py"),
            run_name="__main__",
        )
    elif cmd == "exam":
        import runpy

        runpy.run_path(
            os.path.join(os.path.dirname(__file__), "cli", "examination.py"),
            run_name="__main__",
        )
    elif cmd == "server":
        _run_server()
    else:
        print(f"未知命令: {cmd}")
        _show_help()


if __name__ == "__main__":
    main()
