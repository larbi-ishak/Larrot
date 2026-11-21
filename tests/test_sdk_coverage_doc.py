"""Docs-as-tests: SDK_COVERAGE.md must match a fresh generation.

Skipped when the official SDKs are not installed (the numbers need
them); CI installs larrot[sdk] and enforces it.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

pytest.importorskip("huaweicloudsdkcore",
                    reason="official SDK not installed (pip install larrot[sdk])")

from tools.sdk_coverage import generate  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "..", "SDK_COVERAGE.md")


def test_sdk_coverage_doc_current():
    assert os.path.exists(OUT), (
        "SDK_COVERAGE.md is missing - run: python3 tools/sdk_coverage.py")
    with open(OUT) as f:
        committed = f.read()
    current = generate()
    assert committed == current, (
        "SDK_COVERAGE.md is stale - regenerate with: python3 tools/sdk_coverage.py")
