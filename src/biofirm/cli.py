"""Command-line entry points for reproducible Biofirm workflows."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .analysis import summarize_records
from .business import BusinessCommittee, load_committee
from .config import ConfigError, load_config
from .io import atomic_write_json
from .research import PerplexityClient, ResearchService, load_regions
from .simulation import parameter_sweep, simulate, validate_result_document, write_result
from .text import BioregionTextProcessor, extract_text
from .visualization import visualize_documents


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="biofirm", description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="validate a typed ecosystem configuration")
    validate.add_argument("--config", type=Path)

    simulation = subparsers.add_parser("simulate", help="run a seeded ecological simulation")
    _config_argument(simulation)
    simulation.add_argument("--steps", type=int, default=20)
    simulation.add_argument("--seed", type=int)
    simulation.add_argument(
        "--controller", choices=["active-inference", "slide-rule", "random", "business"]
    )
    simulation.add_argument("--output", type=Path)

    sweep = subparsers.add_parser("sweep", help="run independent seeded simulations")
    _config_argument(sweep)
    sweep.add_argument("--steps", type=int, default=20)
    sweep.add_argument("--seeds", type=int, nargs="+", default=[7, 8, 9])
    sweep.add_argument(
        "--controller", choices=["active-inference", "slide-rule", "random", "business"]
    )
    sweep.add_argument("--output", type=Path)

    analyze = subparsers.add_parser("analyze", help="summarize a simulation JSON artifact")
    analyze.add_argument("--input", type=Path, required=True)
    analyze.add_argument("--output", type=Path)

    visualize = subparsers.add_parser("visualize", help="create a deterministic document plot")
    visualize.add_argument("--input", type=Path, required=True)
    visualize.add_argument("--output", type=Path, required=True)
    visualize.add_argument("--seed", type=int, default=7)

    research = subparsers.add_parser(
        "research", help="run explicitly enabled live bioregion research"
    )
    research.add_argument(
        "--live", action="store_true", help="required acknowledgement for network access"
    )
    research.add_argument("--source", type=Path, required=True)
    research.add_argument("--persona", action="append", dest="personas", required=True)
    research.add_argument("--output", type=Path, required=True)
    research.add_argument("--model", default="sonar")
    research.add_argument("--base-url", default="https://api.perplexity.ai")
    research.add_argument("--timeout", type=float, default=30.0)
    research.add_argument("--retries", type=int, default=3)
    research.add_argument("--backoff", type=float, default=0.5)
    research.add_argument("--temperature", type=float, default=0.2)
    research.add_argument("--max-tokens", type=int, default=1500)

    parse = subparsers.add_parser(
        "parse-description", help="extract deterministic evidence from bioregion text"
    )
    _config_argument(parse)
    parse.add_argument("--input", type=Path, required=True, help="UTF-8 text or PDF path")
    parse.add_argument("--output", type=Path)

    business = subparsers.add_parser(
        "business-evaluate", help="evaluate a committee policy against state"
    )
    _config_argument(business)
    business.add_argument("--state", type=Path, required=True)
    business.add_argument("--committee", type=Path)
    business.add_argument("--output", type=Path)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = _dispatch(args)
    except (ConfigError, ValueError, RuntimeError, OSError, json.JSONDecodeError) as exc:
        print(f"biofirm: error: {exc}", file=sys.stderr)
        return 2
    if result is not None:
        print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


def _dispatch(args: argparse.Namespace) -> Any:
    if args.command == "validate":
        config = load_config(args.config)
        return {
            "valid": True,
            "name": config.name,
            "variables": list(config.variables),
            "seed": config.seed,
        }
    if args.command == "simulate":
        config = load_config(args.config)
        result = simulate(config, args.steps, args.seed, controller_name=args.controller)
        output = args.output
        if output is None and config.output.write_by_default:
            output = Path(config.output.directory) / f"{_safe_filename(config.name)}.json"
        if output is not None:
            write_result(result, output)
        return result.to_dict()
    if args.command == "sweep":
        config = load_config(args.config)
        rows = parameter_sweep(config, args.steps, args.seeds, args.controller)
        output = args.output
        if output is None and config.output.write_by_default:
            output = Path(config.output.directory) / f"{_safe_filename(config.name)}_sweep.json"
        if output is not None:
            atomic_write_json(output, rows)
        return {"rows": rows}
    if args.command == "analyze":
        document = validate_result_document(json.loads(args.input.read_text(encoding="utf-8")))
        summary = summarize_records(document.get("records", []))
        if args.output:
            atomic_write_json(args.output, summary)
        return summary
    if args.command == "visualize":
        document = validate_result_document(json.loads(args.input.read_text(encoding="utf-8")))
        records = document.get("records", [])
        texts = [json.dumps(record.get("values", {}), sort_keys=True) for record in records]
        labels = [f"step-{record.get('timestep', index)}" for index, record in enumerate(records)]
        path = visualize_documents(texts, labels, args.output, seed=args.seed)
        return {"output": str(path), "bytes": path.stat().st_size}
    if args.command == "research":
        client = PerplexityClient(
            live=args.live,
            base_url=args.base_url,
            timeout=args.timeout,
            retries=args.retries,
            backoff=args.backoff,
        )
        service = ResearchService(client)
        paths = service.run(
            load_regions(args.source),
            args.personas,
            output_dir=args.output,
            live=args.live,
            model=args.model,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
        )
        return {"written": [str(path) for path in paths]}
    if args.command == "parse-description":
        config = load_config(args.config)
        processor = BioregionTextProcessor(config)
        profile = processor.process(extract_text(args.input))
        if args.output:
            atomic_write_json(args.output, profile.to_dict())
        return profile.to_dict()
    if args.command == "business-evaluate":
        config = load_config(args.config)
        committee = load_committee(args.committee, config) if args.committee else None
        decision = BusinessCommittee(config, committee).evaluate(_load_state(args.state))
        business_result = {
            "action": decision.action,
            "score": decision.score,
            "cost": decision.cost,
            "risk": decision.risk,
            "votes": dict(decision.votes),
            "rationale": list(decision.rationale),
        }
        if args.output:
            atomic_write_json(args.output, business_result)
        return business_result
    raise AssertionError(f"unhandled command {args.command}")


def _config_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--config", type=Path, help="JSON configuration (packaged default when omitted)"
    )


def _load_state(path: Path) -> dict[str, float]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("state must be a JSON object")
    values: dict[str, float] = {}
    for key, value in raw.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"state value {key!r} must be numeric")
        numeric = float(value)
        if not math.isfinite(numeric):
            raise ValueError(f"state value {key!r} must be finite")
        values[str(key)] = numeric
    return values


def _safe_filename(value: str) -> str:
    return "".join(
        character if character.isalnum() or character in "-_" else "_" for character in value
    )
