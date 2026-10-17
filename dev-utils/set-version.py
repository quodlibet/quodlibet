#!/usr/bin/env python3
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Set the Quod Libet version everywhere it lives.

set-version.py X.Y.Z       release: (X, Y, Z), plus an appdata <release> entry
set-version.py X.Y.Z-pre   development: (X, Y, Z, -1)
"""

import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = ROOT / "pyproject.toml"
CONST = ROOT / "quodlibet" / "const.py"
APPDATA = sorted((ROOT / "data").glob("*.appdata.xml.in"))

VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)(-pre)?$")


def parse(version: str) -> tuple[int, ...]:
    match = VERSION_RE.match(version)
    if not match:
        raise ValueError(f"Expected X.Y.Z or X.Y.Z-pre, got {version!r}")
    numbers = tuple(int(n) for n in match.groups()[:3])
    return numbers + (-1,) if match.group(4) else numbers


def set_pyproject(text: str, version: str) -> str:
    return re.sub(
        r'^version = ".*"$', f'version = "{version}"', text, count=1, flags=re.M
    )


def set_const(text: str, numbers: tuple[int, ...]) -> str:
    args = ", ".join(map(str, numbers))
    return re.sub(
        r'^VERSION_TUPLE = Version\("", .*\)$',
        f'VERSION_TUPLE = Version("", {args})',
        text,
        count=1,
        flags=re.M,
    )


def add_appdata_release(text: str, version: str, day: date) -> str:
    if f'<release version="{version}"' in text:
        return text
    entry = f'<release version="{version}" date="{day.isoformat()}"/>'
    return re.sub(
        r"^(\s*)<release ",
        rf"\g<1>{entry}\n\g<1><release ",
        text,
        count=1,
        flags=re.M,
    )


def update(path: Path, new_text: str) -> None:
    if path.read_text() == new_text:
        sys.exit(f"Couldn't update {path.relative_to(ROOT)} (or already set)")
    path.write_text(new_text)


def main(version: str) -> None:
    numbers = parse(version)
    update(PYPROJECT, set_pyproject(PYPROJECT.read_text(), version))
    update(CONST, set_const(CONST.read_text(), numbers))
    if numbers[-1] != -1:
        for path in APPDATA:
            update(path, add_appdata_release(path.read_text(), version, date.today()))
    print(f"Set version to {version} {numbers}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    try:
        main(sys.argv[1])
    except ValueError as e:
        sys.exit(str(e))
