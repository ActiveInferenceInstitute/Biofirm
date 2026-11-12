"""GNN specification conformance and pinned-parser validation tests.

These tests keep the specification in ``models/`` and the matrices the package
builds in ``biofirm.pymdp`` in agreement, and re-validate the specification with
the parser of the pinned upstream revision. The pin, the pointer and the
specification's syntax are checked by the shared ``gnn.importers`` reader that
the ``gnn`` arm of ``./run.sh`` runs; these tests do not read the pin.

The upstream parser runs against a clean export of the pinned revision, which
that arm writes to ``GNN_EXPORT`` after it materializes the revision — never
against the GNN checkout's working tree, so in-progress edits in a sibling
checkout cannot contaminate the result. The upstream half skips with an explicit
reason when no export is available, and fails instead of skipping when a
checkout was selected explicitly (CI sets ``GNN_CHECKOUT``, so a missing or
unusable export is a red check there).
"""

from __future__ import annotations

import os
import re
import subprocess
from collections.abc import Iterator
from pathlib import Path

import numpy as np
import pytest

from biofirm.gnn import (
    EXPECTED_EDGES,
    SPEC_PATH,
    GNNSpecError,
    _invariant_issues,
    conformance_issues,
    declared_matrix,
    load_spec,
    parse_spec,
)
from biofirm.pymdp import ActiveInferenceMatrices, build_active_inference_matrices

REPO_ROOT = Path(__file__).resolve().parents[1]
CHECKOUT_ENV = "GNN_CHECKOUT"
EXPORT_ENV = "GNN_EXPORT"
DEFAULT_CHECKOUT = REPO_ROOT.parent / "Generalized_Notation_Notation"
UPSTREAM_TIMEOUT_SECONDS = 300


def _checkout() -> Path:
    override = os.environ.get(CHECKOUT_ENV)
    return Path(override) if override else DEFAULT_CHECKOUT


def _spec_text() -> str:
    return SPEC_PATH.read_text(encoding="utf-8")


def _replace_block(text: str, section: str, body: str) -> str:
    pattern = re.compile(rf"(^## {re.escape(section)}\n)(.*?)(?=^## |\Z)", re.MULTILINE | re.DOTALL)
    replaced, count = pattern.subn(lambda match: match.group(1) + body, text, count=1)
    assert count == 1, f"section {section} not found"
    return replaced


def _unavailable(message: str) -> None:
    """Skip when no checkout was selected; fail when one was selected explicitly.

    ``GNN_CHECKOUT`` is the explicit selection, and CI sets it after
    provisioning the pinned revision. An unusable selected checkout must be a
    failure, never a skip: a skipped check cannot fail and so proves nothing.
    """

    if os.environ.get(CHECKOUT_ENV):
        pytest.fail(f"{CHECKOUT_ENV} selects a checkout, but {message}")
    pytest.skip(message)


@pytest.fixture(scope="module")
def pinned_upstream() -> Iterator[tuple[Path, Path]]:
    """Yield ``(checkout, exported_tree)`` for the pinned revision.

    The revision is materialized and exported by the ``gnn`` arm, which passes
    both paths in ``GNN_CHECKOUT`` and ``GNN_EXPORT``. Reading the export rather
    than the checkout keeps in-progress edits in a sibling tree out of the run.
    """

    checkout = _checkout()
    if not (checkout / ".git").exists():
        _unavailable(f"no GNN checkout exists at {checkout}")
    interpreter = checkout / ".venv" / "bin" / "python"
    if not interpreter.is_file():
        _unavailable(f"the GNN checkout at {checkout} has no .venv/bin/python interpreter")
    export = os.environ.get(EXPORT_ENV)
    if not export:
        _unavailable(
            f"{EXPORT_ENV} is unset; `./run.sh gnn` exports the pinned revision's src tree"
        )
    tree = Path(export)
    if not (tree / "src" / "gnn").is_dir():
        _unavailable(f"the export at {tree} holds no src/gnn tree")
    yield checkout, tree


