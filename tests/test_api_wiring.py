"""Guards for the router split — the app's shape, not any single endpoint.

The failure mode a router layout invites is silent: add a module under
``api_pkg/routers/``, forget to include it, and the endpoints simply do not
exist. These tests pin the wiring so that cannot ship.
"""

from __future__ import annotations

import pkgutil

import pytest
from fastapi.testclient import TestClient

from artificial_emotions.api import app, create_app
from artificial_emotions.api_pkg import routers as routers_pkg

# Every path the API serves. Adding one here is deliberate; losing one is a bug.
EXPECTED_PATHS = {
    "/",
    "/health",
    "/ready",
    "/v1/agent",
    "/v1/agent/tools",
    "/v1/briefs/critique",
    "/v1/curiosity/decompose",
    "/v1/curiosity/explore",
    "/v1/curiosity/provoke",
    "/v1/curiosity/run",
    "/v1/domains",
    "/v1/emotions/annotate",
    "/v1/emotions/catalog",
    "/v1/emotions/cues",
    "/v1/emotions/elicit",
    "/v1/emotions/mix",
    "/v1/emotions/pack",
    "/v1/epistemic/annotate",
    "/v1/epistemic/catalog",
    "/v1/epistemic/cues",
    "/v1/epistemic/elicit",
    "/v1/epistemic/mix",
    "/v1/epistemic/pack",
    "/v1/dream",
    "/v1/evals/cross-model-vote",
    "/v1/evals/idea-graph",
    "/v1/evals/soundness",
    "/v1/export/unknowns",
    "/v1/imagination",
    "/v1/imagination/transfer",
    "/v1/imagination/{kind}",
    "/v1/memory",
    "/v1/memory/avoiding",
    "/v1/memory/forget",
    "/v1/memory/reset",
    "/v1/preferences/hints",
    "/v1/preferences/suggest-pair",
    "/v1/preferences/summarize",
    "/v1/profiles",
    "/v1/profiles/compare",
    "/v1/profiles/constitution-compare",
    "/v1/stances",
    "/v1/stances/{stance}",
    "/v1/surprise/worksheet",
    "/v1/voi/worksheet",
}


def test_the_served_path_set_is_exactly_what_we_expect():
    assert set(app.openapi()["paths"]) == EXPECTED_PATHS


def test_every_router_module_is_included_in_the_app():
    """A router module that exists but is never included serves nothing."""
    served = set(app.openapi()["paths"])
    discovered = [name for _finder, name, _pkg in pkgutil.iter_modules(routers_pkg.__path__)]
    assert discovered, "no router modules found"

    for name in discovered:
        module = __import__(f"artificial_emotions.api_pkg.routers.{name}", fromlist=["router"])
        paths = {r.path for r in module.router.routes}
        assert paths, f"router {name} declares no routes"
        missing = paths - served
        assert not missing, f"router {name} is not wired into the app: {sorted(missing)}"


def test_epistemic_is_a_complete_alias_of_emotions():
    served = set(app.openapi()["paths"])
    emotions = {p for p in served if p.startswith("/v1/emotions/")}
    epistemic = {p for p in served if p.startswith("/v1/epistemic/")}
    assert emotions
    assert {p.replace("/v1/emotions/", "/v1/epistemic/") for p in emotions} == epistemic


def test_middleware_order_rate_limit_auth_cors():
    """Order is load-bearing: Starlette runs the last-added middleware outermost."""
    names = [m.cls.__name__ for m in app.user_middleware]
    assert names == [
        "AuditMiddleware",
        "RateLimitMiddleware",
        "OptionalApiKeyMiddleware",
        "CORSMiddleware",
    ]


def test_create_app_builds_an_equivalent_independent_app():
    fresh = create_app()
    assert fresh is not app
    assert set(fresh.openapi()["paths"]) == set(app.openapi()["paths"])


@pytest.mark.parametrize(
    "name",
    [
        "app",
        "create_app",
        "RunRequest",
        "ProvokeRequest",
        "ExportUnknownsRequest",
        "MixEmotionsRequest",
        "AnnotateEmotionsRequest",
        "OptionalApiKeyMiddleware",
    ],
)
def test_public_names_stay_importable_from_the_api_module(name: str):
    """`artificial_emotions.api` is the documented import path — keep it stable."""
    import artificial_emotions.api as api_mod

    assert hasattr(api_mod, name)


def test_openapi_schema_components_are_present():
    schemas = app.openapi()["components"]["schemas"]
    for expected in (
        "RunRequest",
        "ProvokeRequest",
        "MixEmotionsRequest",
        "ExportUnknownsRequest",
        "ValueProfile",
    ):
        assert expected in schemas


@pytest.mark.parametrize("path", ["/", "/health", "/ready", "/docs", "/openapi.json"])
def test_open_paths_stay_reachable_without_a_key(monkeypatch, path: str):
    monkeypatch.setenv("CURIOSITY_API_KEY", "secret-key")
    client = TestClient(app)
    assert client.get(path).status_code == 200


@pytest.mark.parametrize(
    "path",
    ["/v1/domains", "/v1/profiles", "/v1/agent", "/v1/emotions/cues"],
)
def test_protected_paths_require_a_key_across_routers(monkeypatch, path: str):
    """Auth is app-level middleware — it must cover every router, not just some."""
    monkeypatch.setenv("CURIOSITY_API_KEY", "secret-key")
    client = TestClient(app)
    assert client.get(path).status_code == 401
    ok = client.get(path, headers={"Authorization": "Bearer secret-key"})
    assert ok.status_code == 200


def test_errors_from_any_router_use_the_shared_envelope(monkeypatch):
    """Exception handlers are registered on the app, so routers share one error shape."""
    monkeypatch.delenv("CURIOSITY_API_KEY", raising=False)
    client = TestClient(app)
    res = client.post("/v1/emotions/mix", json={"weights": {"not_an_emotion": 100}})
    assert res.status_code >= 400
    body = res.json()
    assert "error" in body
    assert "code" in body["error"]
