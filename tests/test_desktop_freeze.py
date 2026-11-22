"""Guard: the web port must not modify the desktop application.

The browser version (``web/``) reuses the physics and tutorial code by
copying it, unchanged, into the Pyodide bundle. The desktop app is frozen at
the ``desktop-v1.0`` tag. Any edit to the shared code fails this test, so a
web-side convenience cannot quietly change or break the desktop version.

If a change to shared code is ever genuinely needed, it is a deliberate
decision: agree it, then move the tag (or add a new one) — don't weaken this
test.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

FREEZE_TAG = "desktop-v1.0"
FROZEN_PATHS = ("telescope_sim", "telescope_gui", "main.py", "gui.py",
                "requirements.txt")
REPO_ROOT = Path(__file__).resolve().parent.parent


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=REPO_ROOT,
                          capture_output=True, text=True)


@pytest.fixture(scope="module")
def freeze_tag():
    if shutil.which("git") is None:
        pytest.skip("git not available")
    if _git("rev-parse", "--verify", "--quiet",
            f"{FREEZE_TAG}^{{commit}}").returncode != 0:
        pytest.skip(f"tag {FREEZE_TAG} not present (e.g. shallow clone)")
    return FREEZE_TAG


def test_desktop_code_matches_freeze_tag(freeze_tag):
    """Committed AND uncommitted changes count: diff the work tree."""
    diff = _git("diff", "--stat", freeze_tag, "--", *FROZEN_PATHS)
    assert diff.returncode == 0, diff.stderr
    assert diff.stdout.strip() == "", (
        f"desktop code differs from {freeze_tag}:\n{diff.stdout}")


def test_no_new_untracked_files_in_desktop_packages(freeze_tag):
    """A new module dropped into a frozen package is a change too."""
    out = _git("ls-files", "--others", "--exclude-standard", "--",
               *FROZEN_PATHS)
    assert out.stdout.strip() == "", (
        f"untracked files in frozen paths:\n{out.stdout}")