def test_repository_spec_conforms_to_built_matrices() -> None:
    spec = load_spec()
    assert spec.section == "ActInfBiofirmEcosystemVariable"
    assert conformance_issues(spec) == ()


@pytest.mark.parametrize("num_bins", [3, 5, 7, 9])
def test_repository_spec_conforms_for_generalized_bins(num_bins: int) -> None:
    spec = load_spec()
    assert conformance_issues(spec, num_bins) == ()


def test_declared_matrices_match_the_built_default_model() -> None:
    spec = load_spec()
    matrices = build_active_inference_matrices()
    assert np.array_equal(declared_matrix(spec, "A_level"), matrices.A)
    assert np.array_equal(declared_matrix(spec, "B_bin"), matrices.B)
    assert np.array_equal(declared_matrix(spec, "C_level"), matrices.C)
    assert np.allclose(declared_matrix(spec, "D_bin"), matrices.D)
    assert declared_matrix(spec, "B_bin").sum(axis=0).tolist() == [[1.0, 1.0, 1.0]] * 3


def test_declared_edges_match_the_expected_dependency_structure() -> None:
    spec = load_spec()
    assert spec.edges() == EXPECTED_EDGES
    assert ("s_bin", ">", "A_level") in spec.edges()
    assert ("C_level", "-", "o_level") in spec.edges()


def test_upstream_parser_accepts_the_specification(pinned_upstream: tuple[Path, Path]) -> None:
    checkout, tree = pinned_upstream
    result = subprocess.run(
        [
            str(checkout / ".venv" / "bin" / "python"),
            "-m",
            "gnn.cli",
            "validate",
            str(SPEC_PATH),
            "--strict",
        ],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(tree / "src")},
        timeout=UPSTREAM_TIMEOUT_SECONDS,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "valid" in result.stdout


def test_upstream_export_shadows_an_installed_parser(pinned_upstream: tuple[Path, Path]) -> None:
    checkout, tree = pinned_upstream
    result = subprocess.run(
        [
            str(checkout / ".venv" / "bin" / "python"),
            "-c",
            "import gnn; print(gnn.__file__)",
        ],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(tree / "src")},
        timeout=UPSTREAM_TIMEOUT_SECONDS,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert str(tree) in result.stdout, "the export must shadow any installed gnn package"


def test_structural_drift_is_reported() -> None:
    text = _spec_text()
    assert "num_actions: 3" in text
    drifted = text.replace("num_actions: 3", "num_actions: 4")
    assert conformance_issues(parse_spec(drifted)) != ()
    dropped = text.replace("u_control>B_bin\n", "")
    issues = conformance_issues(parse_spec(dropped))
    assert any("missing declared connections" in issue for issue in issues)
    extra = text.replace("B_bin>s_bin\n", "B_bin>s_bin\nC_level>D_bin\n")
    issues = conformance_issues(parse_spec(extra))
    assert any("undeclared connections" in issue for issue in issues)


def test_declared_value_drift_is_reported() -> None:
    text = _spec_text()
    drifted = text.replace("C_level={-1.0,2.0,-1.0}", "C_level={2.0,-1.0,-1.0}")
    issues = conformance_issues(parse_spec(drifted))
    assert any("declared C_level" in issue for issue in issues)


def test_invalid_conformance_bins_are_rejected() -> None:
    spec = load_spec()
    for invalid in (True, 2.5, 1, 4):
        with pytest.raises(GNNSpecError, match="odd integer"):
            conformance_issues(spec, invalid)  # type: ignore[arg-type]


def test_nonconforming_matrices_are_detected() -> None:
    matrices = build_active_inference_matrices()
    assert _invariant_issues(matrices, 3) == []
    wrong_a = ActiveInferenceMatrices(np.full((3, 3), 1 / 3), matrices.B, matrices.C, matrices.D)
    assert any("A must be the identity" in issue for issue in _invariant_issues(wrong_a, 3))
    wrong_d = ActiveInferenceMatrices(
        matrices.A, matrices.B, matrices.C, np.array([0.5, 0.25, 0.25])
    )
    assert any("D must be uniform" in issue for issue in _invariant_issues(wrong_d, 3))
    wrong_c = ActiveInferenceMatrices(
        matrices.A, matrices.B, np.array([2.0, -1.0, -1.0]), matrices.D
    )
    assert any("C must peak" in issue for issue in _invariant_issues(wrong_c, 3))
    wrong_b = ActiveInferenceMatrices(matrices.A, np.full((3, 3, 3), 1 / 3), matrices.C, matrices.D)
    assert any("B must shift" in issue for issue in _invariant_issues(wrong_b, 3))


