import gzip
import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable

import brotli

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_STATIC_DIR = PROJECT_ROOT / "web" / "static"
OUTPUT_STATIC_DIR = PROJECT_ROOT / "dist" / "static"
MANIFEST_FILE = OUTPUT_STATIC_DIR / "manifest.json"

TEXT_PRECOMPRESS_EXTENSIONS = {".js", ".css", ".json", ".svg", ".txt", ".map"}
HASHED_ASSET_PATTERN = re.compile(r"^[0-9a-f]{6}\.(css|js)$")
LEGACY_HASHED_SOURCE_PATTERN = re.compile(r"^.+\.[0-9a-f]{6}\.(css|js)$")
ENABLE_ASSET_OBFUSCATION = os.environ.get("ENABLE_ASSET_OBFUSCATION", "1") == "1"

AssetMinifier = Callable[[Path, Path, str], str]


def get_asset_output_dir(asset_type: str) -> Path:
    output_dir = OUTPUT_STATIC_DIR / asset_type
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def get_asset_manifest_key(file_path: Path) -> str:
    return file_path.relative_to(SOURCE_STATIC_DIR).as_posix()


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
    return re.sub(
        r"(sourceMappingURL=)[^*\r\n]+",
        lambda match: f"{match.group(1)}{source_map_filename}",
        content,
    )


