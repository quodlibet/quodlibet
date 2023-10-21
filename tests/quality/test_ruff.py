import os
import subprocess

from ruff.__main__ import find_ruff_bin

from tests import QL_BASE_PATH


def test_ruff():
    ruff = find_ruff_bin()
    completed_process = subprocess.run([os.fsdecode(ruff), "check", str(QL_BASE_PATH)])
    assert completed_process.returncode == 0, "Failed with:\n{completed_process.stderr}"
