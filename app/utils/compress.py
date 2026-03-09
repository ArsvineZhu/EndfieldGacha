import os
import json
import hashlib
import subprocess
import rcssmin

STATIC_DIR = "app/static"
MANIFEST_FILE = "app/static/manifest.json"


def get_file_hash(content):
    # 使用 SHA256 生成更安全的哈希值
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
            "--toplevel"
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
        print(
            "terser 未找到，请先安装Node.js，然后运行: npm install -g terser"
        )
        return False


def compress_css(content):
    return rcssmin.cssmin(content)


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

    # 检查是否已有相同哈希的文件存在
    file_exists = os.path.exists(output_path)
    
    # 检查是否已有相同哈希的文件
    if existing_manifest and manifest_key in existing_manifest and file_exists:
        existing_path = existing_manifest[manifest_key]
        if current_hash in existing_path:
            # 文件未修改且存在，直接复用
            manifest[manifest_key] = existing_path
            print(f"JS文件未修改，跳过: {file_path}")
            return True

    # 文件不存在或已修改，进行处理
    if obfuscate_js(file_path, output_path):
        manifest[manifest_key] = f"js/{hashed_name}"
        print(f"JS压缩完成: {file_path} -> {output_path}")
        return True
    else:
        # 压缩失败则直接复制原内容到哈希文件名
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        manifest[manifest_key] = f"js/{hashed_name}"
        print(f"JS压缩失败，使用原内容: {file_path} -> {output_path}")
        return False


def process_css_file(file_path, manifest, existing_manifest=None):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    file_dir = os.path.dirname(file_path)
    file_name = os.path.basename(file_path)
    name, ext = os.path.splitext(file_name)

    # 计算原始内容的哈希值（用来判断是否修改）
    original_hash = get_file_hash(content)
    
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
        existing_path = existing_manifest[manifest_key]
        # 检查原始文件是否修改
        # 这里我们保存原始文件的哈希到manifest的注释中？或者直接检查输出文件是否存在
        if os.path.exists(output_path):
            manifest[manifest_key] = existing_path
            print(f"CSS文件未修改，跳过: {file_path}")
            return True

    # 文件已修改，写入压缩后的内容
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(minified_content)

    manifest[manifest_key] = f"css/{hashed_name}"
    print(f"CSS压缩完成: {file_path} -> {output_path}")
    return True


def clean_old_files():
    for root, _, files in os.walk(STATIC_DIR):
        for file in files:
            file_path = os.path.join(root, file)
            # 清理旧的.min.js和.min.css文件
            if file.endswith((".min.js", ".min.css")):
                try:
                    os.remove(file_path)
                    print(f"清理旧的min文件: {file_path}")
                except OSError:
                    pass
            # 清理旧的哈希化文件（文件名中包含哈希值）
            elif file.endswith((".js", ".css")):
                if "." in file and file.count(".") >= 2:
                    parts = file.split(".")
                    # 哈希值通常在倒数第二个部分，长度为6
                    potential_hash = parts[-2]
                    if len(potential_hash) == 6 and all(
                        c in "0123456789abcdef" for c in potential_hash.lower()
                    ):
                        try:
                            os.remove(file_path)
                            print(f"清理旧哈希文件: {file_path}")
                        except OSError:
                            pass


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
    return manifest.get(filename, filename)


def main():
    # 加载现有的manifest文件
    existing_manifest = load_manifest()
    manifest = {}

    # 清理旧的哈希化文件
    clean_old_files()

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
