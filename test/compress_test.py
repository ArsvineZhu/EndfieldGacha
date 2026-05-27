import importlib.util
import json
from pathlib import Path

import pytest

COMPRESS_PATH = Path(__file__).resolve().parents[1] / "build" / "compress.py"
SPEC = importlib.util.spec_from_file_location("compress_module", COMPRESS_PATH)
compress = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(compress)


def test_minify_js_file_uses_safe_aggressive_terser_flags(tmp_path, monkeypatch):
    source = tmp_path / "sample.js"
    output = tmp_path / "sample.min.js"
    map_path = output.with_name(f"{output.name}.map")
    source.write_text("function demo () { return 1 + 2; }\n", encoding="utf-8")
    output.write_text("function demo(){return 3}\n//# sourceMappingURL=sample.min.js.map\n", encoding="utf-8")
    map_path.write_text('{"version":3,"file":"sample.min.js"}', encoding="utf-8")

    captured = {}

    def fake_require_local_bin(name):
        assert name == "terser"
        return "terser-bin"

    def fake_run_command(command):
        captured["command"] = command

    monkeypatch.setattr(compress, "_require_local_bin", fake_require_local_bin)
    monkeypatch.setattr(compress, "_run_command", fake_run_command)
    monkeypatch.setattr(compress, "ENABLE_ASSET_OBFUSCATION", False)

    result = compress.minify_js_file(source, output, "sample.map")

    command = captured["command"]
    command_text = " ".join(command)

    assert command[0] == "terser-bin"
    assert "--compress" in command
    assert "passes=3,toplevel=true,drop_console=true,drop_debugger=true" in command
    assert "--mangle" in command
    assert "toplevel=true" in command
    assert "--source-map" in command
    assert "url='sample.map'" in command
    assert "unsafe" not in command_text
    assert "--mangle-props" not in command_text
    assert "sourceMappingURL=sample.map" in result


def test_minify_css_file_enables_sourcemap(tmp_path, monkeypatch):
    source = tmp_path / "sample.css"
    output = tmp_path / "sample.min.css"
    map_path = output.with_name(f"{output.name}.map")
    source.write_text("body { color: red; }\n", encoding="utf-8")
    output.write_text(
        "body{color:red}\n/*# sourceMappingURL=C:\\temp\\sample.min.css.map */\n",
        encoding="utf-8",
    )
    map_path.write_text('{"version":3,"file":"sample.min.css"}', encoding="utf-8")

    captured = {}

    def fake_require_local_bin(name):
        assert name == "lightningcss"
        return "lightningcss-bin"

    def fake_run_command(command):
        captured["command"] = command

    monkeypatch.setattr(compress, "_require_local_bin", fake_require_local_bin)
    monkeypatch.setattr(compress, "_run_command", fake_run_command)
    monkeypatch.setattr(compress, "ENABLE_ASSET_OBFUSCATION", False)

    result = compress.minify_css_file(source, output, "sample.map")
    command = captured["command"]

    assert command[0] == "lightningcss-bin"
    assert "--minify" in command
    assert "--sourcemap" in command
    assert "sourceMappingURL=sample.map" in result


def test_normalize_source_mapping_url_handles_digit_prefixed_map_name():
    content = "body{color:red}\n/*# sourceMappingURL=old.map */\n"
    normalized = compress._normalize_source_mapping_url(content, "123abc.css.map")
    assert "sourceMappingURL=123abc.css.map" in normalized


