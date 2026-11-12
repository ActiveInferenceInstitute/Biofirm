#!/usr/bin/env bash
# Biofirm gate — the only entry point for this repository's checks.
#
# `.github/workflows/ci.yml` runs these arms and nothing else, so a local green
# run and a CI green run execute the same commands. Every arm is independent and
# calls one command; no arm repeats another arm's work.
#
#   ./run.sh sync       Lock the environment for the selected interpreter.
#   ./run.sh deps       Verify uv.lock matches the manifests.
#   ./run.sh lint       ruff check and ruff format --check on src tests tools.
#   ./run.sh types      Strict mypy on src/biofirm.
#   ./run.sh test       pytest with the 90% coverage floor (the full suite).
#   ./run.sh test-fast  pytest without coverage and without tests/test_gnn.py.
#   ./run.sh links      tools/verify_repository.py: relative links, source data,
#                       notebooks, credential patterns, required documents.
#   ./run.sh docs       biofirm validate and biofirm validate-data.
#   ./run.sh bandit     bandit on src and tools.
#   ./run.sh build      Build sdist and wheel into dist/.
#   ./run.sh install    Install dist/ into a clean venv and exercise the CLI
#                       outside the checkout, from the locked requirements.
#   ./run.sh secret     gitleaks scan with a synthetic negative control.
#   ./run.sh gnn        Pinned GNN conformance: the shared gnn.importers reader
#                       from the pinned revision, then tests/test_gnn.py.
#   ./run.sh gate       Check docs/gate.md matches this arm list and environment.
#   ./run.sh all        Every arm above, in CI order.
#
# Environment:
#   BIOFIRM_PYTHON  Interpreter used for `sync`, `install` and the GNN runtime
#                   (default: 3.12). CI sets it per job and matrix leg.
#   GNN_CHECKOUT    Already-provisioned GNN checkout for `gnn`. Without it the
#                   script reuses a usable sibling checkout or provisions the
#                   pinned revision in a temporary directory. The arm exports
#                   GNN_EXPORT, a clean `git archive` of that revision's `src`,
#                   so neither the reader nor the tests run from a working tree.
#
# Runtime numbers for this host live in docs/gate.md, which
# tools/gate_report.py refreshes; do not hand-edit them.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
cd "$ROOT"

cleanup() {
    local path
    for path in ${CLEANUP[@]+"${CLEANUP[@]}"}; do
        [[ -n "$path" ]] && rm -rf -- "$path"
    done
}
trap cleanup EXIT

UV="${UV:-uv}"
PROJECT_PYTHON="${BIOFIRM_PYTHON:-3.12}"
PIN_FILE=".github/gnn-pin.json"
GNN_UPSTREAM="https://github.com/ActiveInferenceInstitute/Generalized_Notation_Notation.git"
GNN_DEPENDENCIES=(numpy defusedxml psutil)
ARMS=(
    sync deps lint types test test-fast links docs bandit build install secret gnn gate
)
CLEANUP=()

usage() {
    sed -n '2,/^# Runtime numbers/p' "$0" | sed -e 's/^# \{0,1\}//'
}

die() {
    printf 'run.sh: %s\n' "$*" >&2
    exit 1
}

require_command() {
    command -v "$1" >/dev/null 2>&1 || die "required command not found: $1"
}

pin_field() {
    python3 -c "import json; print(json.load(open('$PIN_FILE'))['$1'])"
}

sha256_file() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | awk '{print $1}'
    else
        shasum -a 256 "$1" | awk '{print $1}'
    fi
}

arm_sync() {
    "$UV" sync --frozen --all-extras --python "$PROJECT_PYTHON"
}

arm_deps() {
    "$UV" lock --check
}

arm_lint() {
    "$UV" run --no-sync ruff check src tests tools
    "$UV" run --no-sync ruff format --check src tests tools
}

arm_types() {
    "$UV" run --no-sync mypy --python-version 3.12 src/biofirm
}

arm_test() {
    "$UV" run --no-sync pytest \
        --cov=biofirm --cov-report=term-missing --cov-fail-under=90
}

arm_test_fast() {
    # tests/test_gnn.py has its own arm (`gnn`) and the coverage floor belongs to
    # the full arm, so this selection is the fast signal, not a narrowed suite.
    "$UV" run --no-sync pytest -q --ignore=tests/test_gnn.py
}

arm_links() {
    "$UV" run --no-sync python tools/verify_repository.py
}

arm_docs() {
    "$UV" run --no-sync biofirm validate
    "$UV" run --no-sync biofirm validate-data
}

arm_bandit() {
    "$UV" run --no-sync bandit -q -r src tools
}

arm_build() {
    "$UV" run --no-sync python -m build
}

