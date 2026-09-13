"""Reproduce the pinned metadata-only dataclasses marker correction."""

from __future__ import annotations

import base64
import csv
import hashlib
import io
import urllib.request
import zipfile
from pathlib import Path

URL = "https://files.pythonhosted.org/packages/c3/90/bf149bccebdc19b21197ee779663564c4d8573923023efc26ca89b0da3c8/scikit_mine-1.0.0-py3-none-any.whl"
UPSTREAM = "74b3b8104882280eb8fc254399b541f652d03c2a0f2ca55d0e97993b7e72938e"
OLD = "scikit_mine-1.0.0.dist-info"
NEW = "scikit_mine-1.0.0+smartref.1.dist-info"


def main() -> None:
    """Verify and reproduce the wheel without changing upstream implementation bytes.

    Raises:
        ValueError: Upstream bytes or the exact metadata patch precondition changed.

    """
    with urllib.request.urlopen(URL, timeout=30) as response:
        data = response.read()
    if hashlib.sha256(data).hexdigest() != UPSTREAM:
        message = "upstream wheel digest changed"
        raise ValueError(message)
    entries = {}
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for name in archive.namelist():
            if name.endswith("/RECORD"):
                continue
            contents = archive.read(name)
            if name == OLD + "/METADATA":
                text = contents.decode()
                matches = [
                    line
                    for line in text.splitlines(keepends=True)
                    if line.lower().startswith("requires-dist: dataclasses")
                ]
                if len(matches) != 1 or "Version: 1.0.0\n" not in text:
                    message = "upstream metadata patch precondition changed"
                    raise ValueError(message)
                contents = (
                    text.replace("Version: 1.0.0\n", "Version: 1.0.0+smartref.1\n", 1)
                    .replace(matches[0], matches[0].rstrip("\n") + '; python_version < "3.7"\n', 1)
                    .encode()
                )
            entries[name.replace(OLD, NEW, 1)] = contents
    rows = [
        (
            name,
            "sha256="
            + base64.urlsafe_b64encode(hashlib.sha256(value).digest()).rstrip(b"=").decode(),
            str(len(value)),
        )
        for name, value in sorted(entries.items())
    ]
    record = NEW + "/RECORD"
    rows.append((record, "", ""))
    output = io.StringIO()
    csv.writer(output, lineterminator="\n").writerows(rows)
    entries[record] = output.getvalue().encode()
    path = Path(__file__).with_name("scikit_mine-1.0.0+smartref.1-py3-none-any.whl")
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, contents in sorted(entries.items()):
            info = zipfile.ZipInfo(name, (2026, 9, 12, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, contents)


if __name__ == "__main__":
    main()
