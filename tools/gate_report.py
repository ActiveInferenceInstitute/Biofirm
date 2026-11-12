"""Refresh or check `docs/gate.md`, the measured record of the gate arms.

`docs/gate.md` is the one document that carries measured numbers: per-arm wall
times before and after the gate was unified, the full-suite test count and the
coverage total. The After column is produced by running `./run.sh`; the Before
column is read from [`gate_baseline.json`](gate_baseline.json), the preserved
receipt for the pre-change gate that cannot be re-measured.

    uv run python tools/gate_report.py            # run every arm, rewrite the doc
    uv run python tools/gate_report.py --check    # CI: verify the doc is current

`--check` does not re-time anything. It proves the document still describes the
gate that exists: the arm list equals `./run.sh list`, the recorded `uv.lock`
digest equals the current file, every arm has a measured value, and every arm
has a baseline entry. Re-timing is `--write`, and it is deliberately not part of
the gate because a wall time is a receipt for one host, not a contract.
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
BASELINE = ROOT / "tools" / "gate_baseline.json"
RECEIPT_OPEN = "<!-- gate-receipt"
RECEIPT_CLOSE = "gate-receipt -->"
SCHEMA = "biofirm-gate-receipt/v1"
BASELINE_SCHEMA = "biofirm-gate-baseline/v1"
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


def baseline() -> dict[str, Any]:
    """Read the preserved pre-change receipt. Never written by this script."""
    if not BASELINE.is_file():
        raise SystemExit(f"missing {BASELINE.relative_to(ROOT)}")
    try:
        data = json.loads(BASELINE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise SystemExit(f"baseline is not valid JSON: {error}") from error
    if data.get("schema") != BASELINE_SCHEMA:
        raise SystemExit(f"baseline schema is {data.get('schema')!r}, expected {BASELINE_SCHEMA!r}")
    return data


def baseline_arms(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(record.get("arm")): record for record in data.get("arms", [])}


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


def receipt(records: list[dict[str, Any]], baseline_data: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "recorded": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "environment": environment(),
        "coverage_floor": COVERAGE_FLOOR,
        "baseline": {
            "file": str(BASELINE.relative_to(ROOT)),
            "schema": baseline_data["schema"],
            "commit": baseline_data.get("commit"),
            "recorded": baseline_data.get("recorded"),
            "environment": baseline_data.get("environment"),
            "arms": baseline_data.get("arms", []),
        },
        "arms": records,
    }


def render(data: dict[str, Any]) -> str:
    descriptions = arm_descriptions()
    environment_data = data["environment"]
    before_arms = baseline_arms(data["baseline"])
    rows = "\n".join(
        "| `{}` | {} | {} | {} |".format(
            record["arm"],
            format_seconds(before_arms.get(record["arm"], {}).get("seconds")),
            format_seconds(record["seconds"]),
            descriptions.get(record["arm"], ""),
        )
        for record in data["arms"]
    )
    by_arm = {record["arm"]: record for record in data["arms"]}
    full = by_arm.get("test", {})
    fast = by_arm.get("test-fast", {})
    gnn = by_arm.get("gnn", {})
    baseline_test = before_arms.get("test", {})
    baseline_data = data["baseline"]
    baseline_environment = baseline_data.get("environment") or {}
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

**Before** is the command CI ran directly, before [`../run.sh`](../run.sh)
existed: one run each on this host, preserved in
[`../tools/gate_baseline.json`](../tools/gate_baseline.json) at commit
`{baseline_data.get("commit")}`. Reconciling that measurement into a script would
mean inventing a run of a tree that no longer exists, so it stays a receipt the
gate reads instead. **After** is the arm as measured by the run that wrote this
document.

| Arm | Before | After | What it runs |
| --- | --- | --- | --- |
{rows}

`gate` and `all` are meta arms and are not timed here: `gate` checks this
document and `all` runs the other arms in order. `test-fast` had no CI arm
before the gate existed; its baseline is the same selection run by hand.

The host is noisy and warm caches persist between runs, so single samples differ
by tens of seconds. Read both columns as receipts, not as a controlled benchmark;
the change to review is structural — interpreter-independent arms run once
instead of twice per push, and each job resolves its environment once instead of
once per command.

## Measured facts

- Full suite (`test`): **{full.get("tests_passed", "unrecorded")} passed** with
  **{full.get("coverage_percent", "unrecorded")}% coverage** against the
  {COVERAGE_FLOOR}% floor.
- Fast arm (`test-fast`): **{fast.get("tests_passed", "unrecorded")} passed**.
  It runs the same suite without coverage and without `tests/test_gnn.py`,
  which the `gnn` arm owns.
- GNN conformance (`gnn`): **{gnn.get("tests_passed", "unrecorded")} passed**.

The suite composition did not change: before the gate the same suite reported
**{baseline_test.get("tests_passed", "unrecorded")} passed** at
**{baseline_test.get("coverage_percent", "unrecorded")}% coverage**.

These are one run each on the host in the receipt below. Wall times are receipts,
not contracts: a slower or faster host does not invalidate them, and nothing in
CI compares them.

## Environment

| Field | Baseline | This run |
| --- | --- | --- |
| Host | `{baseline_environment.get("system")}/{baseline_environment.get("machine")}` | `{environment_data["system"]}/{environment_data["machine"]}` |
| Python | `{baseline_environment.get("python")}` | `{environment_data["python"]}` |
| uv | `{baseline_environment.get("uv")}` | `{environment_data["uv"]}` |
| `uv.lock` SHA-256 | not recorded | `{environment_data["lock_sha256"]}` |
| Recorded | `{baseline_data.get("recorded")}` | `{data["recorded"]}` |

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


def format_seconds(seconds: Any) -> str:
    return "not measured" if not isinstance(seconds, (int, float)) else f"{seconds}s"


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
    document = DOC.read_text(encoding="utf-8")
    data = parse_receipt(document)
    baseline_data = baseline()
    before = baseline_arms(baseline_data)
    problems: list[str] = []
    if data.get("schema") != SCHEMA:
        problems.append(f"receipt schema is {data.get('schema')!r}, expected {SCHEMA!r}")
    expected = [arm for arm in gate_arms() if arm not in UNMEASURED_ARMS]
    recorded = [record.get("arm") for record in data.get("arms", [])]
    if recorded != expected:
        problems.append(f"arm list drifted: document {recorded}, run.sh {expected}")
    if "| Arm | Before | After | What it runs |" not in document:
        problems.append("the arms table has no Before/After columns")
    if not re.fullmatch(r"[0-9a-f]{40}", str(baseline_data.get("commit"))):
        problems.append("the baseline receipt has no full pre-change commit")
    for arm in expected:
        if arm not in before:
            problems.append(f"baseline receipt has no entry for arm {arm}")
        elif not isinstance(before[arm].get("seconds"), (int, float)):
            problems.append(f"baseline entry for arm {arm} has no measured wall time")
        elif not before[arm].get("command"):
            problems.append(f"baseline entry for arm {arm} records no command")
    if data.get("baseline", {}).get("commit") != baseline_data.get("commit"):
        problems.append("document baseline provenance does not match the baseline receipt")
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
    baseline_data = baseline()
    records = [measure(arm) for arm in gate_arms() if arm not in UNMEASURED_ARMS]
    data = receipt(records, baseline_data)
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
