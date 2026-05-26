import importlib.util
from pathlib import Path

COMPRESS_PATH = Path(__file__).resolve().parents[1] / "build" / "compress.py"
SPEC = importlib.util.spec_from_file_location("compress_module", COMPRESS_PATH)
compress = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(compress)


def test_process_js_file_rebuilds_stale_unminified_artifact(tmp_path, monkeypatch):
    static_dir = tmp_path / "static"
    js_dir = static_dir / "js"
    js_dir.mkdir(parents=True)

    source_path = js_dir / "sample.js"
    source_content = "function demo () { return 1 + 2; }\n"
    source_path.write_text(source_content, encoding="utf-8")

    stale_hash = compress.get_file_hash(source_content)
    stale_output = js_dir / f"sample.{stale_hash}.js"
    stale_output.write_text(source_content, encoding="utf-8")

    existing_manifest = {
        "js/sample.js": {
            "hash": stale_hash,
            "path": f"js/{stale_output.name}",
        }
    }
    manifest = {}

    minified_content = "function demo(){return 3}\n"

    def fake_obfuscate_js(input_path, output_path):
        assert input_path == str(source_path)
        Path(output_path).write_text(minified_content, encoding="utf-8")
        return True

    monkeypatch.setattr(compress, "STATIC_DIR", str(static_dir))
    monkeypatch.setattr(compress, "obfuscate_js", fake_obfuscate_js)

    assert compress.process_js_file(str(source_path), manifest, existing_manifest) is True

    expected_hash = compress.get_file_hash(minified_content)
    expected_name = f"sample.{expected_hash}.js"
    expected_path = js_dir / expected_name

    assert manifest["js/sample.js"]["hash"] == stale_hash
    assert manifest["js/sample.js"]["path"] == f"js/{expected_name}"
    assert expected_path.read_text(encoding="utf-8") == minified_content
    assert not stale_output.exists()
