from __future__ import annotations

import json

import pytest

from biofirm.data_validation import DataValidationError
from biofirm.graph import (
    RegionalEdge,
    RegionalGraph,
    RegionalNode,
    acceptance_report,
    descriptive_summary,
    empty_regional_graph,
    nodes_from_json,
    validate_graph,
    with_candidate_edge,
)


def _nodes() -> list[RegionalNode]:
    return [
        RegionalNode("ME-AND", "Androscoggin", "test-source", ("test-source",)),
        RegionalNode("ME-ARO", "Aroostook", "test-source", ("test-source",)),
        RegionalNode("NH-BEL", "Belknap", "test-source", ("test-source",)),
    ]


def _graph() -> RegionalGraph:
    graph = empty_regional_graph("test-graph", _nodes())
    return with_candidate_edge(
        graph,
        source="ME-AND",
        target="ME-ARO",
        weight=0.5,
        kind="candidate-relationship",
        uncertainty=0.8,
        provenance="test-source",
    )


def test_graph_validation_rejects_bad_edges() -> None:
    graph = _graph()
    assert graph.experimental is True
    assert validate_graph(graph) == []
    with pytest.raises(DataValidationError, match="unknown source"):
        with_candidate_edge(
            graph,
            source="NOPE",
            target="ME-AND",
            weight=1.0,
            kind="k",
            uncertainty=0.1,
            provenance="p",
        )
    with pytest.raises(DataValidationError, match="self-loop"):
        with_candidate_edge(
            graph,
            source="ME-AND",
            target="ME-AND",
            weight=1.0,
            kind="k",
            uncertainty=0.1,
            provenance="p",
        )


def test_edge_field_validation_is_strict() -> None:
    with pytest.raises(DataValidationError, match="uncertainty"):
        RegionalEdge("a", "b", 1.0, "k", 2.0, "p")
    with pytest.raises(DataValidationError, match="uncertainty"):
        RegionalEdge("a", "b", 1.0, "k", -0.1, "p")
    with pytest.raises(DataValidationError, match="finite"):
        RegionalEdge("a", "b", float("nan"), "k", 0.1, "p")
    with pytest.raises(DataValidationError, match="provenance"):
        RegionalEdge("a", "b", 1.0, "k", 0.1, "")


def test_descriptive_summary_is_experimental_only() -> None:
    summary = descriptive_summary(_graph())
    assert summary["experimental"] is True
    assert summary["node_count"] == 3
    assert summary["edge_count"] == 1
    assert summary["average_out_degree"] == pytest.approx(1 / 3)
    assert any("not validated ecological evidence" in note for note in summary["notes"])


def test_acceptance_report_enforces_thresholds() -> None:
    report = acceptance_report(_graph(), min_nodes=3, min_edges=1)
    assert report["passed"] is True
    assert report["missing"] == []
    failing = acceptance_report(_graph(), min_nodes=10, min_edges=1)
    assert failing["passed"] is False
    assert any("nodes" in item for item in failing["missing"])


def test_nodes_from_json_accepts_map_and_list_sources(tmp_path) -> None:  # type: ignore[no-untyped-def]
    mapping = tmp_path / "map.json"
    mapping.write_text(json.dumps({"A": {"name": "Alpha"}}), encoding="utf-8")
    nodes = nodes_from_json(mapping, "map")
    assert nodes[0].node_id == "A"
    listing = tmp_path / "list.json"
    listing.write_text(json.dumps([{"_id": "B", "name": "Beta"}]), encoding="utf-8")
    assert nodes_from_json(listing, "list")[0].node_id == "B"

    bad = tmp_path / "bad-list.json"
    bad.write_text(json.dumps([{"name": "no id"}]), encoding="utf-8")
    with pytest.raises(DataValidationError, match="identified"):
        nodes_from_json(bad, "bad")
    bad_map = tmp_path / "bad-map.json"
    bad_map.write_text("42", encoding="utf-8")
    with pytest.raises(DataValidationError, match="object or list"):
        nodes_from_json(bad_map, "bad-map")


def test_real_region_sources_build_graphs() -> None:
    from pathlib import Path

    root = Path(__file__).parents[1]
    nodes = nodes_from_json(root / "Bio_Perplexity" / "Biofirm_Regions.json", "regions")
    assert len(nodes) == 67
    graph = empty_regional_graph("regions", nodes)
    assert graph.experimental is True
    assert descriptive_summary(graph)["node_count"] == 67
    one_earth_nodes = nodes_from_json(
        root / "One_Earth" / "oneearth_bioregion_ecoregions.json", "one-earth"
    )
    assert len(one_earth_nodes) >= 100
