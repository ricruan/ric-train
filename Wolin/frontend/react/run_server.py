#!/usr/bin/env python3
"""
AI 面试系统 — 前端 Monorepo 开发服务启动脚本

支持同时启动用户侧（:3000）和管理侧（:3001）两个 Vite 开发服务器。

用法:
    python run_server.py                  # 同时启动 user(:3000) + admin(:3001)
    python run_server.py --user-only      # 仅启动用户侧
    python run_server.py --admin-only     # 仅启动管理侧
    python run_server.py --user-port 8000 # 自定义用户侧端口
    python run_server.py --admin-port 8001# 自定义管理侧端口
    python run_server.py --no-host        # 不绑定 0.0.0.0，仅 localhost
    python run_server.py --clear          # 清理 node_modules 并重装依赖
    python run_server.py --build          # 仅执行生产构建（两端）
    python run_server.py --kill-all       # 杀掉所有 node.exe 进程

从其他 Python 脚本调用:
    from run_server import main
    main()                                  # 同时启动两端
    main(user_only=True)                    # 仅用户侧
    main(admin_only=True, admin_port=8080)  # 仅管理侧，指定端口
    main(build=True)                        # 仅构建
"""

import argparse
import ctypes
import io
import os
import signal
import socket
import subprocess
import sys
import threading
from pathlib import Path

# ── 修复 Windows 控制台编码 ──
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# ── 定位项目目录 ──
SCRIPT_DIR = Path(__file__).resolve().parent
os.chdir(SCRIPT_DIR)

# ── 颜色输出 ──
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
RESET = "\033[0m"


def info(msg: str):
    print(f"{CYAN}[INFO]{RESET} {msg}")


def ok(msg: str):
    print(f"{GREEN}[ OK ]{RESET} {msg}")


def warn(msg: str):
    print(f"{YELLOW}[WARN]{RESET} {msg}")


def error(msg: str):
    print(f"{RED}[ERR ]{RESET} {msg}")


def user_tag(msg: str):
    print(f"{CYAN}[USER :{msg}]{RESET}")


def admin_tag(msg: str):
    print(f"{MAGENTA}[ADMIN]{RESET} {msg}")


# ── 权限检查（Windows） ──
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


# ── 端口占用检查 ──
def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
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


