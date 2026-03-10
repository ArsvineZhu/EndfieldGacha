import os
import json
import hashlib
import subprocess
import rcssmin

STATIC_DIR = "app/static"
MANIFEST_FILE = "app/static/manifest.json"


def get_file_hash(content):
    """使用 SHA256 生成哈希值"""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:6]


def obfuscate_js(input_path, output_path):
    try:
        # 确保输出目录存在
        output_dir = os.path.dirname(output_path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # 使用terser进行压缩和轻度混淆
        cmd = [
            "npx",
            "terser",
            input_path,
            "--output",
            output_path,
            "--compress",
            "--mangle",
            "--toplevel",
        ]

        result = subprocess.run(
            cmd, check=True, capture_output=True, text=True, shell=True
        )
        return True
    except subprocess.CalledProcessError as e:
        stderr_output = (
            e.stderr
            if isinstance(e.stderr, str)
            else (e.stderr.decode("utf-8", errors="ignore") if e.stderr else str(e))
        )
        stdout_output = (
            e.stdout
            if isinstance(e.stdout, str)
            else (e.stdout.decode("utf-8", errors="ignore") if e.stdout else "")
        )
        print(f"JS压缩失败: {stderr_output}")
        if stdout_output:
            print(f"标准输出: {stdout_output}")
        print("提示: 请确保已安装Node.js，然后运行: npm install -g terser")
        return False
    except FileNotFoundError:
        print("terser 未找到，请先安装Node.js，然后运行: npm install -g terser")
        return False


def compress_css(content):
    return rcssmin.cssmin(content)


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

    # 计算当前文件的哈希值
    current_hash = get_file_hash(content)
    hashed_name = f"{name}.{current_hash}{ext}"
    output_path = os.path.join(file_dir, hashed_name)
    manifest_key = f"js/{file_name}"

    # 检查是否已有相同哈希的文件
    if existing_manifest and manifest_key in existing_manifest:
        existing_entry = existing_manifest[manifest_key]
        # 如果是字典格式，检查哈希值
        if isinstance(existing_entry, dict):
            if existing_entry.get("hash") == current_hash and os.path.exists(
                os.path.join(STATIC_DIR, existing_entry["path"])
            ):
                manifest[manifest_key] = existing_entry
                print(f"JS文件未修改，跳过: {file_path}")
                return True
        # 如果是字符串格式（旧版本），检查路径中是否包含哈希
        elif isinstance(existing_entry, str):
            if current_hash in existing_entry and os.path.exists(
                os.path.join(STATIC_DIR, existing_entry)
            ):
                manifest[manifest_key] = {"hash": current_hash, "path": existing_entry}
                print(f"JS文件未修改，跳过: {file_path}")
                return True

    # 文件已修改，先清理旧文件
    cleanup_old_files(file_dir, name, ext, current_hash)

    # 文件不存在或已修改，进行处理
    if obfuscate_js(file_path, output_path):
        manifest[manifest_key] = {"hash": current_hash, "path": f"js/{hashed_name}"}
        print(f"JS压缩完成: {file_path} -> {output_path}")
        return True
    else:
        # 压缩失败则直接复制原内容到哈希文件名
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        manifest[manifest_key] = {"hash": current_hash, "path": f"js/{hashed_name}"}
        print(f"JS压缩失败，使用原内容: {file_path} -> {output_path}")
        return False


def process_css_file(file_path, manifest, existing_manifest=None):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    file_dir = os.path.dirname(file_path)
    file_name = os.path.basename(file_path)
    name, ext = os.path.splitext(file_name)

    # 计算原始内容的哈希值
    current_hash = get_file_hash(content)

    # 压缩CSS
    minified_content = compress_css(content)

    # 确保内容是字符串类型
    if isinstance(minified_content, (bytes, bytearray)):
        minified_content = minified_content.decode("utf-8")

    # 生成哈希文件名
    file_hash = get_file_hash(minified_content)
    hashed_name = f"{name}.{file_hash}{ext}"
    output_path = os.path.join(file_dir, hashed_name)
    manifest_key = f"css/{file_name}"

    # 检查是否已有相同哈希的文件
    if existing_manifest and manifest_key in existing_manifest:
        existing_entry = existing_manifest[manifest_key]
        # 如果是字典格式，检查哈希值
        if isinstance(existing_entry, dict):
            if existing_entry.get("hash") == current_hash and os.path.exists(
                os.path.join(STATIC_DIR, existing_entry["path"])
            ):
                manifest[manifest_key] = existing_entry
                print(f"CSS文件未修改，跳过: {file_path}")
                return True
        # 如果是字符串格式（旧版本），检查路径中是否包含哈希
        elif isinstance(existing_entry, str):
            if current_hash in existing_entry and os.path.exists(
                os.path.join(STATIC_DIR, existing_entry)
            ):
                manifest[manifest_key] = {"hash": current_hash, "path": existing_entry}
                print(f"CSS文件未修改，跳过: {file_path}")
                return True

    # 文件已修改，先清理旧文件
    cleanup_old_files(file_dir, name, ext, file_hash)

    # 文件已修改，写入压缩后的内容
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
