import zipfile

from ingest.download import fetch, read_zip_lines

UNREACHABLE_URL = "http://127.0.0.1:1/datos.zip"


def test_fetch_reuses_a_cached_file_without_downloading(tmp_path):
    cached = tmp_path / "datos.zip"
    cached.write_bytes(b"contenido")
    assert fetch(UNREACHABLE_URL, tmp_path) == cached
    assert cached.read_bytes() == b"contenido"


def test_failed_download_leaves_no_partial_file(tmp_path):
    cache_dir = tmp_path / "no" / "existe"
    try:
        fetch(UNREACHABLE_URL, cache_dir)
    except OSError:
        pass
    else:
        raise AssertionError("fetch debería haber fallado")
    assert cache_dir.is_dir()
    assert list(cache_dir.iterdir()) == []


def test_read_zip_lines_decodes_utf8_and_drops_the_bom(tmp_path):
    path = tmp_path / "texto.zip"
    content = "﻿GEN 1:1 EN el principio crió\r\nGEN 1:2 Y la tierra\n"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("texto.txt", content.encode("utf-8"))
    assert read_zip_lines(path, "texto.txt") == [
        "GEN 1:1 EN el principio crió",
        "GEN 1:2 Y la tierra",
    ]
