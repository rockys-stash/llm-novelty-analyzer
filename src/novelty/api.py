"""HTTP API for the Novelty Explorer console.

- Every route is a GET over finished result directories, except ``POST /api/annotations``, which
  appends one validated human annotation to an append-only store. Nothing can be started or deleted.
- Every client is rate limited.
- With ``NOVELTY_API_TOKEN`` set, every ``/api`` route except ``/api/health`` needs
  ``Authorization: Bearer <token>``. Binding a non-loopback host without a token is refused.
"""

from __future__ import annotations

import hmac
import ipaddress
import json
import os
import re
import threading
import time
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from novelty.experiments.common import ROOT

EXPERIMENTS = ("e1_indicators", "e2_validity", "e3_judgments", "e4_disagreement", "e5_robustness")
_ITEM = re.compile(r"^[a-z0-9_-]{1,60}$")
_DOI = re.compile(r"^10\.[0-9]{4,9}/\S{1,200}$")
WRITABLE = {"/api/annotations"}
MAX_BODY = 4096
_RUN = re.compile(r"^[0-9]{8}T[0-9]{6}Z-[0-9a-z]{4,40}$")


class RateLimiter:
    """Token bucket per client address."""

    def __init__(self, rate: float, burst: int) -> None:
        self.rate, self.burst = rate, burst
        self._buckets: dict[str, tuple[float, float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            tokens, last = self._buckets.get(key, (float(self.burst), now))
            tokens = min(self.burst, tokens + (now - last) * self.rate)
            if tokens < 1:
                self._buckets[key] = (tokens, now)
                return False
            self._buckets[key] = (tokens - 1, now)
            if len(self._buckets) > 10_000:
                self._buckets = dict(list(self._buckets.items())[-5_000:])
            return True


class GuardMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: Any, token: str | None, limiter: RateLimiter) -> None:
        super().__init__(app)
        self.token, self.limiter = token, limiter

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path
        if path.startswith("/api"):
            client = request.client.host if request.client else "unknown"
            if not self.limiter.allow(client):
                return JSONResponse({"detail": "rate limit exceeded"}, status_code=429, headers={"Retry-After": "1"})
            if request.method not in ("GET", "HEAD") and not (request.method == "POST" and path in WRITABLE):
                return JSONResponse({"detail": "read-only API"}, status_code=405)
            if request.method == "POST" and int(request.headers.get("content-length") or MAX_BODY + 1) > MAX_BODY:
                return JSONResponse({"detail": "request body too large or without length"}, status_code=413)
            if self.token and path != "/api/health":
                supplied = request.headers.get("authorization", "").removeprefix("Bearer ").strip()
                if not hmac.compare_digest(supplied.encode(), self.token.encode()):
                    return JSONResponse({"detail": "unauthorized"}, status_code=401)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
            "font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        )
        return response


def is_loopback(host: str) -> bool:
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def check_bind(host: str) -> None:
    if not is_loopback(host) and not os.environ.get("NOVELTY_API_TOKEN"):
        raise SystemExit(f"refusing to serve on {host} without NOVELTY_API_TOKEN")


def create_app(results: Path | None = None, static_dir: Path | None = None, store: Path | None = None,
               items_path: Path | None = None) -> FastAPI:  # fmt: skip
    from novelty import annotations as human_store
    from novelty import corpus, judge
    from novelty.items import ITEMS, read

    results = (results or ROOT / "results").resolve()
    static = (static_dir or ROOT / "web" / "dist").resolve()
    store = store or human_store.STORE
    items_file = items_path or ITEMS
    token = os.environ.get("NOVELTY_API_TOKEN") or None
    app = FastAPI(title="novelty", docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(
        GuardMiddleware,
        token=token,
        limiter=RateLimiter(rate=float(os.environ.get("NOVELTY_RATE_PER_SEC", "30")), burst=120),
    )

    def run_dir(exp: str) -> Path | None:
        if exp not in EXPERIMENTS:
            raise HTTPException(404, "unknown experiment")
        marker = results / exp / "LATEST"
        if not marker.is_file():
            return None
        run_id = marker.read_text(encoding="utf-8").strip()
        if not _RUN.match(run_id):
            raise HTTPException(500, "corrupt LATEST marker")
        d = results / exp / run_id
        return d if (d / "summary.json").is_file() else None

    def need(exp: str) -> Path:
        d = run_dir(exp)
        if d is None:
            raise HTTPException(404, f"{exp} has not been run")
        return d

    @lru_cache(maxsize=32)
    def _read(path: str, mtime: float) -> Any:
        return json.loads(Path(path).read_text(encoding="utf-8"))

    def read_json(p: Path) -> Any:
        if not p.is_file():
            raise HTTPException(404, f"{p.name} missing")
        return _read(str(p), p.stat().st_mtime)

    def prov(d: Path) -> Any:
        return read_json(d / "provenance.json")

    def item_ids() -> set[str]:
        return {i.id for i in read(items_file)}

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/experiments")
    def experiments() -> dict[str, Any]:
        items = []
        for exp in EXPERIMENTS:
            d = run_dir(exp)
            if d is None:
                items.append({"experiment": exp, "status": "pending"})
            else:
                s = read_json(d / "summary.json")
                items.append({"experiment": exp, "status": "complete", "title": s["title"], "question": s["question"],
                              **prov(d)})  # fmt: skip
        return {"items": items}

    @app.get("/api/experiments/{exp}")
    def experiment(exp: str) -> dict[str, Any]:
        d = need(exp)
        return {**read_json(d / "summary.json"), "provenance": prov(d)}

    @app.get("/api/overview")
    def overview() -> dict[str, Any]:
        d = need("e1_indicators")
        rows = [
            {k: r[k] for k in ("id", "topic", "kind", "model", "title", "values")} for r in read_json(d / "items.json")
        ]
        out: dict[str, Any] = {"items": rows, "corpus": read_json(d / "corpus.json"), "by_kind": read_json(d / "by_kind.json"),
                               "topics": corpus.topics(), "provenance": prov(d)}  # fmt: skip
        if (d4 := run_dir("e4_disagreement")) is not None:
            g = read_json(d4 / "groups.json")
            out["groups"] = {i["id"]: i["group"] for i in g["ideas"]}
        return out

    @app.get("/api/items/{item_id}")
    def item(item_id: str) -> dict[str, Any]:
        if not _ITEM.match(item_id):
            raise HTTPException(404, "unknown item")
        d = need("e1_indicators")
        row = next((r for r in read_json(d / "items.json") if r["id"] == item_id), None)
        if row is None:
            raise HTTPException(404, "unknown item")
        out: dict[str, Any] = {**row, "topic_label": corpus.topics().get(row["topic"], row["topic"]),
                               "judgments": [j for j in judge.read_judgments() if j["item"] == item_id],
                               "human": [{k: h[k] for k in ("novelty", "relevance", "meaningfulness")}
                                         for h in human_store.latest(store) if h["item"] == item_id],
                               "provenance": prov(d)}  # fmt: skip
        if (d4 := run_dir("e4_disagreement")) is not None:
            g = read_json(d4 / "groups.json")
            out["group"] = next((i["group"] for i in g["ideas"] if i["id"] == item_id), None)
            out["thresholds"] = g["thresholds"]
        return out

    @app.get("/api/papers")
    def paper(doi: str) -> dict[str, Any]:
        """A corpus paper's abstract, from the local copy (abstracts are never committed)."""
        if not _DOI.match(doi):
            raise HTTPException(404, "unknown paper")
        doi = doi.lower()
        for t in corpus.topics():
            for part in ("corpus", "later"):
                try:
                    papers = corpus.load(t, part)
                except FileNotFoundError:
                    raise HTTPException(404, "corpus not fetched (make data)") from None
                for p in papers:
                    if p.doi == doi:
                        return {"doi": p.doi, "title": p.title, "abstract": p.abstract, "year": p.year, "venue": p.venue,
                                "topic": t, "part": part, "references": len(p.references), "cited_by": p.cited_by}  # fmt: skip
        raise HTTPException(404, "unknown paper")

    for route, exp, files in (("validity", "e2_validity", ("auroc.json", "recovery.json")),
                              ("judgments", "e3_judgments", ("human.json", "model_judges.json")),
                              ("disagreement", "e4_disagreement", ("matrix.json", "groups.json")),
                              ("robustness", "e5_robustness", ("variants.json",))):  # fmt: skip

        def handler(exp: str = exp, files: tuple[str, ...] = files) -> dict[str, Any]:
            d = need(exp)
            return {**{f.removesuffix(".json"): read_json(d / f) for f in files}, "provenance": prov(d)}

        app.add_api_route(f"/api/{route}", handler, methods=["GET"])

    @app.get("/api/annotate/queue")
    def queue(annotator: str) -> dict[str, Any]:
        """Items for one annotator, blinded (no kind, model, source or indicator), in an order fixed per annotator."""
        if not re.match(r"^[A-Za-z0-9_-]{2,32}$", annotator):
            raise HTTPException(422, "annotator must be a pseudonym of 2-32 letters, digits, - or _")
        items = read(items_file)
        done = {h["item"] for h in human_store.latest(store) if h["annotator"] == annotator}
        seed = int.from_bytes(hmac.digest(b"novelty-queue", annotator.encode(), "sha256")[:8], "big")
        import random

        order = sorted(items, key=lambda i: i.id)
        random.Random(seed).shuffle(order)
        labels = corpus.topics()
        todo = [{"id": i.id, "topic": labels.get(i.topic, i.topic), "title": i.title, "text": i.text}
                for i in order if i.id not in done]  # fmt: skip
        return {"annotator": annotator, "done": len(done), "total": len(items), "queue": todo[:20]}

    @app.post("/api/annotations")
    async def annotate(request: Request) -> dict[str, Any]:
        try:
            body = await request.json()
        except ValueError:
            raise HTTPException(400, "body must be JSON") from None
        if not isinstance(body, dict):
            raise HTTPException(400, "body must be a JSON object")
        try:
            rec = human_store.validate(body, item_ids())
        except human_store.InvalidAnnotationError as exc:
            raise HTTPException(422, str(exc)) from None
        return {"saved": human_store.append(rec, store)}

    @app.get("/api/{rest:path}")
    def api_404(rest: str) -> Response:
        return JSONResponse({"detail": "not found"}, status_code=404)

    @app.get("/{rest:path}")
    def spa(rest: str) -> Response:
        if not static.exists():
            return JSONResponse({"detail": "console not built (npm --prefix web run build)"}, status_code=404)
        candidate = (static / rest).resolve()
        if rest and candidate.is_file() and candidate.is_relative_to(static):
            return FileResponse(candidate)
        return FileResponse(static / "index.html")

    return app