def _rewrite_map_file_target(map_path: Path, output_filename: str) -> None:
    data = json.loads(map_path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data["file"] = output_filename
        if ENABLE_ASSET_OBFUSCATION:
            data.pop("sourcesContent", None)
        map_path.write_text(
            json.dumps(data, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )


def _obfuscate_js_file(input_path: Path, output_path: Path) -> None:
    obfuscator_bin = _require_local_bin("javascript-obfuscator")
    output_map_name = f"{output_path.name}.map"
    command = [
        obfuscator_bin,
        str(input_path),
        "--output",
        str(output_path),
        "--options-preset",
        "medium-obfuscation",
        "--target",
        "browser-no-eval",
        "--rename-globals",
        "false",
        "--self-defending",
        "false",
        "--debug-protection",
        "false",
        "--source-map",
        "true",
        "--source-map-mode",
        "separate",
        "--source-map-file-name",
        output_map_name,
    ]
    _run_command(command)


def minify_js_file(input_path: Path, output_path: Path, source_map_filename: str) -> str:
    terser_bin = _require_local_bin("terser")
    terser_output_path = output_path
    if ENABLE_ASSET_OBFUSCATION:
        terser_output_path = output_path.with_name(f".{output_path.name}.terser.js")
    command = [
        terser_bin,
        str(input_path),
        "--output",
        str(terser_output_path),
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

    if ENABLE_ASSET_OBFUSCATION:
        _obfuscate_js_file(terser_output_path, output_path)
        terser_output_path.unlink(missing_ok=True)
        _source_map_path(terser_output_path).unlink(missing_ok=True)

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

    if ENABLE_ASSET_OBFUSCATION:
        _rewrite_map_file_target(map_path, output_path.name)

    content = output_path.read_text(encoding="utf-8")
    normalized = _normalize_source_mapping_url(content, source_map_filename)
    if normalized != content:
        output_path.write_text(normalized, encoding="utf-8")
    return normalized


def _remove_variant_files(path: Path) -> None:
    path.unlink(missing_ok=True)
    path.with_name(f"{path.name}.gz").unlink(missing_ok=True)
    path.with_name(f"{path.name}.br").unlink(missing_ok=True)


def _remove_manifest_output_bundle(existing_entry: Any) -> None:
    if not isinstance(existing_entry, dict):
        return

    rel_path = existing_entry.get("path")
    if not isinstance(rel_path, str):
        return

    output_path = OUTPUT_STATIC_DIR / rel_path
    _remove_variant_files(output_path)

    if output_path.suffix in {".css", ".js"}:
        map_path = output_path.with_name(f"{output_path.name}.map")
        _remove_variant_files(map_path)


def _is_legacy_hashed_source_name(filename: str) -> bool:
    parts = filename.split(".")
    return (
        bool(HASHED_ASSET_PATTERN.match(filename))
        or bool(LEGACY_HASHED_SOURCE_PATTERN.match(filename))
        or (
            len(parts) >= 3
            and len(parts[-2]) == 6
            and all(c in "0123456789abcdef" for c in parts[-2].lower())
        )
    )


def _resolve_manifest_output_paths(entry: Any) -> tuple[Path, Path] | None:
    if not isinstance(entry, dict):
        return None

    rel_path = entry.get("path")
    if not isinstance(rel_path, str) or not rel_path:
        return None

    output_path = OUTPUT_STATIC_DIR / rel_path
    map_path = output_path.with_name(f"{output_path.name}.map")
    return output_path, map_path


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

    # 生产目录不暴露源码 CSS/JS；清理历史遗留目录避免旧文件继续可访问
    shutil.rmtree(OUTPUT_STATIC_DIR / "css", ignore_errors=True)
    shutil.rmtree(OUTPUT_STATIC_DIR / "js", ignore_errors=True)

    for root, _, files in os.walk(SOURCE_STATIC_DIR):
        src_root = Path(root)
        rel_root = src_root.relative_to(SOURCE_STATIC_DIR)
        if rel_root.parts and rel_root.parts[0] in {"css", "js", "pages"}:
            continue
        dst_root = OUTPUT_STATIC_DIR / rel_root
        dst_root.mkdir(parents=True, exist_ok=True)

        for file in files:
            src_file = src_root / file
            rel_file = src_file.relative_to(SOURCE_STATIC_DIR).as_posix()

            if rel_file == "manifest.json":
                continue
            if src_file.suffix in {".gz", ".br"}:
                continue
            shutil.copy2(src_file, dst_root / file)


def _cleanup_source_legacy_build_artifacts() -> None:
    for asset_type in ("css", "js"):
        asset_dir = SOURCE_STATIC_DIR / asset_type
        if not asset_dir.exists():
            continue

        for file_path in asset_dir.iterdir():
            if not file_path.is_file():
                continue

            name = file_path.name
            should_remove = name.endswith((".gz", ".br", ".map")) or _is_legacy_hashed_source_name(name)
            if should_remove:
                file_path.unlink(missing_ok=True)


def _try_reuse_manifest_entry(
    *,
    manifest_key: str,
    current_hash: str,
    manifest: dict[str, Any],
    existing_manifest: dict[str, Any] | None,
    file_path: Path,
    asset_label: str,
) -> bool:
    if not existing_manifest or manifest_key not in existing_manifest:
        return False

    existing_entry = existing_manifest[manifest_key]
    if not isinstance(existing_entry, dict) or existing_entry.get("hash") != current_hash:
        return False

    resolved_paths = _resolve_manifest_output_paths(existing_entry)
    if resolved_paths is None:
        return False

    existing_output_path, existing_map_path = resolved_paths
    if not existing_output_path.exists() or not existing_map_path.exists():
        return False

    existing_output = existing_output_path.read_text(encoding="utf-8")
    if get_file_hash(existing_output) == current_hash:
        return False

    manifest[manifest_key] = existing_entry
    write_precompressed_variants(existing_output_path)
    write_precompressed_variants(existing_map_path)
    print(f"{asset_label}文件未修改，跳过: {file_path}")
    return True


def _process_asset_file(
    *,
    file_path: Path,
    asset_type: str,
    asset_label: str,
    minify_fn: AssetMinifier,
    manifest: dict[str, Any],
    existing_manifest: dict[str, Any] | None,
) -> None:
    content = file_path.read_text(encoding="utf-8")
    ext = file_path.suffix
    current_hash = get_file_hash(content)
    source_map_name = f"{current_hash}{ext}.map"
    manifest_key = get_asset_manifest_key(file_path)
    output_dir = get_asset_output_dir(asset_type)

    if _try_reuse_manifest_entry(
        manifest_key=manifest_key,
        current_hash=current_hash,
        manifest=manifest,
        existing_manifest=existing_manifest,
        file_path=file_path,
        asset_label=asset_label,
    ):
        return

    temp_output_path = output_dir / f".{file_path.stem}.tmp.min{ext}"
    minified_content = minify_fn(file_path, temp_output_path, source_map_name)

    output_hash = get_file_hash(minified_content)
    hashed_name = f"{output_hash}{ext}"
    output_path = output_dir / hashed_name
    output_map_path = output_dir / f"{output_hash}{ext}.map"

    _remove_manifest_output_bundle(existing_manifest.get(manifest_key) if existing_manifest else None)
    output_path.write_text(minified_content, encoding="utf-8")

    temp_map_path = _source_map_path(temp_output_path)
    temp_map_path.replace(output_map_path)
    _rewrite_map_file_target(output_map_path, output_path.name)
    temp_output_path.unlink(missing_ok=True)

    write_precompressed_variants(output_path)
    write_precompressed_variants(output_map_path)

    manifest[manifest_key] = {"hash": current_hash, "path": f"{asset_type}/{hashed_name}"}
    print(f"{asset_label}压缩完成: {file_path} -> {output_path}")


def process_js_file(
    file_path: Path,
    manifest: dict[str, Any],
    existing_manifest: dict[str, Any] | None = None,
) -> None:
    _process_asset_file(
        file_path=file_path,
        asset_type="js",
        asset_label="JS",
        minify_fn=minify_js_file,
        manifest=manifest,
        existing_manifest=existing_manifest,
    )


def process_css_file(
    file_path: Path,
    manifest: dict[str, Any],
    existing_manifest: dict[str, Any] | None = None,
) -> None:
    _process_asset_file(
        file_path=file_path,
        asset_type="css",
        asset_label="CSS",
        minify_fn=minify_css_file,
        manifest=manifest,
        existing_manifest=existing_manifest,
    )


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
    _cleanup_source_legacy_build_artifacts()
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

            if _is_legacy_hashed_source_name(file):
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
