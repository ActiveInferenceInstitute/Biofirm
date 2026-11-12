"""Refresh or check `docs/gate.md`, the measured record of the gate arms.

`docs/gate.md` is the one document that carries measured numbers: per-arm wall
times, the full-suite test count and the coverage total. Those values are
produced by running `./run.sh`, never typed by hand.

    uv run python tools/gate_report.py            # run every arm, rewrite the doc
    uv run python tools/gate_report.py --check    # CI: verify the doc is current

`--check` does not re-time anything. It proves the document still describes the
gate that exists: the arm list equals `./run.sh list`, the recorded `uv.lock`
digest equals the current file, and every arm has a measured value. Re-timing is
`--write`, and it is deliberately not part of the gate because a wall time is a
receipt for one host, not a contract.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re

# Subprocesses run this repository's own arms; argv is never a shell string.
import subprocess  # nosec B404
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "gate.md"
RECEIPT_OPEN = "<!-- gate-receipt"
RECEIPT_CLOSE = "gate-receipt -->"
SCHEMA = "biofirm-gate-receipt/v1"
META_ARMS = {"all", "list"}
UNMEASURED_ARMS = {"all", "gate"}
COVERAGE_FLOOR = 90
PASSED_PATTERN = re.compile(r"(\d+) passed")
COVERAGE_PATTERN = re.compile(r"Total coverage:\s*([\d.]+)%")
ARM_HEADER_PATTERN = re.compile(r"^#   \./run\.sh (\S+)\s+(.+)$")
ARM_DETAIL_PATTERN = re.compile(r"^#\s{7,}(\S.*)$")


def run(*command: str) -> subprocess.CompletedProcess[str]:
    # Fixed argv passed by this script; no shell, no caller input.
    return subprocess.run(  # nosec B603
        command, cwd=ROOT, capture_output=True, text=True, check=False
    )


def gate_arms() -> list[str]:
    completed = run("./run.sh", "list")
    if completed.returncode != 0:
        raise SystemExit(f"cannot list arms: {completed.stderr.strip()}")
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def arm_descriptions() -> dict[str, str]:
    """Read the arm table from run.sh's own header so prose cannot drift."""
    descriptions: dict[str, str] = {}
    current: str | None = None
    for line in (ROOT / "run.sh").read_text(encoding="utf-8").splitlines():
        header = ARM_HEADER_PATTERN.match(line)
        if header:
            current = header.group(1)
            descriptions[current] = header.group(2).strip()
            continue
        detail = ARM_DETAIL_PATTERN.match(line)
        if detail and current is not None:
            descriptions[current] = f"{descriptions[current]} {detail.group(1).strip()}"
    return descriptions


def lock_digest() -> str:
    return hashlib.sha256((ROOT / "uv.lock").read_bytes()).hexdigest()


def environment() -> dict[str, str]:
    uv = run("uv", "--version").stdout.split()
    python = run(
        "uv", "run", "--no-sync", "python", "-c", "import sys; print(sys.version.split()[0])"
    )
    return {
        "system": platform.system(),
        "machine": platform.machine(),
        "python": python.stdout.strip() or "unavailable",
        "uv": uv[1] if len(uv) > 1 else "unavailable",
        "lock_sha256": lock_digest(),
    }


def measure(arm: str) -> dict[str, Any]:
    started = time.monotonic()
    # The arm name comes from `run.sh list`, not from user input.
    completed = subprocess.run(  # nosec B603
        ["./run.sh", arm], cwd=ROOT, capture_output=True, text=True, check=False
    )
    seconds = round(time.monotonic() - started, 1)
    output = completed.stdout + completed.stderr
    if completed.returncode != 0:
        tail = "\n".join(output.strip().splitlines()[-20:])
        raise SystemExit(f"arm {arm} failed (exit {completed.returncode}):\n{tail}")
    record: dict[str, Any] = {"arm": arm, "seconds": seconds, "status": "passed"}
    passed = PASSED_PATTERN.search(output)
    if passed:
        record["tests_passed"] = int(passed.group(1))
    coverage = COVERAGE_PATTERN.search(output)
    if coverage:
        record["coverage_percent"] = float(coverage.group(1))
    return record


def receipt(records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "recorded": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "environment": environment(),
        "coverage_floor": COVERAGE_FLOOR,
        "arms": records,
    }