def test_minify_js_file_runs_obfuscator_when_enabled(tmp_path, monkeypatch):
    source = tmp_path / "sample.js"
    output = tmp_path / "sample.min.js"
    source.write_text("function demo () { return 1 + 2; }\n", encoding="utf-8")

    commands = []

    def fake_require_local_bin(name):
        if name == "terser":
            return "terser-bin"
        if name == "javascript-obfuscator":
            return "obf-bin"
        raise AssertionError(f"unexpected binary: {name}")

    def fake_run_command(command):
        commands.append(command)
        if command[0] == "terser-bin":
            out_path = Path(command[command.index("--output") + 1])
            out_path.write_text("function demo(){return 3}\n//# sourceMappingURL=sample.map\n", encoding="utf-8")
            out_path.with_name(f"{out_path.name}.map").write_text(
                '{"version":3,"file":"sample.min.js","sourcesContent":["x"]}',
                encoding="utf-8",
            )
        elif command[0] == "obf-bin":
            out_path = Path(command[command.index("--output") + 1])
            out_path.write_text("var _0x1='x';console.log(_0x1);\n//# sourceMappingURL=sample.map\n", encoding="utf-8")
            out_path.with_name(f"{out_path.name}.map").write_text(
                '{"version":3,"file":"sample.min.js"}',
                encoding="utf-8",
            )

    monkeypatch.setattr(compress, "_require_local_bin", fake_require_local_bin)
    monkeypatch.setattr(compress, "_run_command", fake_run_command)
    monkeypatch.setattr(compress, "ENABLE_ASSET_OBFUSCATION", True)

    result = compress.minify_js_file(source, output, "sample.map")

    assert commands[0][0] == "terser-bin"
    assert commands[1][0] == "obf-bin"
    assert "sourceMappingURL=sample.map" in result
    assert output.exists()
    assert output.with_name(f"{output.name}.map").exists()


def test_rewrite_map_file_target_strips_sources_content_when_obfuscation_enabled(tmp_path, monkeypatch):
    map_path = tmp_path / "sample.js.map"
    map_path.write_text(
        '{"version":3,"file":"old.js","sources":["old.js"],"sourcesContent":["secret"]}',
        encoding="utf-8",
    )
    monkeypatch.setattr(compress, "ENABLE_ASSET_OBFUSCATION", True)

    compress._rewrite_map_file_target(map_path, "new.js")
    data = json.loads(map_path.read_text(encoding="utf-8"))

    assert data["file"] == "new.js"
    assert "sourcesContent" not in data


def test_process_js_file_rebuilds_stale_artifact_and_cleans_old_precompressed(tmp_path, monkeypatch):
    source_static = tmp_path / "source_static"
    output_static = tmp_path / "dist_static"
    source_js_dir = source_static / "js"
    output_js_dir = output_static / "js"
    source_js_dir.mkdir(parents=True)
    output_js_dir.mkdir(parents=True)

    source_path = source_js_dir / "sample.js"
    source_content = "function demo () { return 1 + 2; }\n"
    source_path.write_text(source_content, encoding="utf-8")

    stale_hash = compress.get_file_hash(source_content)
    stale_output = output_js_dir / f"{stale_hash}.js"
    stale_output.write_text(source_content, encoding="utf-8")
    stale_map = output_js_dir / f"{stale_hash}.js.map"
    stale_map.write_text('{"version":3,"file":"old.js"}', encoding="utf-8")
    stale_map.with_name(f"{stale_map.name}.gz").write_bytes(b"old-map-gz")
    stale_map.with_name(f"{stale_map.name}.br").write_bytes(b"old-map-br")
    stale_output.with_name(f"{stale_output.name}.gz").write_bytes(b"old-gz")
    stale_output.with_name(f"{stale_output.name}.br").write_bytes(b"old-br")

    existing_manifest = {
        "js/sample.js": {
            "hash": stale_hash,
            "path": f"js/{stale_output.name}",
        }
    }
    manifest = {}

    minified_content = "function demo(){return 3}\n"

    def fake_minify_js(input_path, output_path, source_map_filename):
        assert input_path == source_path
        assert source_map_filename == f"{stale_hash}.js.map"
        output_path.write_text(
            minified_content + f"//# sourceMappingURL={source_map_filename}\n",
            encoding="utf-8",
        )
        output_path.with_name(f"{output_path.name}.map").write_text(
            '{"version":3,"file":"sample.tmp.js"}',
            encoding="utf-8",
        )
        return minified_content

    def fake_write_precompressed(path):
        path.with_name(f"{path.name}.gz").write_bytes(b"new-gz")
        path.with_name(f"{path.name}.br").write_bytes(b"new-br")

    monkeypatch.setattr(compress, "SOURCE_STATIC_DIR", source_static)
    monkeypatch.setattr(compress, "OUTPUT_STATIC_DIR", output_static)
    monkeypatch.setattr(compress, "MANIFEST_FILE", output_static / "manifest.json")
    monkeypatch.setattr(compress, "minify_js_file", fake_minify_js)
    monkeypatch.setattr(compress, "write_precompressed_variants", fake_write_precompressed)

    compress.process_js_file(source_path, manifest, existing_manifest)

    expected_hash = compress.get_file_hash(minified_content)
    expected_name = f"{expected_hash}.js"
    expected_path = output_js_dir / expected_name
    expected_map_path = output_js_dir / f"{expected_hash}.js.map"

    assert manifest["js/sample.js"]["hash"] == stale_hash
    assert manifest["js/sample.js"]["path"] == f"js/{expected_name}"
    assert minified_content in expected_path.read_text(encoding="utf-8")
    assert expected_map_path.exists()
    assert not stale_output.exists()
    assert not stale_map.exists()
    assert not stale_output.with_name(f"{stale_output.name}.gz").exists()
    assert not stale_output.with_name(f"{stale_output.name}.br").exists()
    assert not stale_map.with_name(f"{stale_map.name}.gz").exists()
    assert not stale_map.with_name(f"{stale_map.name}.br").exists()
    assert expected_path.with_name(f"{expected_path.name}.gz").exists()
    assert expected_path.with_name(f"{expected_path.name}.br").exists()
    assert expected_map_path.with_name(f"{expected_map_path.name}.gz").exists()
    assert expected_map_path.with_name(f"{expected_map_path.name}.br").exists()