def check_pnpm():
    try:
        result = subprocess.run(
            "pnpm --version", capture_output=True, text=True, shell=True
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def ensure_pnpm():
    """确保 pnpm 已安装，未安装则自动安装"""
    version = check_pnpm()
    if version:
        info(f"pnpm {version} 已就绪")
        return

    warn("未找到 pnpm，正在安装...")
    try:
        subprocess.run("npm install -g pnpm", shell=True, check=True)
        ok("pnpm 安装完成")
    except subprocess.CalledProcessError:
        error("pnpm 安装失败，请手动安装: npm install -g pnpm")
        sys.exit(1)


def check_dependencies():
    check_node()
    ensure_pnpm()

    node_modules = SCRIPT_DIR / "node_modules"
    if not node_modules.exists():
        warn("node_modules 不存在，正在安装依赖...")
        subprocess.run("pnpm install", shell=True, check=True, cwd=str(SCRIPT_DIR))
        ok("依赖安装完成")
    elif not (SCRIPT_DIR / "pnpm-lock.yaml").exists():
        warn("pnpm-lock.yaml 不存在，重新安装依赖...")
        subprocess.run("pnpm install", shell=True, check=True, cwd=str(SCRIPT_DIR))
        ok("依赖安装完成")


# ── 清除安装 ──
def do_clear_install():
    # 清理根目录和所有 workspace 的 node_modules
    for dir_path in [
        SCRIPT_DIR / "node_modules",
        SCRIPT_DIR / "apps" / "user" / "node_modules",
        SCRIPT_DIR / "apps" / "admin" / "node_modules",
        SCRIPT_DIR / "packages" / "shared" / "node_modules",
    ]:
        if dir_path.exists():
            info(f"清除 {dir_path.relative_to(SCRIPT_DIR)}...")
            subprocess.run(["rmdir", "/S", "/Q", str(dir_path)], shell=True)

    lock = SCRIPT_DIR / "pnpm-lock.yaml"
    if lock.exists():
        lock.unlink()

    info("重新安装依赖...")
    subprocess.run("pnpm install", shell=True, check=True, cwd=str(SCRIPT_DIR))
    ok("清理安装完成")


# ── 构建 ──
def do_build():
    info("开始生产构建（双端）...")
    subprocess.run("pnpm run build", shell=True, check=True, cwd=str(SCRIPT_DIR))
    ok("构建完成")
    ok(f"  用户侧: apps/user/dist/")
    ok(f"  管理侧: apps/admin/dist/")


# ── 预览 ──
def do_preview(user_port: int, admin_port: int):
    do_build()
    info("启动预览服务器...")
    info(f"  用户侧: http://localhost:{user_port}")
    info(f"  管理侧: http://localhost:{admin_port}")

    procs = []
    try:
        p_user = subprocess.Popen(
            f"pnpm --filter @interview/user exec vite preview --port {user_port}",
            shell=True, cwd=str(SCRIPT_DIR),
        )
        procs.append(p_user)

        p_admin = subprocess.Popen(
            f"pnpm --filter @interview/admin exec vite preview --port {admin_port}",
            shell=True, cwd=str(SCRIPT_DIR),
        )
        procs.append(p_admin)

        for p in procs:
            p.wait()
    except KeyboardInterrupt:
        for p in procs:
            p.terminate()
        ok("\n预览服务器已停止")


# ── 启动单个 dev server ──
def run_single_dev(
    app_name: str,
    filter_name: str,
    port: int,
    host: bool,
    strict_port: bool,
    tag_fn,
):
    """启动单个应用的 dev server"""
    if is_port_in_use(port):
        warn(f"端口 {port} 已被占用")
        if strict_port:
            info(f"正在释放端口 {port}...")
            kill_port(port)
        else:
            info("Vite 将自动尝试其他端口...")

    cmd = f"pnpm --filter {filter_name} exec vite --port {port}"
    if host:
        cmd += " --host"

    tag_fn(f"启动 http://localhost:{port}")
    if host:
        tag_fn("已启用 --host，局域网可访问")

    try:
        subprocess.run(cmd, shell=True, cwd=str(SCRIPT_DIR))
    except KeyboardInterrupt:
        tag_fn("开发服务器已停止")


# ── 同时启动双端 ──
def run_dual_dev(
    user_port: int,
    admin_port: int,
    host: bool,
    strict_port: bool,
):
    """同时启动 user 和 admin 两个 dev server"""
    # 检查端口
    for port, name in [(user_port, "user"), (admin_port, "admin")]:
        if is_port_in_use(port):
            warn(f"{name} 端口 {port} 已被占用")
            if strict_port:
                info(f"正在释放端口 {port}...")
                kill_port(port)
            else:
                info("Vite 将自动尝试其他端口...")

    host_flag = " --host" if host else ""

    user_cmd = f"pnpm --filter @interview/user exec vite --port {user_port}{host_flag}"
    admin_cmd = f"pnpm --filter @interview/admin exec vite --port {admin_port}{host_flag}"

    print()
    print(f"{BOLD}{'=' * 56}{RESET}")
    print(f"{BOLD}  🎯 AI 面试系统 — 前端开发服务器{RESET}")
    print(f"{BOLD}{'=' * 56}{RESET}")
    print(f"  {CYAN}用户侧{RESET}  → http://localhost:{user_port}")
    print(f"  {MAGENTA}管理侧{RESET}  → http://localhost:{admin_port}")
    if host:
        print(f"  {YELLOW}--host{RESET}   已启用，局域网可访问")
    print(f"{BOLD}{'─' * 56}{RESET}")
    print(f"  按 {BOLD}Ctrl+C{RESET} 停止所有服务器")
    print(f"{BOLD}{'=' * 56}{RESET}")
    print()

    procs = []
    try:
        p_user = subprocess.Popen(
            user_cmd, shell=True, cwd=str(SCRIPT_DIR),
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        procs.append(("user", p_user))

        p_admin = subprocess.Popen(
            admin_cmd, shell=True, cwd=str(SCRIPT_DIR),
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        procs.append(("admin", p_admin))

        # 实时输出两个 server 的日志（带颜色前缀）
        def stream_output(proc, tag_fn):
            for line in iter(proc.stdout.readline, b""):
                text = line.decode("utf-8", errors="replace").rstrip()
                if text:
                    tag_fn(text)

        threads = []
        for name, proc in procs:
            tag_fn = user_tag if name == "user" else admin_tag
            t = threading.Thread(target=stream_output, args=(proc, tag_fn), daemon=True)
            t.start()
            threads.append(t)

        # 等待进程结束
        for _, proc in procs:
            proc.wait()

    except KeyboardInterrupt:
        print()
        ok("正在停止所有服务器...")
        for name, proc in procs:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except Exception:
                proc.kill()
        ok("所有服务器已停止")


# ── 主函数 ──
def main(
    user_port: int | None = None,
    admin_port: int | None = None,
    user_only: bool = False,
    admin_only: bool = False,
    host: bool | None = None,
    strict_port: bool = False,
    build: bool = False,
    preview: bool = False,
    clear: bool = False,
    kill_all: bool = False,
):
    """
    启动前端开发服务。

    Args:
        user_port:    用户侧端口 (默认 3000)
        admin_port:   管理侧端口 (默认 3001)
        user_only:    仅启动用户侧
        admin_only:   仅启动管理侧
        host:         绑定 0.0.0.0 (默认 True)
        strict_port:  端口被占用时强制释放
        build:        仅执行生产构建
        preview:      构建后预览
        clear:        清理依赖后启动
        kill_all:     杀掉所有 node 进程
    """
    # CLI 参数解析（仅在直接运行时）
    args = None
    cli_kwargs = {
        "user_port": user_port, "admin_port": admin_port,
        "user_only": user_only, "admin_only": admin_only,
        "host": host, "strict_port": strict_port,
        "build": build, "preview": preview,
        "clear": clear, "kill_all": kill_all,
    }
    # 如果所有参数都是默认值，则解析命令行
    if all(v is None or v is False for v in cli_kwargs.values()):
        parser = argparse.ArgumentParser(
            description="AI 面试系统 — 前端 Monorepo 开发服务管理脚本",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
示例:
  python run_server.py                       同时启动 user(:3000) + admin(:3001)
  python run_server.py --user-only           仅启动用户侧
  python run_server.py --admin-only          仅启动管理侧
  python run_server.py --user-port 8000      自定义用户侧端口
  python run_server.py --build               仅构建生产版本
  python run_server.py --preview             构建并预览
  python run_server.py --clear               清理依赖后启动
  python run_server.py --kill-all            杀掉所有 node 进程
            """,
        )
        parser.add_argument("--user-port", type=int, default=3000, help="用户侧端口 (默认: 3000)")
        parser.add_argument("--admin-port", type=int, default=3001, help="管理侧端口 (默认: 3001)")
        parser.add_argument("--user-only", action="store_true", help="仅启动用户侧")
        parser.add_argument("--admin-only", action="store_true", help="仅启动管理侧")
        parser.add_argument("--no-host", action="store_true", help="不绑定 0.0.0.0，仅 localhost")
        parser.add_argument("--strict-port", action="store_true", help="端口被占用时强制释放")
        parser.add_argument("--build", action="store_true", help="仅执行生产构建")
        parser.add_argument("--preview", action="store_true", help="构建后预览")
        parser.add_argument("--clear", action="store_true", help="清除 node_modules 并重装")
        parser.add_argument("--kill-all", action="store_true", help="杀掉所有 node.exe 进程")
        args = parser.parse_args()

    # 解析值：kwargs > CLI > defaults
    p_user_port = user_port if user_port is not None else (args.user_port if args else 3000)
    p_admin_port = admin_port if admin_port is not None else (args.admin_port if args else 3001)
    p_user_only = user_only or (args.user_only if args else False)
    p_admin_only = admin_only or (args.admin_only if args else False)
    p_host = host if host is not None else (not args.no_host if args else True)
    p_strict = strict_port or (args.strict_port if args else False)
    p_build = build or (args.build if args else False)
    p_preview = preview or (args.preview if args else False)
    p_clear = clear or (args.clear if args else False)
    p_kill_all = kill_all or (args.kill_all if args else False)

    if p_kill_all:
        kill_all_node()
        return

    if p_clear:
        do_clear_install()
        if p_build:
            do_build()
            return
        elif p_preview:
            do_preview(p_user_port, p_admin_port)
            return

    if p_build:
        do_build()
        return

    if p_preview:
        do_preview(p_user_port, p_admin_port)
        return

    # 开发服务器
    check_dependencies()

    if p_user_only:
        run_single_dev("user", "@interview/user", p_user_port, p_host, p_strict, user_tag)
    elif p_admin_only:
        run_single_dev("admin", "@interview/admin", p_admin_port, p_host, p_strict, admin_tag)
    else:
        run_dual_dev(p_user_port, p_admin_port, p_host, p_strict)


if __name__ == "__main__":
    main()
