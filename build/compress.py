import gzip
import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import brotli

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_STATIC_DIR = PROJECT_ROOT / "web" / "static"
OUTPUT_STATIC_DIR = PROJECT_ROOT / "dist" / "static"
MANIFEST_FILE = OUTPUT_STATIC_DIR / "manifest.json"
BUILD_DIR_NAME = "_build"

TEXT_PRECOMPRESS_EXTENSIONS = {".js", ".css", ".json", ".svg", ".txt", ".map"}


def get_asset_output_dir(asset_type: str) -> Path:
    output_dir = OUTPUT_STATIC_DIR / BUILD_DIR_NAME / asset_type
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def get_file_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:6]


def _run_command(command: list[str]) -> None:
    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        shell=False,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"命令执行失败: {' '.join(command)}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )


def _require_local_bin(bin_name: str) -> str:
    candidates = [
        PROJECT_ROOT / "node_modules" / ".bin" / f"{bin_name}.cmd",
        PROJECT_ROOT / "node_modules" / ".bin" / bin_name,
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    raise RuntimeError(f"未找到本地依赖 {bin_name}。请先执行 `npm install`。")


def _source_map_path(asset_path: Path) -> Path:
    return asset_path.with_name(f"{asset_path.name}.map")


def _normalize_source_mapping_url(content: str, source_map_filename: str) -> str:
    return re.sub(r"(sourceMappingURL=)[^*\r\n]+", rf"\1{source_map_filename}", content)


def _rewrite_map_file_target(map_path: Path, output_filename: str) -> None:
    data = json.loads(map_path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data["file"] = output_filename
        map_path.write_text(
            json.dumps(data, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )


def minify_js_file(input_path: Path, output_path: Path, source_map_filename: str) -> str:
    terser_bin = _require_local_bin("terser")
    command = [
        terser_bin,
        str(input_path),
        "--output",
        str(output_path),
        "--compress",
        "passes=3,toplevel=true,drop_console=true,drop_debugger=true",
        "--mangle",
        "toplevel=true",
        "--ecma",
        "2020",
        "--source-map",
        f"url='{source_map_filename}'",
    ]
    _run_command(command)

    map_path = _source_map_path(output_path)
    if not map_path.exists():
        raise RuntimeError(f"terser 未生成 source map: {map_path}")

    content = output_path.read_text(encoding="utf-8")
    normalized = _normalize_source_mapping_url(content, source_map_filename)
    if normalized != content:
        output_path.write_text(normalized, encoding="utf-8")
    return normalized


def minify_css_file(input_path: Path, output_path: Path, source_map_filename: str) -> str:
    lightningcss_bin = _require_local_bin("lightningcss")
    command = [
        lightningcss_bin,
        str(input_path),
        "--minify",
        "--sourcemap",
        "-o",
        str(output_path),
    ]
    _run_command(command)

    map_path = _source_map_path(output_path)
    if not map_path.exists():
        raise RuntimeError(f"lightningcss 未生成 source map: {map_path}")

    content = output_path.read_text(encoding="utf-8")
    normalized = _normalize_source_mapping_url(content, source_map_filename)
    if normalized != content:
        output_path.write_text(normalized, encoding="utf-8")
    return normalized


def cleanup_old_files(output_dir: Path, name: str, ext: str, current_hash: str) -> None:
    for file in output_dir.iterdir():
        if not file.is_file():
            continue
        if not file.name.startswith(f"{name}.") or file.suffix != ext:
            continue

        parts = file.name.split(".")
        if len(parts) < 3:
            continue

        file_hash = parts[-2]
        if (
            file_hash != current_hash
            and len(file_hash) == 6
            and all(c in "0123456789abcdef" for c in file_hash.lower())
        ):
            file.unlink(missing_ok=True)
            file.with_name(f"{file.name}.gz").unlink(missing_ok=True)
            file.with_name(f"{file.name}.br").unlink(missing_ok=True)
            print(f"删除旧文件: {file}")


def _is_text_precompress_target(path: Path) -> bool:
    return path.suffix in TEXT_PRECOMPRESS_EXTENSIONS


def write_precompressed_variants(path: Path) -> None:
    if not _is_text_precompress_target(path):
        return
    data = path.read_bytes()
    path.with_name(f"{path.name}.gz").write_bytes(gzip.compress(data, compresslevel=9, mtime=0))
    path.with_name(f"{path.name}.br").write_bytes(brotli.compress(data, quality=11))


def _prepare_output_tree() -> None:
    OUTPUT_STATIC_DIR.mkdir(parents=True, exist_ok=True)

    for root, _, files in os.walk(SOURCE_STATIC_DIR):
        src_root = Path(root)
        rel_root = src_root.relative_to(SOURCE_STATIC_DIR)
        dst_root = OUTPUT_STATIC_DIR / rel_root
        dst_root.mkdir(parents=True, exist_ok=True)

        for file in files:
            src_file = src_root / file
            rel_file = src_file.relative_to(SOURCE_STATIC_DIR).as_posix()

            if rel_file == "manifest.json":
                continue
            if re.match(r"css/.+\.[0-9a-f]{6}\.css$", rel_file):
                continue
            if re.match(r"js/.+\.[0-9a-f]{6}\.js$", rel_file):
                continue
            if re.match(r"(css|js)/.+\.map$", rel_file):
                continue
            if src_file.suffix in {".gz", ".br"}:
                continue

            shutil.copy2(src_file, dst_root / file)


def process_js_file(
    file_path: Path,
    manifest: dict[str, Any],
    existing_manifest: dict[str, Any] | None = None,
) -> None:
    content = file_path.read_text(encoding="utf-8")

    name = file_path.stem
    ext = file_path.suffix
    source_map_name = f"{name}.map"
    current_hash = get_file_hash(content)
    manifest_key = f"js/{file_path.name}"
    output_dir = get_asset_output_dir("js")

    if existing_manifest and manifest_key in existing_manifest:
        existing_entry = existing_manifest[manifest_key]
        existing_rel_path = existing_entry.get("path") if isinstance(existing_entry, dict) else existing_entry
        existing_output_path = OUTPUT_STATIC_DIR / str(existing_rel_path)

        if (
            isinstance(existing_entry, dict)
            and existing_entry.get("hash") == current_hash
            and existing_output_path.exists()
            and (output_dir / source_map_name).exists()
        ):
            existing_output = existing_output_path.read_text(encoding="utf-8")
            if get_file_hash(existing_output) != current_hash:
                manifest[manifest_key] = existing_entry
                write_precompressed_variants(existing_output_path)
                write_precompressed_variants(output_dir / source_map_name)
                print(f"JS文件未修改，跳过: {file_path}")
                return

    temp_output_path = output_dir / f".{name}.tmp.min.js"
    minified_content = minify_js_file(file_path, temp_output_path, source_map_name)

    output_hash = get_file_hash(minified_content)
    hashed_name = f"{name}.{output_hash}{ext}"
    output_path = output_dir / hashed_name
    output_map_path = output_dir / source_map_name

    cleanup_old_files(output_dir, name, ext, output_hash)
    output_path.write_text(minified_content, encoding="utf-8")

    temp_map_path = _source_map_path(temp_output_path)
    temp_map_path.replace(output_map_path)
    _rewrite_map_file_target(output_map_path, output_path.name)
    temp_output_path.unlink(missing_ok=True)

    write_precompressed_variants(output_path)
    write_precompressed_variants(output_map_path)

    manifest[manifest_key] = {"hash": current_hash, "path": f"{BUILD_DIR_NAME}/js/{hashed_name}"}
    print(f"JS压缩完成: {file_path} -> {output_path}")


def process_css_file(
    file_path: Path,
    manifest: dict[str, Any],
    existing_manifest: dict[str, Any] | None = None,
) -> None:
    content = file_path.read_text(encoding="utf-8")

    name = file_path.stem
    ext = file_path.suffix
    source_map_name = f"{name}.map"
    current_hash = get_file_hash(content)
    manifest_key = f"css/{file_path.name}"
    output_dir = get_asset_output_dir("css")

    if existing_manifest and manifest_key in existing_manifest:
        existing_entry = existing_manifest[manifest_key]
        existing_rel_path = existing_entry.get("path") if isinstance(existing_entry, dict) else existing_entry
        existing_output_path = OUTPUT_STATIC_DIR / str(existing_rel_path)

        if (
            isinstance(existing_entry, dict)
            and existing_entry.get("hash") == current_hash
            and existing_output_path.exists()
            and (output_dir / source_map_name).exists()
        ):
            existing_output = existing_output_path.read_text(encoding="utf-8")
            if get_file_hash(existing_output) != current_hash:
                manifest[manifest_key] = existing_entry
                write_precompressed_variants(existing_output_path)
                write_precompressed_variants(output_dir / source_map_name)
                print(f"CSS文件未修改，跳过: {file_path}")
                return

    temp_output_path = output_dir / f".{name}.tmp.min.css"
    minified_content = minify_css_file(file_path, temp_output_path, source_map_name)

    output_hash = get_file_hash(minified_content)
    hashed_name = f"{name}.{output_hash}{ext}"
    output_path = output_dir / hashed_name
    output_map_path = output_dir / source_map_name

    cleanup_old_files(output_dir, name, ext, output_hash)
    output_path.write_text(minified_content, encoding="utf-8")

    temp_map_path = _source_map_path(temp_output_path)
    temp_map_path.replace(output_map_path)
    _rewrite_map_file_target(output_map_path, output_path.name)
    temp_output_path.unlink(missing_ok=True)

    write_precompressed_variants(output_path)
    write_precompressed_variants(output_map_path)

    manifest[manifest_key] = {"hash": current_hash, "path": f"{BUILD_DIR_NAME}/css/{hashed_name}"}
    print(f"CSS压缩完成: {file_path} -> {output_path}")


def load_manifest() -> dict[str, Any]:
    if MANIFEST_FILE.exists():
        return json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    return {}


def get_static_url(filename: str) -> str:
    manifest = load_manifest()
    entry = manifest.get(filename)
    if isinstance(entry, dict):
        return entry["path"]
    return entry or filename


def precompress_additional_text_assets() -> None:
    for file_path in OUTPUT_STATIC_DIR.rglob("*"):
        if not file_path.is_file():
            continue
        if file_path.suffix in {".gz", ".br"}:
            continue
        if file_path.suffix not in TEXT_PRECOMPRESS_EXTENSIONS:
            continue
        if file_path.suffix in {".js", ".css", ".map"}:
            continue
        write_precompressed_variants(file_path)


def main() -> None:
    _prepare_output_tree()

    existing_manifest = load_manifest()
    manifest: dict[str, Any] = {}

    for root, _, files in os.walk(SOURCE_STATIC_DIR):
        for file in files:
            file_path = Path(root) / file

            if file.endswith((".gz", ".br", ".map")):
                continue
            if ".min." in file:
                continue

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

    precompress_additional_text_assets()

    MANIFEST_FILE.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_FILE.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    write_precompressed_variants(MANIFEST_FILE)

    print(f"Manifest文件已生成: {MANIFEST_FILE}")


if __name__ == "__main__":
    main()
