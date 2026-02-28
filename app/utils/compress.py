import os
import rcssmin
import rjsmin

# 静态文件目录（Flask 默认）
STATIC_DIR = "static"
# 压缩后的文件后缀（如 style.css → style.min.css）
MIN_SUFFIX = ".min"

def compress_file(file_path, minify_func):
    """压缩单个文件"""
    # 读取原文件
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 压缩内容
    minified_content = minify_func(content)
    
    # 生成压缩后的文件路径（替换 .css/.js 为 .min.css/.min.js）
    file_dir, file_name = os.path.split(file_path)
    name, ext = os.path.splitext(file_name)
    min_file_name = f"{name}{MIN_SUFFIX}{ext}"
    min_file_path = os.path.join(file_dir, min_file_name)
    
    # 写入压缩文件
    with open(min_file_path, "w", encoding="utf-8") as f:
        f.write(minified_content)
    
    print(f"已压缩：{file_path} → {min_file_path}")

def main():
    # 遍历所有 CSS/JS 文件
    for root, _, files in os.walk(STATIC_DIR):
        for file in files:
            file_path = os.path.join(root, file)
            # 跳过已压缩的 .min 文件
            if MIN_SUFFIX in file:
                continue
            # 压缩 CSS
            if file.endswith(".css"):
                compress_file(file_path, rcssmin.cssmin)
            # 压缩 JS
            elif file.endswith(".js"):
                compress_file(file_path, rjsmin.jsmin)

if __name__ == "__main__":
    main()