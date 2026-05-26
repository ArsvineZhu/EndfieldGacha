import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from typing import Any

import rcssmin

STATIC_DIR = "web/static"
MANIFEST_FILE = "web/static/manifest.json"


def get_file_hash(content):
    """使用 SHA256 生成哈希值"""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:6]


def obfuscate_js(input_path, output_path):
    terser_bin = shutil.which("terser") or shutil.which("terser.cmd") or "terser"
    npx_bin = shutil.which("npx") or shutil.which("npx.cmd") or "npx"
    commands = [
        [
            terser_bin,
            input_path,
            "--output",
            output_path,
            "--compress",
            "--mangle",
            "--toplevel",
        ],
        [
            npx_bin,
            "--yes",
            "terser",
            input_path,
            "--output",
            output_path,
            "--compress",
            "--mangle",
            "--toplevel",
        ],
    ]

    try:
        # 确保输出目录存在
        output_dir = os.path.dirname(output_path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        last_error = None
        for cmd in commands:
            try:
                subprocess.run(
                    cmd,
                    check=True,
                    capture_output=True,
                    text=True,
                    shell=False,
                    timeout=60,
                )
                return True
            except FileNotFoundError as e:
                last_error = e
                continue
            except subprocess.TimeoutExpired as e:
                last_error = e
                print(f"JS压缩超时（60s）: {' '.join(cmd)}")
                continue
            except subprocess.CalledProcessError as e:
                last_error = e
                stderr_output = (
                    e.stderr
                    if isinstance(e.stderr, str)
                    else (
                        e.stderr.decode("utf-8", errors="ignore")
                        if e.stderr
                        else str(e)
                    )
                )
                stdout_output = (
                    e.stdout
                    if isinstance(e.stdout, str)
                    else (
                        e.stdout.decode("utf-8", errors="ignore")
                        if e.stdout
                        else ""
                    )
                )
                print(f"JS压缩失败: {stderr_output}")
                if stdout_output:
                    print(f"标准输出: {stdout_output}")
                continue

        print("提示: 请确保已安装Node.js；或预装 terser（npm i -g terser）")
        if last_error:
            print(f"最后错误: {last_error}")
        return False
    except Exception as e:
        print(f"JS压缩异常: {e}")
        return False


def minify_js_file(input_path):
    """返回 JS 压缩结果；失败时返回原始内容。"""
    with open(input_path, "r", encoding="utf-8") as f:
        original_content = f.read()

    temp_fd, temp_path = tempfile.mkstemp(suffix=".js")
    os.close(temp_fd)
    try:
        success = obfuscate_js(input_path, temp_path)
        if not success or not os.path.exists(temp_path):
            return False, original_content
        with open(temp_path, "r", encoding="utf-8") as f:
            return True, f.read()
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def compress_css(content):
    return rcssmin.cssmin(content)


def ensure_text(value: Any) -> str:
    """将压缩输出统一转换为 str，便于类型检查与文件写入。"""
    if isinstance(value, str):
        return value
    if isinstance(value, memoryview):
        return value.tobytes().decode("utf-8")
    if isinstance(value, (bytes, bytearray)):
        return bytes(value).decode("utf-8")
    return str(value)


def cleanup_old_files(file_dir, name, ext, current_hash):
    """清理旧的压缩文件"""
    for file in os.listdir(file_dir):
        # 检查是否是同一文件的旧哈希版本
        if file.startswith(f"{name}.") and file.endswith(ext):
            # 提取文件名中的哈希部分
            parts = file.split(".")
            if len(parts) >= 3:
                file_hash = parts[-2]
                # 如果哈希不是当前的，且是6位十六进制，则删除
                if (
                    file_hash != current_hash
                    and len(file_hash) == 6
                    and all(c in "0123456789abcdef" for c in file_hash.lower())
                ):
                    old_path = os.path.join(file_dir, file)
                    try:
                        os.remove(old_path)
                        print(f"删除旧文件: {old_path}")
                    except Exception as e:
                        print(f"删除旧文件失败 {old_path}: {e}")


def process_js_file(file_path, manifest, existing_manifest=None):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    file_dir = os.path.dirname(file_path)
    file_name = os.path.basename(file_path)
    name, ext = os.path.splitext(file_name)
    current_hash = get_file_hash(content)
    manifest_key = f"js/{file_name}"

    # 先检查 manifest — 源哈希一致且产物确实被压缩过（内容与源码不同）则跳过
    if existing_manifest and manifest_key in existing_manifest:
        existing_entry = existing_manifest[manifest_key]
        if isinstance(existing_entry, dict):
            existing_output_path = os.path.join(STATIC_DIR, existing_entry["path"])
            if (
                existing_entry.get("hash") == current_hash
                and os.path.exists(existing_output_path)
                and get_file_hash(open(existing_output_path, "r", encoding="utf-8").read()) != current_hash
            ):
                manifest[manifest_key] = existing_entry
                print(f"JS文件未修改，跳过: {file_path}")
                return True
        elif isinstance(existing_entry, str):
            existing_output_path = os.path.join(STATIC_DIR, existing_entry)
            if (
                os.path.exists(existing_output_path)
                and get_file_hash(open(existing_output_path, "r", encoding="utf-8").read()) != current_hash
            ):
                manifest[manifest_key] = {"hash": current_hash, "path": existing_entry}
                print(f"JS文件未修改，跳过: {file_path}")
                return True

    # 源文件已变更，执行压缩
    minify_success, output_content = minify_js_file(file_path)
    output_hash = get_file_hash(output_content)
    hashed_name = f"{name}.{output_hash}{ext}"
    output_path = os.path.join(file_dir, hashed_name)

    cleanup_old_files(file_dir, name, ext, output_hash)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(output_content)

    manifest[manifest_key] = {"hash": current_hash, "path": f"js/{hashed_name}"}
    if minify_success:
        print(f"JS压缩完成: {file_path} -> {output_path}")
    else:
        print(f"JS压缩失败，使用原内容: {file_path} -> {output_path}")
    return minify_success


def process_css_file(file_path, manifest, existing_manifest=None):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    file_dir = os.path.dirname(file_path)
    file_name = os.path.basename(file_path)
    name, ext = os.path.splitext(file_name)
    current_hash = get_file_hash(content)
    manifest_key = f"css/{file_name}"

    # 先检查 manifest — 源哈希一致且产物确实被压缩过（内容与源码不同）则跳过
    if existing_manifest and manifest_key in existing_manifest:
        existing_entry = existing_manifest[manifest_key]
        if isinstance(existing_entry, dict):
            existing_output_path = os.path.join(STATIC_DIR, existing_entry["path"])
            if (
                existing_entry.get("hash") == current_hash
                and os.path.exists(existing_output_path)
                and get_file_hash(open(existing_output_path, "r", encoding="utf-8").read()) != current_hash
            ):
                manifest[manifest_key] = existing_entry
                print(f"CSS文件未修改，跳过: {file_path}")
                return True
        elif isinstance(existing_entry, str):
            if os.path.exists(os.path.join(STATIC_DIR, existing_entry)):
                manifest[manifest_key] = {"hash": current_hash, "path": existing_entry}
                print(f"CSS文件未修改，跳过: {file_path}")
                return True

    # 源文件已变更，执行压缩
    minified_content = ensure_text(compress_css(content))
    file_hash = get_file_hash(minified_content)
    hashed_name = f"{name}.{file_hash}{ext}"
    output_path = os.path.join(file_dir, hashed_name)

    cleanup_old_files(file_dir, name, ext, file_hash)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(minified_content)

    manifest[manifest_key] = {"hash": current_hash, "path": f"css/{hashed_name}"}
    print(f"CSS压缩完成: {file_path} -> {output_path}")
    return True


def load_manifest():
    """加载manifest文件"""
    manifest_path = os.path.join(STATIC_DIR, "manifest.json")
    if os.path.exists(manifest_path):
        with open(manifest_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def get_static_url(filename):
    """根据原始文件名获取哈希化后的URL"""
    manifest = load_manifest()
    entry = manifest.get(filename)
    if isinstance(entry, dict):
        return entry["path"]
    return entry or filename


def main():
    # 加载现有的manifest文件
    existing_manifest = load_manifest()
    manifest = {}

    # 处理静态文件
    for root, _, files in os.walk(STATIC_DIR):
        for file in files:
            file_path = os.path.join(root, file)

            # 跳过已经压缩/混淆的文件
            if ".min." in file:
                continue

            # 跳过已经是哈希化命名的文件
            parts = file.split(".")
            if (
                len(parts) >= 3
                and len(parts[-2]) == 6
                and all(c in "0123456789abcdef" for c in parts[-2].lower())
            ):
                continue

            if file.endswith(".css"):
                process_css_file(file_path, manifest, existing_manifest)
            elif file.endswith(".js"):
                process_js_file(file_path, manifest, existing_manifest)

    # 生成manifest文件
    manifest_path = os.path.join(STATIC_DIR, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"Manifest文件已生成: {manifest_path}")


if __name__ == "__main__":
    main()
