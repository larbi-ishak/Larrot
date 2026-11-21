"""Docs-as-tests: the conformance scorecard must match a fresh run.

If this fails, the committed CONFORMANCE_REPORT.md is stale - the run has
already regenerated it, so just commit the updated file.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

REPORT = os.path.join(os.path.dirname(__file__), "..", "CONFORMANCE_REPORT.md")


def test_conformance_report_current():
    assert os.path.exists(REPORT), (
        "CONFORMANCE_REPORT.md is missing - run: python3 tools/conformance.py")
    with open(REPORT) as f:
        before = f.read()

    from tools.conformance import run
    exit_code = run()

    with open(REPORT) as f:
        after = f.read()
    assert before == after, (
        "CONFORMANCE_REPORT.md is stale - commit the regenerated file "
        "(python3 tools/conformance.py)")
    assert exit_code == 0, "conformance suite has failing checks"
