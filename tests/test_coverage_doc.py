"""Docs-as-tests: docs/coverage.md must match the OpenAPI spec.

If this fails, regenerate with:  python tools/gen_coverage.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tools.gen_coverage import generate  # noqa: E402

COVERAGE = os.path.join(os.path.dirname(__file__), "..", "docs", "coverage.md")


def test_coverage_doc_is_current():
    assert os.path.exists(COVERAGE), (
        "docs/coverage.md is missing - run: python tools/gen_coverage.py")
    with open(COVERAGE) as f:
        committed = f.read()
    current = generate()
    assert committed == current, (
        "docs/coverage.md is stale - regenerate with: python tools/gen_coverage.py")
