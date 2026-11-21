"""Generate docs/coverage.md from the OpenAPI spec: every operation, by service.

The committed file is enforced by a test (tests/test_coverage_doc.py),
so the docs cannot drift from the code. Run after adding operations:

    python tools/gen_coverage.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from collections import defaultdict  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402

from larrot.app import create_app  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "..", "COVERAGE.md")


def generate() -> str:
    client = TestClient(create_app())
    spec = client.get("/openapi.json").json()

    by_service = defaultdict(list)
    for path, methods in sorted(spec["paths"].items()):
        for method, op in methods.items():
            if method not in ("get", "post", "put", "delete", "patch", "head"):
                continue
            tags = op.get("tags") or ["untagged"]
            by_service[tags[0]].append(f"`{method.upper()}` `{path}`")

    lines = [
        "# API coverage",
        "",
        "Every operation Larrot serves, grouped by service. This page is",
        "generated from the OpenAPI spec by `tools/gen_coverage.py` and",
        "enforced by a test - it cannot drift from the code.",
        "",
    ]
    total_ops = sum(len(v) for v in by_service.values())
    lines.append(f"**{len(by_service)} services - {total_ops} operations**")
    lines.append("")
    for service in sorted(by_service):
        ops = by_service[service]
        lines.append(f"## {service} ({len(ops)})")
        lines.append("")
        lines.extend(f"- {op}" for op in sorted(ops))
        lines.append("")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    content = generate()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        f.write(content)
    print(f"wrote {os.path.normpath(OUT)}")
