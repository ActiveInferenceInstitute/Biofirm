"""Experimental regional-interaction graph data model with provenance.

This module defines the *data model and evaluation contract* for regional
graph/network work. It is intentionally experimental: every analytic output is
labelled as descriptive, not as validated ecological evidence. No graph is
allowed to carry calibrated scientific claims until an authoritative
source-of-truth dataset, per-edge provenance, and an acceptance protocol exist.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .data_validation import DataValidationError


@dataclass(frozen=True)
class RegionalNode:
    """One regional entity in an experimental interaction graph."""

    node_id: str
    name: str
    provenance: str
    sources: tuple[str, ...]


@dataclass(frozen=True)
class RegionalEdge:
    """One directed, provenance-bearing candidate interaction between nodes."""

    source: str
    target: str
    weight: float
    kind: str
    uncertainty: float
    provenance: str
    calibrated: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.source, str) or not self.source.strip():
            raise DataValidationError("edge source must be a non-empty node id")
        if not isinstance(self.target, str) or not self.target.strip():
            raise DataValidationError("edge target must be a non-empty node id")
        if isinstance(self.weight, bool) or not isinstance(self.weight, (int, float)):
            raise DataValidationError("edge weight must be numeric")
        if not math.isfinite(float(self.weight)):
            raise DataValidationError("edge weight must be finite")
        if (
            isinstance(self.uncertainty, bool)
            or not isinstance(self.uncertainty, (int, float))
            or not 0 <= self.uncertainty <= 1
        ):
            raise DataValidationError("edge uncertainty must be in [0, 1]")
        if not isinstance(self.kind, str) or not self.kind.strip():
            raise DataValidationError("edge kind must be a non-empty string")
        if not isinstance(self.provenance, str) or not self.provenance.strip():
            raise DataValidationError("edge provenance must be a non-empty string")
        if not isinstance(self.calibrated, bool):
            raise DataValidationError("edge calibrated must be boolean")


@dataclass(frozen=True)
class RegionalGraph:
    """An experimental, provenance-bound regional interaction graph."""

    label: str
    nodes: Mapping[str, RegionalNode]
    edges: tuple[RegionalEdge, ...]
    experimental: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.label, str) or not self.label.strip():
            raise DataValidationError("graph label must be a non-empty string")
        if not isinstance(self.nodes, Mapping):
            raise DataValidationError("graph nodes must be a mapping")
        if not isinstance(self.experimental, bool):
            raise DataValidationError("graph experimental must be boolean")
        for node_id, node in self.nodes.items():
            if not isinstance(node, RegionalNode) or node.node_id != node_id:
                raise DataValidationError(f"graph node {node_id!r} is invalid")
        validation_errors = validate_graph(self)
        if validation_errors:
            raise DataValidationError("graph failed validation: " + "; ".join(validation_errors))


def validate_graph(graph: RegionalGraph) -> list[str]:
    """Return a list of validation problems (empty when the graph is valid)."""
    problems: list[str] = []
    for edge in graph.edges:
        if edge.source not in graph.nodes:
            problems.append(f"edge references unknown source node {edge.source!r}")
        if edge.target not in graph.nodes:
            problems.append(f"edge references unknown target node {edge.target!r}")
        if edge.source == edge.target:
            problems.append(f"edge {edge.source!r} is a self-loop")
    return problems


def nodes_from_regions_entries(entries: list[RegionalNode]) -> dict[str, RegionalNode]:
    """Index regional nodes by id, rejecting duplicate ids."""
    result: dict[str, RegionalNode] = {}
    for node in entries:
        if node.node_id in result:
            raise DataValidationError(f"duplicate regional node id {node.node_id!r}")
        result[node.node_id] = node
    return result


def nodes_from_json(path: str | Path, label: str = "regional-source") -> list[RegionalNode]:
    """Build regional nodes from a region JSON source (provenance-preserving)."""
    source_path = Path(path)
    raw = json.loads(source_path.read_text(encoding="utf-8"))
    provenance = str(source_path)
    nodes: list[RegionalNode] = []
    if isinstance(raw, Mapping):
        for key, value in raw.items():
            if isinstance(value, Mapping):
                nodes.append(
                    RegionalNode(str(key), str(value.get("name", key)), provenance, (provenance,))
                )
            else:
                nodes.append(RegionalNode(str(key), str(key), provenance, (provenance,)))
    elif isinstance(raw, list):
        for item in raw:
            nodes.extend(_flatten_graph_nodes(item, provenance, label))
    else:
        raise DataValidationError(f"{label} region source must be an object or list")
    if not nodes:
        raise DataValidationError(f"{label} region source produced no nodes")
    return nodes


def _flatten_graph_nodes(node: Any, provenance: str, label: str) -> list[RegionalNode]:
    """Recursively collect identified leaf regions from a hierarchical source."""
    if not isinstance(node, Mapping):
        raise DataValidationError(f"{label} region source hierarchy contains a non-object node")
    children = node.get("children")
    if isinstance(children, list) and children:
        flattened: list[RegionalNode] = []
        for child in children:
            flattened.extend(_flatten_graph_nodes(child, provenance, label))
        return flattened
    if node.get("_id") or node.get("id"):
        node_id = str(node.get("_id") or node.get("id"))
        return [RegionalNode(node_id, str(node.get("name", node_id)), provenance, (provenance,))]
    raise DataValidationError(f"{label} region source must contain identified regions")


def empty_regional_graph(label: str, nodes: list[RegionalNode]) -> RegionalGraph:
    """Build an experimental graph with nodes and no edges."""
    return RegionalGraph(label, nodes_from_regions_entries(nodes), ())


def with_candidate_edge(
    graph: RegionalGraph,
    *,
    source: str,
    target: str,
    weight: float,
    kind: str,
    uncertainty: float,
    provenance: str,
    calibrated: bool = False,
) -> RegionalGraph:
    """Return a copy of the graph with one provenance-bearing candidate edge."""
    edge = RegionalEdge(source, target, weight, kind, uncertainty, provenance, calibrated)
    return RegionalGraph(graph.label, graph.nodes, (*graph.edges, edge))


def descriptive_summary(graph: RegionalGraph) -> dict[str, Any]:
    """Return a descriptive-only summary (never a validated ecological claim)."""
    node_ids = list(graph.nodes)
    out_degree = {node_id: 0 for node_id in node_ids}
    for edge in graph.edges:
        out_degree[edge.source] = out_degree.get(edge.source, 0) + 1
    undirected_pairs: set[tuple[str, str]] = set()
    for edge in graph.edges:
        undirected_pairs.add((edge.source, edge.target))
        undirected_pairs.add((edge.target, edge.source))
    return {
        "label": graph.label,
        "experimental": True,
        "node_count": len(node_ids),
        "edge_count": len(graph.edges),
        "average_out_degree": (
            float(sum(out_degree.values())) / len(node_ids) if node_ids else 0.0
        ),
        "unique_undirected_pairs": len(undirected_pairs),
        "notes": [
            "descriptive topology only",
            "not validated ecological evidence",
            "no calibrated ecological relationship is implied",
        ],
    }


def acceptance_report(
    graph: RegionalGraph, *, min_nodes: int = 1, min_edges: int = 0
) -> dict[str, Any]:
    """Check whether a graph meets explicit evaluation thresholds.

    This is a protocol check, not a scientific validation. It only verifies that
    the graph has enough provenance-bound structure to be worth evaluating.
    """
    if isinstance(min_nodes, bool) or not isinstance(min_nodes, int) or min_nodes < 0:
        raise DataValidationError("min_nodes must be a non-negative integer")
    if isinstance(min_edges, bool) or not isinstance(min_edges, int) or min_edges < 0:
        raise DataValidationError("min_edges must be a non-negative integer")
    node_ok = len(graph.nodes) >= min_nodes
    edge_ok = len(graph.edges) >= min_edges
    missing = []
    if not node_ok:
        missing.append(f"need at least {min_nodes} nodes")
    if not edge_ok:
        missing.append(f"need at least {min_edges} edges")
    return {
        "label": graph.label,
        "passed": node_ok and edge_ok,
        "node_count_meets": node_ok,
        "edge_count_meets": edge_ok,
        "missing": missing,
        "warnings": ["components present without calibrated ecological validation"],
    }
