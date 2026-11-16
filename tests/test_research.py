from __future__ import annotations

import hashlib
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

from biofirm.research import (
    PerplexityClient,
    ResearchError,
    ResearchFinding,
    ResearchRequest,
    ResearchResponse,
    ResearchService,
    _parse_response,
    build_prompt,
    estimate_cost,
    load_regions,
    parse_findings,
    set_review_status,
    stable_region_id,
)


class ProviderHandler(BaseHTTPRequestHandler):
    calls = 0
    failure_count = 0
    mode = "success"
    delay = 0.0

    def do_POST(self) -> None:  # noqa: N802
        ProviderHandler.calls += 1
        if ProviderHandler.delay:
            time.sleep(ProviderHandler.delay)
        if ProviderHandler.mode == "auth":
            self.send_response(401)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if ProviderHandler.mode == "malformed":
            body = b"{not-json"
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if ProviderHandler.mode == "schema":
            body = b'{"choices": []}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if ProviderHandler.calls <= ProviderHandler.failure_count:
            self.send_response(500)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        size = int(self.headers["Content-Length"])
        payload = json.loads(self.rfile.read(size))
        assert payload["messages"][0]["role"] == "user"
        body = json.dumps(
            {
                "id": "request-1",
                "model": payload["model"],
                "choices": [{"message": {"content": "A cited result."}}],
                "citations": ["https://example.test/source"],
                "usage": {"total_tokens": 12},
            }
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        del format, args


@pytest.fixture
def server():  # type: ignore[no-untyped-def]
    ProviderHandler.calls = 0
    ProviderHandler.failure_count = 1
    ProviderHandler.mode = "success"
    ProviderHandler.delay = 0.0
    server = ThreadingHTTPServer(("127.0.0.1", 0), ProviderHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        thread.join(timeout=3)


def test_research_client_retries_and_resumes(tmp_path, server, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("PERPLEXITY_API_KEY", "test-secret")
    client = PerplexityClient(
        live=True,
        base_url=f"http://127.0.0.1:{server.server_port}",
        backoff=0.0,
        allow_custom_endpoint=True,
        allow_insecure_transport=True,
    )
    response = client.complete(ResearchRequest("r1", "Region", "ecologist", "Describe Region"))
    assert response.citations == ("https://example.test/source",)
    service = ResearchService(client)
    regions = [{"_id": "R1", "name": "Region", "description": "water"}]
    paths = service.run(regions, ["ecologist"], output_dir=tmp_path, live=True)
    assert paths[0].exists()
    assert (tmp_path / "manifest.json").exists()
    calls = ProviderHandler.calls
    service.run(regions, ["ecologist"], output_dir=tmp_path, live=True)
    assert ProviderHandler.calls == calls


def test_research_prompt_and_endpoint_policy(monkeypatch) -> None:
    monkeypatch.setenv("PERPLEXITY_API_KEY", "test-secret")
    prompt = build_prompt({"_id": "r1", "name": "Region"}, "ecologist")
    assert prompt.count("<bioregion>") == 1
    assert prompt.count("</bioregion>") == 1
    with pytest.raises(ResearchError, match="custom research endpoints"):
        PerplexityClient(live=True, base_url="https://example.test")
    with pytest.raises(ResearchError, match="HTTPS"):
        PerplexityClient(
            live=True,
            base_url="http://127.0.0.1:1",
            allow_custom_endpoint=True,
        )


def test_research_resume_rejects_tampered_markdown(tmp_path, server, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("PERPLEXITY_API_KEY", "test-secret")
    client = PerplexityClient(
        live=True,
        base_url=f"http://127.0.0.1:{server.server_port}",
        backoff=0,
        allow_custom_endpoint=True,
        allow_insecure_transport=True,
    )
    service = ResearchService(client)
    regions = [{"_id": "R1", "name": "Region", "description": "water"}]
    service.run(regions, ["ecologist"], output_dir=tmp_path, live=True)
    calls = ProviderHandler.calls
    markdown = next(tmp_path.glob("r1/*.md"))
    markdown.write_text("tampered\n", encoding="utf-8")
    service.run(regions, ["ecologist"], output_dir=tmp_path, live=True)
    assert ProviderHandler.calls == calls + 1


def test_research_requires_key_and_live(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("PERPLEXITY_API_KEY", raising=False)
    with pytest.raises(ResearchError, match="live"):
        PerplexityClient(live=False)
    with pytest.raises(ResearchError, match="PERPLEXITY_API_KEY"):
        PerplexityClient(live=True)


def test_research_request_parameters_are_strict() -> None:
    with pytest.raises(ResearchError, match="temperature"):
        ResearchRequest("r1", "Region", "ecologist", "prompt", temperature=3)
    with pytest.raises(ResearchError, match="max_tokens"):
        ResearchRequest("r1", "Region", "ecologist", "prompt", max_tokens=0)
    with pytest.raises(ResearchError, match="prompt"):
        ResearchRequest("r1", "Region", "ecologist", " ")
    with pytest.raises(ResearchError, match="prompt_version"):
        ResearchRequest("r1", "Region", "ecologist", "prompt", prompt_version=" ")


def test_research_rejects_malformed_and_invalid_schema(tmp_path, server, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("PERPLEXITY_API_KEY", "secret-value-that-must-not-leak")
    client = PerplexityClient(
        live=True,
        base_url=f"http://127.0.0.1:{server.server_port}",
        allow_custom_endpoint=True,
        allow_insecure_transport=True,
    )
    request = ResearchRequest("r1", "Region", "ecologist", "Describe Region")
    ProviderHandler.mode = "malformed"
    with pytest.raises(ResearchError, match="malformed JSON"):
        client.complete(request)
    ProviderHandler.mode = "schema"
    with pytest.raises(ResearchError, match="no choices"):
        client.complete(request)


def test_research_authentication_fails_without_retry(server, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("PERPLEXITY_API_KEY", "secret-value-that-must-not-leak")
    ProviderHandler.mode = "auth"
    client = PerplexityClient(
        live=True,
        base_url=f"http://127.0.0.1:{server.server_port}",
        retries=3,
        backoff=0,
        allow_custom_endpoint=True,
        allow_insecure_transport=True,
    )
    with pytest.raises(ResearchError, match="authentication"):
        client.complete(ResearchRequest("r1", "Region", "ecologist", "Describe Region"))
    assert ProviderHandler.calls == 1


def test_research_timeout_and_retry_exhaustion_are_explicit(server, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("PERPLEXITY_API_KEY", "secret-value-that-must-not-leak")
    ProviderHandler.delay = 0.05
    client = PerplexityClient(
        live=True,
        base_url=f"http://127.0.0.1:{server.server_port}",
        timeout=0.001,
        retries=1,
        backoff=0,
        allow_custom_endpoint=True,
        allow_insecure_transport=True,
    )
    with pytest.raises(ResearchError, match="failed after 2 attempts"):
        client.complete(ResearchRequest("r1", "Region", "ecologist", "Describe Region"))
    ProviderHandler.delay = 0
    ProviderHandler.failure_count = 10
    client = PerplexityClient(
        live=True,
        base_url=f"http://127.0.0.1:{server.server_port}",
        retries=2,
        backoff=0,
        allow_custom_endpoint=True,
        allow_insecure_transport=True,
    )
    with pytest.raises(ResearchError, match="HTTP 500"):
        client.complete(ResearchRequest("r1", "Region", "ecologist", "Describe Region"))
    assert ProviderHandler.calls == 5


def test_research_artifacts_include_hashes_and_no_secret(tmp_path, server, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    api_key_value = "secret-value-that-must-not-leak"
    monkeypatch.setenv("PERPLEXITY_API_KEY", api_key_value)
    client = PerplexityClient(
        live=True,
        base_url=f"http://127.0.0.1:{server.server_port}",
        backoff=0,
        allow_custom_endpoint=True,
        allow_insecure_transport=True,
    )
    paths = ResearchService(client).run(
        [{"_id": "R1", "name": "Region", "content": "water"}],
        ["ecologist"],
        output_dir=tmp_path,
        live=True,
    )
    payload = paths[0].read_text(encoding="utf-8")
    assert "prompt_hash" in payload
    assert "configuration_hash" in payload
    assert "source_hash" in payload
    assert api_key_value not in payload


def test_research_rejects_colliding_region_or_persona_artifacts(
    tmp_path, server, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("PERPLEXITY_API_KEY", "test-secret")
    client = PerplexityClient(
        live=True,
        base_url=f"http://127.0.0.1:{server.server_port}",
        allow_custom_endpoint=True,
        allow_insecure_transport=True,
    )
    service = ResearchService(client)
    with pytest.raises(ResearchError, match="region identifiers"):
        service.run(
            [{"_id": "same"}, {"_id": "same"}],
            ["ecologist"],
            output_dir=tmp_path,
            live=True,
        )
    with pytest.raises(ResearchError, match="artifact identifiers"):
        service.run(
            [{"_id": "region"}],
            ["ecologist", "ecologist!"],
            output_dir=tmp_path,
            live=True,
        )


def test_retained_oneearth_source_flattens_to_unique_stable_ids() -> None:
    regions = load_regions("One_Earth/oneearth_bioregion_ecoregions.json")
    ids = [stable_region_id(region) for region in regions]
    assert len(regions) >= 100
    assert len(ids) == len(set(ids))
    assert all(ids)


def test_research_parsers_reject_invalid_sources_and_responses(tmp_path) -> None:  # type: ignore[no-untyped-def]
    invalid = tmp_path / "invalid.json"
    invalid.write_text("42", encoding="utf-8")
    with pytest.raises(ResearchError, match="object or list"):
        load_regions(invalid)
    valid = {
        "choices": [{"message": {"content": "ok"}}],
        "citations": ["not-a-url"],
        "usage": {"total_tokens": 1},
    }
    with pytest.raises(ResearchError, match="HTTP"):
        _parse_response(valid, "sonar")
    invalid_usage = {
        "choices": [{"message": {"content": "ok"}}],
        "usage": {"total_tokens": -1},
    }
    with pytest.raises(ResearchError, match="usage values"):
        _parse_response(invalid_usage, "sonar")
    with pytest.raises(ResearchError, match="no textual"):
        _parse_response({"choices": [{"message": {"content": ""}}]}, "sonar")


def test_research_client_rejects_invalid_transport_configuration(monkeypatch) -> None:
    monkeypatch.setenv("PERPLEXITY_API_KEY", "test-secret")
    with pytest.raises(ResearchError, match="absolute"):
        PerplexityClient(live=True, base_url="not-a-url")
    with pytest.raises(ResearchError, match="retry delays"):
        PerplexityClient(live=True, max_backoff=-1)


def test_research_service_rejects_invalid_requests(tmp_path, server, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("PERPLEXITY_API_KEY", "test-secret")
    client = PerplexityClient(
        live=True,
        base_url=f"http://127.0.0.1:{server.server_port}",
        allow_custom_endpoint=True,
        allow_insecure_transport=True,
    )
    service = ResearchService(client)
    with pytest.raises(ResearchError, match="at least one"):
        service.run([], ["ecologist"], output_dir=tmp_path, live=True)
    with pytest.raises(ResearchError, match="unique"):
        service.run([{"_id": "r"}], ["ecologist", "ecologist"], output_dir=tmp_path, live=True)
    with pytest.raises(ResearchError, match="temperature"):
        service.run([{"_id": "r"}], ["ecologist"], output_dir=tmp_path, live=True, temperature=3)


def test_findings_are_verbatim_with_hedge_confidence() -> None:
    findings = parse_findings(
        "Wetlands store carbon. Their area may be declining.", ("https://example.test/s",)
    )
    assert isinstance(findings, tuple)
    assert isinstance(findings[0], ResearchFinding)
    assert findings[0].claim == "Wetlands store carbon."
    assert findings[0].confidence == 1.0
    assert findings[1].confidence == 0.7
    with pytest.raises(ResearchError, match="non-empty"):
        parse_findings("", ())


def test_cost_estimate_uses_documented_rates() -> None:
    assert estimate_cost({"prompt_tokens": 1_000_000, "completion_tokens": 1_000_000}) == 3.0
    assert estimate_cost({"prompt_tokens": 0, "completion_tokens": 0}) == 0.0
    with pytest.raises(ResearchError, match="finite"):
        estimate_cost({"prompt_tokens": -1, "completion_tokens": 0})


def test_research_stages_are_independently_rerunnable(tmp_path, server, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("PERPLEXITY_API_KEY", "test-secret")
    client = PerplexityClient(
        live=True,
        base_url=f"http://127.0.0.1:{server.server_port}",
        backoff=0,
        allow_custom_endpoint=True,
        allow_insecure_transport=True,
    )
    service = ResearchService(client)
    regions = [{"_id": "R1", "name": "Region", "description": "water"}]
    jobs, manifest_entries = service.prepare(regions, ["ecologist"], output_dir=tmp_path, live=True)
    assert isinstance(manifest_entries, dict)
    job = jobs[0]
    response = service.execute(job.request)
    document = service.build_document(job, response)
    findings = service.parse(document)
    rendered = service.render(document)
    assert findings
    assert "Prompt hash:" in rendered
    assert document["review"]["status"] == "unreviewed"
    assert document["cost"]["usd_estimate"] >= 0.0


def test_manifest_records_cost_total_findings_and_review(tmp_path, server, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("PERPLEXITY_API_KEY", "test-secret")
    client = PerplexityClient(
        live=True,
        base_url=f"http://127.0.0.1:{server.server_port}",
        backoff=0,
        allow_custom_endpoint=True,
        allow_insecure_transport=True,
    )
    service = ResearchService(client)
    paths = service.run(
        [{"_id": "R1", "name": "Region", "content": "water"}],
        ["ecologist"],
        output_dir=tmp_path,
        live=True,
    )
    document = json.loads(paths[0].read_text(encoding="utf-8"))
    assert document["findings"]
    assert document["review"]["status"] == "unreviewed"
    assert "usd_estimate" in document["cost"]
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert "cost_usd_total" in manifest
    assert manifest["cost_usd_total"] >= 0.0
    approved = set_review_status(
        document, "approved", reviewer="dr-friedman", reviewed_at="2026-01-01T00:00:00Z"
    )
    assert approved["review"] == {
        "status": "approved",
        "reviewed_at": "2026-01-01T00:00:00Z",
        "reviewer": "dr-friedman",
    }
    with pytest.raises(ResearchError, match="review status"):
        set_review_status(document, "unknown")


@pytest.mark.parametrize("failure_stage", ["provider", "render"])
def test_interrupted_research_preserves_committed_pairs_on_resume(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure_stage: str
) -> None:
    class InterruptingProvider:
        def __init__(self) -> None:
            self.calls: list[str] = []
            self.resuming = False

        def complete(self, request: ResearchRequest) -> ResearchResponse:
            self.calls.append(request.region_id)
            if failure_stage == "provider" and request.region_id == "r2" and not self.resuming:
                raise ResearchError("interrupted second job")
            return ResearchResponse(
                content=f"Response {len(self.calls)} for {request.region_id}.",
                citations=("https://example.test/source",),
                model=request.model,
                usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
                provider_request_id=f"request-{len(self.calls)}",
            )

    provider = InterruptingProvider()
    service = ResearchService(provider)
    original_render = service.render

    def render(document: dict[str, Any]) -> str:
        if (
            failure_stage == "render"
            and document["request"]["region_id"] == "r2"
            and not provider.resuming
        ):
            raise ResearchError("interrupted second job")
        return original_render(document)

    monkeypatch.setattr(service, "render", render)
    regions = [{"_id": "r1", "name": "First"}, {"_id": "r2", "name": "Second"}]
    with pytest.raises(ResearchError, match="interrupted second job"):
        service.run(regions, ["ecologist"], output_dir=tmp_path, live=True)

    first_json = tmp_path / "r1" / "ecologist.json"
    first_markdown = first_json.with_suffix(".md")
    completed_pair = (first_json.read_bytes(), first_markdown.read_bytes())
    manifest_path = tmp_path / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert [entry["json"] for entry in manifest["entries"]] == ["r1/ecologist.json"]
    first_entry = manifest["entries"][0]
    assert first_entry["json_sha256"] == hashlib.sha256(completed_pair[0]).hexdigest()
    assert first_entry["markdown_sha256"] == hashlib.sha256(completed_pair[1]).hexdigest()
    one_job_cost = estimate_cost({"prompt_tokens": 100, "completion_tokens": 50})
    assert manifest["cost_usd_total"] == pytest.approx(one_job_cost)
    second_json = tmp_path / "r2" / "ecologist.json"
    assert second_json.exists() == (failure_stage == "render")
    assert not second_json.with_suffix(".md").exists()

    provider.resuming = True
    written = ResearchService(provider).run(regions, ["ecologist"], output_dir=tmp_path, live=True)
    assert written == [second_json]
    assert provider.calls == ["r1", "r2", "r2"]
    assert (first_json.read_bytes(), first_markdown.read_bytes()) == completed_pair
    resumed = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert [entry["json"] for entry in resumed["entries"]] == [
        "r1/ecologist.json",
        "r2/ecologist.json",
    ]
    assert resumed["entries"][0] == first_entry
    assert resumed["cost_usd_total"] == pytest.approx(2.0 * one_job_cost)