def test_process_css_file_reuses_manifest_when_source_unchanged(tmp_path, monkeypatch):
    source_static = tmp_path / "source_static"
    output_static = tmp_path / "dist_static"
    source_css_dir = source_static / "css"
    output_css_dir = output_static / "css"
    source_css_dir.mkdir(parents=True)
    output_css_dir.mkdir(parents=True)

    source_path = source_css_dir / "sample.css"
    source_content = "body { color: red; }\n"
    source_path.write_text(source_content, encoding="utf-8")

    source_hash = compress.get_file_hash(source_content)
    minified_output = "body{color:red}"
    output_hash = compress.get_file_hash(minified_output)
    hashed_output = output_css_dir / f"{output_hash}.css"
    hashed_output.write_text(minified_output, encoding="utf-8")
    (output_css_dir / f"{output_hash}.css.map").write_text(
        '{"version":3,"file":"sample.css"}',
        encoding="utf-8",
    )

    existing_manifest = {
        "css/sample.css": {
            "hash": source_hash,
            "path": f"css/{hashed_output.name}",
        }
    }
    manifest = {}

    called = {"precompressed": 0, "minify": 0}

    def fake_write_precompressed(path):
        called["precompressed"] += 1

    def fake_minify_css(input_path, output_path, source_map_filename):
        called["minify"] += 1
        raise AssertionError("minify_css_file should not be called when cache is reusable")

    monkeypatch.setattr(compress, "SOURCE_STATIC_DIR", source_static)
    monkeypatch.setattr(compress, "OUTPUT_STATIC_DIR", output_static)
    monkeypatch.setattr(compress, "MANIFEST_FILE", output_static / "manifest.json")
    monkeypatch.setattr(compress, "write_precompressed_variants", fake_write_precompressed)
    monkeypatch.setattr(compress, "minify_css_file", fake_minify_css)

    compress.process_css_file(source_path, manifest, existing_manifest)

    assert manifest["css/sample.css"] == existing_manifest["css/sample.css"]
    assert called["precompressed"] == 2
    assert called["minify"] == 0


