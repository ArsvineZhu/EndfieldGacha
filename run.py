# -*- coding: utf-8 -*-
"""统一入口：快速运行演示、策略评估、概率验证或启动 Web 服务。

用法:
    python run.py              # 显示帮助
    python run.py demo         # 抽卡演示与统计
    python run.py eval         # 策略评估
    python run.py exam         # 概率分布验证
    python run.py server       # 启动 Web 服务
"""
import sys
import os


def _show_help():
    print(__doc__)
    print("快捷命令:")
    print("  python run.py demo         - 抽卡演示（120抽角色 + 8次武器申领）")
    print("  python run.py eval         - 策略评估（批量模拟多种策略）")
    print("  python run.py exam         - 概率验证（验证卡池概率分布）")
    print("  python run.py server       - 启动 Web 服务（http://localhost:5000）")


def main():
    if len(sys.argv) < 2:
        _show_help()
        return

    cmd = sys.argv[1].lower()
    rest = sys.argv[2:]

    if cmd == "demo":
        import runpy

        runpy.run_path(
            os.path.join(os.path.dirname(__file__), "tools", "demo.py"),
            run_name="__main__",
        )
    elif cmd == "eval":
        import runpy

        runpy.run_path(
            os.path.join(os.path.dirname(__file__), "tools", "evaluation.py"),
            run_name="__main__",
        )
    elif cmd == "exam":
        import runpy

        runpy.run_path(
            os.path.join(os.path.dirname(__file__), "tools", "examination.py"),
            run_name="__main__",
        )
    elif cmd == "server":
        from server import compress_static_files, create_app

        compress_static_files()
        app = create_app()
        app.run(debug=False, port=5000)
    else:
        print(f"未知命令: {cmd}")
        _show_help()


if __name__ == "__main__":
    main()
