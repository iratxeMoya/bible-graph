"""Descarga con caché en disco y lectura de un fichero dentro de un zip."""

import io
import urllib.request
import zipfile
from pathlib import Path

USER_AGENT = "bible-graph-ingest/1.0"


def fetch(url: str, cache_dir: Path, force: bool = False) -> Path:
    """Descarga `url` a `cache_dir` y devuelve la ruta. Reutiliza el fichero si ya existe."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    target = cache_dir / url.rsplit("/", 1)[-1]
    if target.exists() and not force:
        return target
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    partial = target.with_suffix(target.suffix + ".part")
    with urllib.request.urlopen(request, timeout=60) as response:
        partial.write_bytes(response.read())
    partial.replace(target)
    return target


def read_zip_lines(zip_path: Path, member: str) -> list[str]:
    """Lee un fichero de texto UTF-8 (con o sin BOM) de dentro de un zip."""
    with zipfile.ZipFile(zip_path) as archive:
        with archive.open(member) as raw:
            return io.TextIOWrapper(raw, encoding="utf-8-sig").read().splitlines()