def test_missing_and_malformed_specifications_fail_loudly(tmp_path: Path) -> None:
    with pytest.raises(GNNSpecError, match="cannot read"):
        load_spec(tmp_path / "absent.gnn.md")
    with pytest.raises(GNNSpecError, match="missing required sections"):
        parse_spec("## GNNSection\nOnly\n")
    with pytest.raises(GNNSpecError, match="no variables"):
        parse_spec(_replace_block(_spec_text(), "StateSpaceBlock", "# no declarations\n"))
    with pytest.raises(GNNSpecError, match="unparsable StateSpaceBlock"):
        parse_spec(_spec_text().replace("A_level[3,3,type=float]", "A_level = identity"))
    with pytest.raises(GNNSpecError, match="non-integer dimension"):
        parse_spec(_spec_text().replace("A_level[3,3,type=float]", "A_level[n,3,type=float]"))
    with pytest.raises(GNNSpecError, match="duplicate StateSpaceBlock"):
        parse_spec(_spec_text().replace("A_level[3,3,type=float]", "s_bin[3,1,type=int]"))
    with pytest.raises(GNNSpecError, match="no edges"):
        parse_spec(_replace_block(_spec_text(), "Connections", "# no edges\n"))
    with pytest.raises(GNNSpecError, match="unparsable Connections"):
        parse_spec(_spec_text().replace("D_bin>s_bin", "D_bin s_bin"))
    with pytest.raises(GNNSpecError, match="no matrices"):
        parse_spec(_replace_block(_spec_text(), "InitialParameterization", "# none\n"))
    with pytest.raises(GNNSpecError, match="unparsable InitialParameterization"):
        parse_spec(_spec_text().replace("C_level={-1.0,2.0,-1.0}", "C_level ~ -1.0"))
    with pytest.raises(GNNSpecError, match="unterminated"):
        parse_spec(_spec_text().replace("C_level={-1.0,2.0,-1.0}", "C_level={-1.0,2.0,-1.0"))
    with pytest.raises(GNNSpecError, match="duplicate InitialParameterization"):
        parse_spec(
            _spec_text().replace(
                "C_level={-1.0,2.0,-1.0}", "C_level={-1.0,2.0,-1.0}\nD_bin={0.2,0.3,0.5}"
            )
        )
    with pytest.raises(GNNSpecError, match="unparsable ModelParameters"):
        parse_spec(_spec_text().replace("num_actions: 3", "num_actions"))
    with pytest.raises(GNNSpecError, match="no parameters"):
        parse_spec(_replace_block(_spec_text(), "ModelParameters", "# none\n"))


def test_spec_accessors_report_missing_declarations() -> None:
    spec = load_spec()
    with pytest.raises(GNNSpecError, match="not declared in StateSpaceBlock"):
        spec.shape("s_absent")
    with pytest.raises(GNNSpecError, match="not declared"):
        spec.text_parameter("absent")
    with pytest.raises(GNNSpecError, match="must be an integer"):
        spec.integer_parameter("observation_bins_rule")
    with pytest.raises(GNNSpecError, match="not declared in InitialParameterization"):
        declared_matrix(spec, "E_absent")
    with pytest.raises(GNNSpecError, match="not a valid numeric literal"):
        declared_matrix(
            parse_spec(_spec_text().replace("C_level={-1.0,2.0,-1.0}", "C_level={x}")), "C_level"
        )
    with pytest.raises(GNNSpecError, match="not numeric"):
        declared_matrix(
            parse_spec(_spec_text().replace("C_level={-1.0,2.0,-1.0}", "C_level={'a','b','c'}")),
            "C_level",
        )
