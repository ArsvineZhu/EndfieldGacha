import importlib.util
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

    result = compress.minify_css_file(source, output, "sample.map")
    command = captured["command"]

    assert command[0] == "lightningcss-bin"
    assert "--minify" in command
    assert "--sourcemap" in command
    assert "sourceMappingURL=sample.map" in result


def test_process_js_file_rebuilds_stale_artifact_and_cleans_old_precompressed(tmp_path, monkeypatch):
    source_static = tmp_path / "source_static"
    output_static = tmp_path / "dist_static"
    source_js_dir = source_static / "js"
    output_js_dir = output_static / "_build" / "js"
    source_js_dir.mkdir(parents=True)
    output_js_dir.mkdir(parents=True)

    source_path = source_js_dir / "sample.js"
    source_content = "function demo () { return 1 + 2; }\n"
    source_path.write_text(source_content, encoding="utf-8")

    stale_hash = compress.get_file_hash(source_content)
    stale_output = output_js_dir / f"sample.{stale_hash}.js"
    stale_output.write_text(source_content, encoding="utf-8")
    stale_output.with_name(f"{stale_output.name}.gz").write_bytes(b"old-gz")
    stale_output.with_name(f"{stale_output.name}.br").write_bytes(b"old-br")

    existing_manifest = {
        "js/sample.js": {
            "hash": stale_hash,
            "path": f"_build/js/{stale_output.name}",
        }
    }
    manifest = {}

    minified_content = "function demo(){return 3}\n"

    def fake_minify_js(input_path, output_path, source_map_filename):
        assert input_path == source_path
        assert source_map_filename == "sample.map"
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
    expected_name = f"sample.{expected_hash}.js"
    expected_path = output_js_dir / expected_name
    expected_map_path = output_js_dir / "sample.map"

    assert manifest["js/sample.js"]["hash"] == stale_hash
    assert manifest["js/sample.js"]["path"] == f"_build/js/{expected_name}"
    assert minified_content in expected_path.read_text(encoding="utf-8")
    assert expected_map_path.exists()
    assert not stale_output.exists()
    assert not stale_output.with_name(f"{stale_output.name}.gz").exists()
    assert not stale_output.with_name(f"{stale_output.name}.br").exists()
    assert expected_path.with_name(f"{expected_path.name}.gz").exists()
    assert expected_path.with_name(f"{expected_path.name}.br").exists()
    assert expected_map_path.with_name(f"{expected_map_path.name}.gz").exists()
    assert expected_map_path.with_name(f"{expected_map_path.name}.br").exists()


def test_process_css_file_reuses_manifest_when_source_unchanged(tmp_path, monkeypatch):
    source_static = tmp_path / "source_static"
    output_static = tmp_path / "dist_static"
    source_css_dir = source_static / "css"
    output_css_dir = output_static / "_build" / "css"
    source_css_dir.mkdir(parents=True)
    output_css_dir.mkdir(parents=True)

    source_path = source_css_dir / "sample.css"
    source_content = "body { color: red; }\n"
    source_path.write_text(source_content, encoding="utf-8")

    source_hash = compress.get_file_hash(source_content)
    minified_output = "body{color:red}"
    output_hash = compress.get_file_hash(minified_output)
    hashed_output = output_css_dir / f"sample.{output_hash}.css"
    hashed_output.write_text(minified_output, encoding="utf-8")
    (output_css_dir / "sample.map").write_text('{"version":3,"file":"sample.css"}', encoding="utf-8")

    existing_manifest = {
        "css/sample.css": {
            "hash": source_hash,
            "path": f"_build/css/{hashed_output.name}",
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
