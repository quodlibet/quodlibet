# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import importlib.util
from datetime import date
from pathlib import Path

import pytest

_PATH = Path(__file__).parent.parent / "dev-utils" / "set-version.py"
_spec = importlib.util.spec_from_file_location("set_version", _PATH)
set_version = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(set_version)


def test_parse_release():
    assert set_version.parse("4.8.0") == (4, 8, 0)


def test_parse_pre_release():
    assert set_version.parse("4.8.1-pre") == (4, 8, 1, -1)


@pytest.mark.parametrize("bad", ["4.8", "4.8.0-rc1", "v4.8.0", ""])
def test_parse_rejects_other_formats(bad):
    with pytest.raises(ValueError):
        set_version.parse(bad)


def test_set_pyproject_changes_only_project_version():
    text = '[project]\nversion = "4.7.0-pre"\n[tool.mypy]\npython_version = "3.10"\n'

    result = set_version.set_pyproject(text, "4.8.0")

    assert (
        result == '[project]\nversion = "4.8.0"\n[tool.mypy]\npython_version = "3.10"\n'
    )


def test_set_const():
    text = 'VERSION_TUPLE = Version("", 4, 7, -1)\nVERSION = str(VERSION_TUPLE)\n'

    result = set_version.set_const(text, (4, 8, 0))

    assert result.startswith('VERSION_TUPLE = Version("", 4, 8, 0)\n')


def test_add_appdata_release_prepends_with_same_indent():
    text = '    <releases>\n        <release version="4.7.1" date="2025-05-31"/>\n'

    result = set_version.add_appdata_release(text, "4.8.0", date(2026, 10, 17))

    assert result == (
        "    <releases>\n"
        '        <release version="4.8.0" date="2026-10-17"/>\n'
        '        <release version="4.7.1" date="2025-05-31"/>\n'
    )


def test_add_appdata_release_is_idempotent():
    text = '        <release version="4.8.0" date="2026-10-17"/>\n'

    assert set_version.add_appdata_release(text, "4.8.0", date(2027, 1, 1)) == text


def test_patterns_match_the_real_files():
    root = _PATH.parent.parent
    pyproject = (root / "pyproject.toml").read_text()
    const = (root / "quodlibet" / "const.py").read_text()

    assert 'version = "9.9.9"' in set_version.set_pyproject(pyproject, "9.9.9")
    assert 'Version("", 9, 9, 9)' in set_version.set_const(const, (9, 9, 9))
