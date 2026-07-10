#!/usr/bin/env python3
"""
Education React 前端开发服务启动脚本
用法:
    python run_server.py                  # 默认端口 3000，绑定 0.0.0.0
    python run_server.py --port 5173      # 指定端口
    python run_server.py --no-host        # 不绑定 0.0.0.0，仅 localhost
    python run_server.py --clear          # 先清理 node_modules 并重装依赖
    python run_server.py --build          # 仅执行生产构建，不启动开发服务器
    python run_server.py --preview        # 构建后用 vite preview 预览
    python run_server.py --kill-all       # 杀掉所有 node.exe 进程

从其他 Python 脚本调用:
    from run_server import main
    main(port=5173, host=True)             # 指定端口，绑定 0.0.0.0
    main(build=True)                       # 仅构建
    main(port=3000, strict_port=True)      # 强制使用指定端口
"""

import argparse
import ctypes
import os
import subprocess
import sys
from pathlib import Path

# ── 定位项目目录 ──
SCRIPT_DIR = Path(__file__).resolve().parent
os.chdir(SCRIPT_DIR)

# ── 颜色输出 ──
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def info(msg: str):
    print(f"{CYAN}[INFO]{RESET} {msg}")


def ok(msg: str):
    print(f"{GREEN}[OK]{RESET} {msg}")


def warn(msg: str):
    print(f"{YELLOW}[WARN]{RESET} {msg}")


def error(msg: str):
    print(f"{RED}[ERROR]{RESET} {msg}")


# ── 权限检查（Windows） ──
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


# ── 端口占用检查 ──
def is_port_in_use(port: int) -> bool:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


# ── 杀掉占用端口的进程 ──
def kill_port(port: int):
    try:
        result = subprocess.run(
            "netstat -ano", capture_output=True, text=True, shell=True
        )
        for line in result.stdout.splitlines():
            if f":{port}" in line and "LISTENING" in line:
                parts = line.split()
                pid = parts[-1]
                try:
                    subprocess.run(
                        f"taskkill /F /PID {pid}",
                        capture_output=True, shell=True,
                    )
                    ok(f"已释放端口 {port} (PID {pid})")
                except Exception:
                    warn(f"无法释放端口，PID {pid}")
                return
    except Exception:
        pass


# ── 杀掉所有 node 进程 ──
def kill_all_node():
    try:
        result = subprocess.run(
            "taskkill /F /IM node.exe",
            capture_output=True, text=True, shell=True
        )
        if "成功" in result.stdout or "SUCCESS" in result.stdout:
            ok("已关闭所有 node.exe 进程")
        elif "没有运行的实例" in result.stdout or "找不到" in result.stdout:
            info("没有找到运行中的 node.exe 进程")
        else:
            info(result.stdout.strip())
    except Exception as e:
        error(f"关闭进程失败: {e}")


# ── 检查依赖 ──
def check_node():
    try:
        subprocess.run("node --version", capture_output=True, check=True, shell=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        error("未找到 Node.js，请先安装: https://nodejs.org/")
        sys.exit(1)


def check_dependencies():
    check_node()
    node_modules = SCRIPT_DIR / "node_modules"
    if not node_modules.exists():
        warn("node_modules 不存在，正在安装依赖...")
        subprocess.run("npm install", shell=True, check=True)
        ok("依赖安装完成")
    elif not (SCRIPT_DIR / "package-lock.json").exists():
        warn("重新安装依赖...")
        subprocess.run("npm install", shell=True, check=True)
        ok("依赖安装完成")


# ── 清除安装 ──
def do_clear_install():
    node_modules = SCRIPT_DIR / "node_modules"
    if node_modules.exists():
        info("清除 node_modules...")
        subprocess.run(["rmdir", "/S", "/Q", str(node_modules)], shell=True)
    lock = SCRIPT_DIR / "package-lock.json"
    if lock.exists():
        lock.unlink()
    info("重新安装依赖...")
    subprocess.run("npm install", shell=True, check=True)
    ok("清理安装完成")


# ── 构建 ──
def do_build():
    info("开始生产构建...")
    subprocess.run("npm run build", shell=True, check=True)
    ok("构建完成，输出目录: dist/")


# ── 预览 ──
def do_preview(port: int):
    do_build()
    info(f"启动预览服务器 http://localhost:{port} ...")
    subprocess.run(f"npx vite preview --port {port}", shell=True, check=True)


# ── 开发服务器 ──
def run_dev(port: int, host: bool, strict_port: bool):
    check_dependencies()

    if is_port_in_use(port):
        warn(f"端口 {port} 已被占用")
        if not strict_port:
            info("Vite 将自动尝试其他端口...")
        else:
            info(f"正在释放端口 {port}...")
            kill_port(port)

    cmd = f"npx vite --port {port}"
    if host:
        cmd += " --host"

    info(f"启动开发服务器 http://localhost:{port}")
    if host:
        info("已启用 --host，局域网可访问")

    try:
        subprocess.run(cmd, shell=True)
    except KeyboardInterrupt:
        ok("\n开发服务器已停止")


# ── 主函数 ──
def main(
    port: int | None = None,
    host: bool | None = None,       # None / True(默认) / False(--no-host)
    strict_port: bool = False,
    build: bool = False,
    preview: bool = False,
    clear: bool = False,
    kill_all: bool = False,
):
    # When called from CLI, parse args; kwargs override
    args = None
    if not any(v is not None for v in [port, host, strict_port, build, preview, clear, kill_all]):
        parser = argparse.ArgumentParser(
            description="Education React 前端开发服务管理脚本",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
示例:
  python run_server.py                  默认端口 3000 启动 (0.0.0.0)
  python run_server.py --port 8080      指定端口 8080
  python run_server.py --port 8080 --no-host  不绑定 0.0.0.0
  python run_server.py --build          仅构建生产版本
  python run_server.py --preview        构建并预览
  python run_server.py --clear          清理依赖后启动
  python run_server.py --kill-all       杀掉所有 node 进程
            """,
        )
        parser.add_argument("--port", "-p", type=int, default=3000, help="服务端口号 (默认: 3000)")
        parser.add_argument("--no-host", action="store_true", help="不绑定 0.0.0.0，仅监听 localhost")
        parser.add_argument("--strict-port", action="store_true", help="端口被占用时强制释放，不自动切换")
        parser.add_argument("--build", action="store_true", help="仅执行生产构建")
        parser.add_argument("--preview", action="store_true", help="构建后用 vite preview 预览")
        parser.add_argument("--clear", action="store_true", help="清除 node_modules 并重装依赖")
        parser.add_argument("--kill-all", action="store_true", help="杀掉所有 node.exe 进程")
        args = parser.parse_args()

    # Resolve values: kwargs > CLI args > defaults
    p_port = port if port is not None else (args.port if args else 3000)
    p_host = host if host is not None else (not args.no_host if args else True)
    p_strict = strict_port if strict_port is not None else (args.strict_port if args else False)
    p_build = build if build else (args.build if args else False)
    p_preview = preview if preview else (args.preview if args else False)
    p_clear = clear if clear else (args.clear if args else False)
    p_kill_all = kill_all if kill_all else (args.kill_all if args else False)

    if p_kill_all:
        kill_all_node()
        return

    if p_clear:
        do_clear_install()
        if p_build:
            do_build()
            return
        elif p_preview:
            do_preview(p_port)
            return

    if p_build:
        do_build()
        return

    if p_preview:
        do_preview(p_port)
        return

    run_dev(p_port, p_host, p_strict)


if __name__ == "__main__":
    main()
