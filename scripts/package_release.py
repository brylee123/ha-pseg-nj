"""Build an installable component archive and its checksum."""

import hashlib
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
component = root / "custom_components/pseg_nj"
destination = root / "dist"
destination.mkdir(exist_ok=True)
archive_path = destination / "pseg_nj.zip"
with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(component.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
            archive.write(path, path.relative_to(component).as_posix())
digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
(destination / "SHA256SUMS").write_text(f"{digest}  pseg_nj.zip\n", encoding="utf-8")