def test_process_css_file_hard_fails_when_lightningcss_errors(tmp_path, monkeypatch):
    source_static = tmp_path / "source_static"
    output_static = tmp_path / "dist_static"
    source_css_dir = source_static / "css"
    source_css_dir.mkdir(parents=True)

    source_path = source_css_dir / "broken.css"
    source_path.write_text("body { color: red; }\n", encoding="utf-8")

    monkeypatch.setattr(compress, "SOURCE_STATIC_DIR", source_static)
    monkeypatch.setattr(compress, "OUTPUT_STATIC_DIR", output_static)
    monkeypatch.setattr(compress, "MANIFEST_FILE", output_static / "manifest.json")

    def fake_minify_css(input_path, output_path, source_map_filename):
        raise RuntimeError("lightningcss failed")

    monkeypatch.setattr(compress, "minify_css_file", fake_minify_css)

    with pytest.raises(RuntimeError, match="lightningcss failed"):
        compress.process_css_file(source_path, {}, {})


def test_prepare_output_tree_excludes_source_css_js_but_keeps_other_assets(tmp_path, monkeypatch):
    source_static = tmp_path / "source_static"
    output_static = tmp_path / "dist_static"
    (source_static / "css").mkdir(parents=True)
    (source_static / "js").mkdir(parents=True)
    (source_static / "img").mkdir(parents=True)

    (source_static / "css" / "layout.css").write_text("body { color: red; }", encoding="utf-8")
    (source_static / "js" / "main.js").write_text("console.log('x')", encoding="utf-8")
    (source_static / "img" / "icon.png").write_bytes(b"png")

    # 模拟历史遗留文件，确保会被清理掉
    (output_static / "css").mkdir(parents=True, exist_ok=True)
    (output_static / "js").mkdir(parents=True, exist_ok=True)
    (output_static / "css" / "layout.css").write_text("old", encoding="utf-8")
    (output_static / "js" / "main.js").write_text("old", encoding="utf-8")

    monkeypatch.setattr(compress, "SOURCE_STATIC_DIR", source_static)
    monkeypatch.setattr(compress, "OUTPUT_STATIC_DIR", output_static)

    compress._prepare_output_tree()

    assert not (output_static / "css" / "layout.css").exists()
    assert not (output_static / "js" / "main.js").exists()
    assert (output_static / "img" / "icon.png").exists()


def test_cleanup_source_legacy_build_artifacts_removes_hashed_and_map_variants(tmp_path, monkeypatch):
    source_static = tmp_path / "source_static"
    css_dir = source_static / "css"
    js_dir = source_static / "js"
    css_dir.mkdir(parents=True)
    js_dir.mkdir(parents=True)

    keep_css = css_dir / "layout.css"
    keep_js = js_dir / "main.js"
    drop_css = css_dir / "layout.14d598.css"
    drop_css_map = css_dir / "layout.map"
    drop_css_gz = css_dir / "layout.css.gz"
    drop_js = js_dir / "main.a7d52a.js"
    drop_js_map = js_dir / "main.map"
    drop_js_br = js_dir / "main.js.br"

    keep_css.write_text("body{}", encoding="utf-8")
    keep_js.write_text("console.log(1)", encoding="utf-8")
    drop_css.write_text("old", encoding="utf-8")
    drop_css_map.write_text("{}", encoding="utf-8")
    drop_css_gz.write_bytes(b"x")
    drop_js.write_text("old", encoding="utf-8")
    drop_js_map.write_text("{}", encoding="utf-8")
    drop_js_br.write_bytes(b"x")

    monkeypatch.setattr(compress, "SOURCE_STATIC_DIR", source_static)

    compress._cleanup_source_legacy_build_artifacts()

    assert keep_css.exists()
    assert keep_js.exists()
    assert not drop_css.exists()
    assert not drop_css_map.exists()
    assert not drop_css_gz.exists()
    assert not drop_js.exists()
    assert not drop_js_map.exists()
    assert not drop_js_br.exists()
