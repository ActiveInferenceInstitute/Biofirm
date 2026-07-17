from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from biofirm.research import (
    PerplexityClient,
    ResearchError,
    ResearchRequest,
    ResearchService,
    load_regions,
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
        live=True, base_url=f"http://127.0.0.1:{server.server_port}", backoff=0.0
    )
    response = client.complete(ResearchRequest("r1", "Region", "ecologist", "Describe Region"))
    assert response.citations == ("https://example.test/source",)
    service = ResearchService(client)
    regions = [{"_id": "R1", "name": "Region", "description": "water"}]
    paths = service.run(regions, ["ecologist"], output_dir=tmp_path, live=True)
    assert paths[0].exists()
    calls = ProviderHandler.calls
    service.run(regions, ["ecologist"], output_dir=tmp_path, live=True)
    assert ProviderHandler.calls == calls


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


def test_research_rejects_malformed_and_invalid_schema(tmp_path, server, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("PERPLEXITY_API_KEY", "secret-value-that-must-not-leak")
    client = PerplexityClient(live=True, base_url=f"http://127.0.0.1:{server.server_port}")
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
        live=True, base_url=f"http://127.0.0.1:{server.server_port}", retries=3, backoff=0
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
    )
    with pytest.raises(ResearchError, match="failed after 2 attempts"):
        client.complete(ResearchRequest("r1", "Region", "ecologist", "Describe Region"))
    ProviderHandler.delay = 0
    ProviderHandler.failure_count = 10
    client = PerplexityClient(
        live=True, base_url=f"http://127.0.0.1:{server.server_port}", retries=2, backoff=0
    )
    with pytest.raises(ResearchError, match="HTTP 500"):
        client.complete(ResearchRequest("r1", "Region", "ecologist", "Describe Region"))
    assert ProviderHandler.calls == 5


def test_research_artifacts_include_hashes_and_no_secret(tmp_path, server, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    api_key_value = "secret-value-that-must-not-leak"
    monkeypatch.setenv("PERPLEXITY_API_KEY", api_key_value)
    client = PerplexityClient(
        live=True, base_url=f"http://127.0.0.1:{server.server_port}", backoff=0
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
    client = PerplexityClient(live=True, base_url=f"http://127.0.0.1:{server.server_port}")
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