def render(data: dict[str, Any]) -> str:
    descriptions = arm_descriptions()
    environment_data = data["environment"]
    rows = "\n".join(
        "| `{}` | {} | {} |".format(
            record["arm"], descriptions.get(record["arm"], ""), f"{record['seconds']}s"
        )
        for record in data["arms"]
    )
    by_arm = {record["arm"]: record for record in data["arms"]}
    full = by_arm.get("test", {})
    fast = by_arm.get("test-fast", {})
    gnn = by_arm.get("gnn", {})
    receipt_json = json.dumps(data, indent=2, sort_keys=True)
    return f"""# Gate and measured arm times

<!-- generated by tools/gate_report.py; `./run.sh gate` verifies it. Do not edit. -->

One entry point, [`../run.sh`](../run.sh), runs every check this repository
gates on. `.github/workflows/ci.yml` calls the same arms, so a local green run
and a CI green run execute the same commands. Arms are independent: run one, or
run `./run.sh all` for the whole gate in CI order.

Start with `./run.sh sync` once, then the arm you need. `./run.sh list` prints
the arm names and `./run.sh --help` the full table.

## Arms

| Arm | What it runs | Last measured wall time |
| --- | --- | --- |
{rows}

`gate` and `all` are meta arms and are not timed here: `gate` checks this
document and `all` runs the other arms in order.

## Measured facts

- Full suite (`test`): **{full.get("tests_passed", "unrecorded")} passed** with
  **{full.get("coverage_percent", "unrecorded")}% coverage** against the
  {COVERAGE_FLOOR}% floor.
- Fast arm (`test-fast`): **{fast.get("tests_passed", "unrecorded")} passed**.
  It runs the same suite without coverage and without `tests/test_gnn.py`,
  which the `gnn` arm owns.
- GNN conformance (`gnn`): **{gnn.get("tests_passed", "unrecorded")} passed**.

These are one run each on the host in the receipt below. Wall times are receipts,
not contracts: a slower or faster host does not invalidate them, and nothing in
CI compares them.

## Environment

| Field | Value |
| --- | --- |
| Host | `{environment_data["system"]}/{environment_data["machine"]}` |
| Python | `{environment_data["python"]}` |
| uv | `{environment_data["uv"]}` |
| `uv.lock` SHA-256 | `{environment_data["lock_sha256"]}` |
| Recorded | `{data["recorded"]}` |

## Receipt

{RECEIPT_OPEN}
```json
{receipt_json}
```
{RECEIPT_CLOSE}

## Related

- [Documentation hub](README.md) — the topical entry point.
- [Contributing](../CONTRIBUTING.md) — when a change needs which arm.
- [Repository index](../DOCUMENTATION_INDEX.md) — every long-lived document.
"""


def parse_receipt(text: str) -> dict[str, Any]:
    start = text.find(RECEIPT_OPEN)
    end = text.find(RECEIPT_CLOSE)
    if start < 0 or end < 0 or end < start:
        raise SystemExit(f"{DOC.relative_to(ROOT)} has no gate receipt block")
    block = text[start:end]
    fenced = block.split("```json", 1)
    if len(fenced) != 2:
        raise SystemExit(f"{DOC.relative_to(ROOT)} has no JSON receipt")
    payload = fenced[1].split("```", 1)
    if len(payload) != 2:
        raise SystemExit(f"{DOC.relative_to(ROOT)} has an unterminated JSON receipt")
    try:
        return json.loads(payload[0])
    except json.JSONDecodeError as error:
        raise SystemExit(f"receipt is not valid JSON: {error}") from error


def check() -> int:
    if not DOC.is_file():
        print(f"missing {DOC.relative_to(ROOT)}; run --write", file=sys.stderr)
        return 1
    data = parse_receipt(DOC.read_text(encoding="utf-8"))
    problems: list[str] = []
    if data.get("schema") != SCHEMA:
        problems.append(f"receipt schema is {data.get('schema')!r}, expected {SCHEMA!r}")
    expected = [arm for arm in gate_arms() if arm not in UNMEASURED_ARMS]
    recorded = [record.get("arm") for record in data.get("arms", [])]
    if recorded != expected:
        problems.append(f"arm list drifted: document {recorded}, run.sh {expected}")
    current_lock = lock_digest()
    recorded_lock = data.get("environment", {}).get("lock_sha256")
    if recorded_lock != current_lock:
        problems.append("uv.lock changed since the numbers were recorded; rerun --write")
    for record in data.get("arms", []):
        if not isinstance(record.get("seconds"), (int, float)):
            problems.append(f"arm {record.get('arm')} has no measured wall time")
    full = next((r for r in data.get("arms", []) if r.get("arm") == "test"), None)
    if not full or "tests_passed" not in full or "coverage_percent" not in full:
        problems.append("the `test` arm has no recorded test count and coverage")
    if data.get("coverage_floor") != COVERAGE_FLOOR:
        problems.append("coverage floor in the document does not match the gate")
    if problems:
        for problem in problems:
            print(f"gate: {problem}", file=sys.stderr)
        return 1
    print(f"gate: {DOC.relative_to(ROOT)} matches run.sh and uv.lock")
    return 0


def write() -> int:
    records = [measure(arm) for arm in gate_arms() if arm not in UNMEASURED_ARMS]
    data = receipt(records)
    DOC.write_text(render(data), encoding="utf-8")
    print(f"wrote {DOC.relative_to(ROOT)} with {len(records)} arms")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check", action="store_true", help="verify docs/gate.md is current; do not re-time"
    )
    arguments = parser.parse_args(argv)
    return check() if arguments.check else write()


if __name__ == "__main__":
    os.chdir(ROOT)
    raise SystemExit(main())