arm_install() {
    local workdir wheel
    workdir="$(mktemp -d "${TMPDIR:-/tmp}/biofirm-install.XXXXXX")"
    CLEANUP+=("$workdir")
    "$UV" export --all-extras --format requirements.txt --locked \
        --no-emit-project --no-header \
        --output-file "$workdir/requirements.lock"
    "$UV" venv --python "$PROJECT_PYTHON" "$workdir/venv"
    "$UV" pip install --python "$workdir/venv/bin/python" \
        --requirement "$workdir/requirements.lock"
    shopt -s nullglob
    local wheels=("$ROOT"/dist/*.whl)
    shopt -u nullglob
    ((${#wheels[@]} == 1)) || {
        arm_build
        shopt -s nullglob
        wheels=("$ROOT"/dist/*.whl)
        shopt -u nullglob
    }
    ((${#wheels[@]} == 1)) || die "expected one wheel in dist/, found ${#wheels[@]}"
    wheel="${wheels[0]}"
    "$UV" pip install --python "$workdir/venv/bin/python" --no-deps "$wheel"
    python3 - "$workdir" <<'PY'
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
root.joinpath("description.txt").write_text(
    "A river supports biodiversity between 40 and 80 index.", encoding="utf-8"
)
root.joinpath("state.json").write_text(
    json.dumps({"biodiversity": 40, "soil_moisture": 40, "water_quality": 40}),
    encoding="utf-8",
)
PY
    local bin="$workdir/venv/bin/biofirm"
    (
        cd "$workdir"
        "$bin" validate
        "$bin" simulate --steps 2 --controller slide-rule --output run.json
        "$bin" sweep --steps 1 --seeds 1 2 --controller random --output sweep.json
        "$bin" analyze --input run.json --output analysis.json
        "$bin" visualize --input run.json --output run.png
        "$bin" parse-description --input description.txt --output profile.json
        "$bin" business-evaluate --state state.json
        test -s run.json
        test -s sweep.json
        test -s analysis.json
        test -s run.png
        test -s profile.json
    )
}

arm_secret() {
    require_command curl
    require_command tar
    local version="8.30.1" asset checksum
    case "$(uname -s)-$(uname -m)" in
        Linux-x86_64) asset="linux_x64"; checksum="551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb" ;;
        Linux-aarch64 | Linux-arm64) asset="linux_arm64"; checksum="e4a487ee7ccd7d3a7f7ec08657610aa3606637dab924210b3aee62570fb4b080" ;;
        Darwin-arm64) asset="darwin_arm64"; checksum="b40ab0ae55c505963e365f271a8d3846efbc170aa17f2607f13df610a9aeb6a5" ;;
        Darwin-x86_64) asset="darwin_x64"; checksum="dfe101a4db2255fc85120ac7f3d25e4342c3c20cf749f2c20a18081af1952709" ;;
        *) die "no pinned gitleaks build for $(uname -s)-$(uname -m)" ;;
    esac
    local scanner control
    scanner="$(mktemp -d "${TMPDIR:-/tmp}/biofirm-gitleaks.XXXXXX")"
    control="$(mktemp -d "${TMPDIR:-/tmp}/biofirm-secret-control.XXXXXX")"
    CLEANUP+=("$scanner" "$control")
    curl --fail --silent --show-error --location \
        "https://github.com/gitleaks/gitleaks/releases/download/v${version}/gitleaks_${version}_${asset}.tar.gz" \
        --output "$scanner/release.tar.gz"
    test "$(sha256_file "$scanner/release.tar.gz")" = "$checksum" ||
        die "gitleaks tarball checksum mismatch"
    tar -xzf "$scanner/release.tar.gz" -C "$scanner" gitleaks
    test "$("$scanner/gitleaks" version)" = "$version" ||
        die "gitleaks version mismatch"

    local control
    python3 - "$control/control.txt" <<'PY'
import secrets
import string
import sys
from pathlib import Path

synthetic = "ghp_" + "".join(
    secrets.choice(string.ascii_letters + string.digits) for _ in range(36)
)
Path(sys.argv[1]).write_text('token = "' + synthetic + '"\n', encoding="utf-8")
PY
    if "$scanner/gitleaks" dir --redact --no-banner --exit-code 1 "$control"; then
        die "secret scanner failed to reject the synthetic control"
    else
        test "$?" = 1 || die "secret scanner control exited unexpectedly"
    fi

    # Exact historical exceptions must not exempt a new commit at the old path.
    mkdir -p "$control/Scripts/utils"
    cp "$control/control.txt" "$control/Scripts/utils/llm_keys.key"
    cp .gitleaksignore "$control/.gitleaksignore"
    git init --quiet "$control"
    git -C "$control" add -f -- .gitleaksignore Scripts/utils/llm_keys.key
    git -C "$control" -c user.name='Scanner control' -c user.email=control@example.invalid \
        -c commit.gpgsign=false -c core.hooksPath=/dev/null \
        commit --quiet -m 'Synthetic scanner negative control'
    if "$scanner/gitleaks" git --redact --no-banner --exit-code 1 --log-opts=--all \
        --gitleaks-ignore-path "$ROOT/.gitleaksignore" "$control"; then
        die "exact historical exceptions admitted a new credential"
    else
        test "$?" = 1 || die "secret scanner control exited unexpectedly"
    fi

    "$scanner/gitleaks" git --redact --no-banner --exit-code 1 --log-opts=--all \
        --gitleaks-ignore-path .gitleaksignore .
}

gnn_checkout_is_usable() {
    local checkout="$1"
    [[ -d "$checkout/.git" && -x "$checkout/.venv/bin/python" ]] || return 1
    git -C "$checkout" cat-file -e "$(pin_field revision)^{commit}" 2>/dev/null
}

gnn_provision() {
    local checkout="$1" revision tag
    revision="$(pin_field revision)"
    tag="$(pin_field tag)"
    git init --quiet "$checkout"
    git -C "$checkout" remote add origin "$GNN_UPSTREAM"
    # A pin that no longer resolves upstream fails here rather than skipping.
    git -C "$checkout" fetch --depth 1 origin "$revision" "refs/tags/$tag:refs/tags/$tag"
    git -C "$checkout" checkout --quiet --detach "$revision"
    # The tag the pin names must dereference to the revision it names.
    test "$(git -C "$checkout" rev-parse "$tag^{commit}")" = "$revision" ||
        die "pin tag $tag does not resolve to revision $revision"
    "$UV" venv --python "$PROJECT_PYTHON" --no-project "$checkout/.venv"
    "$UV" pip install --python "$checkout/.venv/bin/python" "${GNN_DEPENDENCIES[@]}"
}

arm_gnn() {
    if [[ -n "${GNN_CHECKOUT:-}" ]]; then
        export GNN_CHECKOUT
    else
        local sibling="$ROOT/../Generalized_Notation_Notation"
        if gnn_checkout_is_usable "$sibling"; then
            export GNN_CHECKOUT="$sibling"
        else
            local workdir="${TMPDIR:-/tmp}/biofirm-gnn-pinned"
            if ! gnn_checkout_is_usable "$workdir"; then
                rm -rf "$workdir"
                mkdir -p "$workdir"
                gnn_provision "$workdir"
            fi
            export GNN_CHECKOUT="$workdir"
        fi
    fi

    # The reader and the tests run from a clean export of the pinned revision in
    # the interpreter this arm provisioned, so a dirty sibling checkout cannot
    # contaminate either. `--repo .` is this checkout: the pin, the pointer and
    # the specification under it are what the reader checks.
    local revision
    revision="$(pin_field revision)"
    GNN_EXPORT="$(mktemp -d "${TMPDIR:-/tmp}/biofirm-gnn-src.XXXXXX")"
    export GNN_EXPORT
    CLEANUP+=("$GNN_EXPORT")
    git -C "$GNN_CHECKOUT" archive "$revision" src | tar -x -C "$GNN_EXPORT"
    PYTHONPATH="$GNN_EXPORT/src" "$GNN_CHECKOUT/.venv/bin/python" -m gnn.importers check \
        --repo . --require-pointer \
        --workflow .github/workflows/ci.yml --job gnn-conformance

    "$UV" run --no-sync pytest tests/test_gnn.py -q
    if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
        local version tag
        version="$(pin_field version)"
        tag="$(pin_field tag)"
        test "${version#v}" = "${tag#v}" ||
            die "pin version ${version} and tag ${tag} disagree"
        printf 'gnn-version=%s\n' "${version#v}" >>"$GITHUB_STEP_SUMMARY"
    fi
}

arm_gate() {
    "$UV" run --no-sync python tools/gate_report.py --check
}

arm_all() {
    local arm
    for arm in sync deps lint types test links docs gate bandit build install secret gnn; do
        printf '\n=== %s ===\n' "$arm"
        "arm_${arm//-/_}"
    done
}

main() {
    (($# > 0)) || {
        usage
        exit 2
    }
    local requested=("$@") arm
    if [[ "${requested[0]}" == "list" ]]; then
        printf '%s\n' "${ARMS[@]}"
        return 0
    fi
    if [[ "${requested[0]}" == "-h" || "${requested[0]}" == "--help" ]]; then
        usage
        return 0
    fi
    for arm in "${requested[@]}"; do
        if [[ "$arm" == "all" ]]; then
            arm_all
            continue
        fi
        local known=0 candidate
        for candidate in "${ARMS[@]}"; do
            [[ "$candidate" == "$arm" ]] && known=1
        done
        ((known)) || {
            printf 'run.sh: unknown arm %s\n\n' "$arm" >&2
            usage >&2
            exit 2
        }
        "arm_${arm//-/_}"
    done
}

main "$@"
