"""E2-E4 on synthetic E1 output, the API over the results, and the annotation endpoint."""

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from novelty import judge
from novelty.api import check_bind, create_app
from novelty.experiments import e2_validity, e3_judgments, e4_disagreement
from novelty.experiments.common import ROOT, load_config
from novelty.items import Item, append
from novelty.results_md import write
from tests.conftest import synthetic_rows, write_e1


@pytest.fixture
def results(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.delenv("NOVELTY_API_TOKEN", raising=False)
    rows = synthetic_rows()
    out = tmp_path / "results"
    write_e1(out, rows)
    fake: list[dict[str, Any]] = [
        {"judge": j, "item": r["id"], "novelty": 5 - 4 * r["values"]["semantic_max"] + (0.1 if j == "qwen3-4b" else 0),
         "relevance": 4.0, "meaningfulness": 3.5, "novelty_dist": [0, 0, 1, 0, 0], "relevance_dist": [0, 0, 0, 1, 0],
         "meaningfulness_dist": [0, 0, 1, 0, 0]}
        for j in ("qwen3-4b", "phi-4-mini") for r in rows]  # fmt: skip
    monkeypatch.setattr(judge, "read_judgments", lambda path=None: fake)
    smoke = ROOT / "configs" / "smoke"
    e2_validity.run(load_config(smoke / "e2_validity.yaml"), out)
    e3_judgments.run(load_config(smoke / "e3_judgments.yaml"), out)
    e4_disagreement.run(load_config(smoke / "e4_disagreement.yaml"), out)
    return out


def latest(results: Path, exp: str, name: str) -> Any:
    d = results / exp / (results / exp / "LATEST").read_text().strip()
    return json.loads((d / name).read_text())


def test_validity_recovers_the_constructed_ordering(results: Path) -> None:
    auc = {(r["a"], r["b"], r["indicator"]): r["auroc"] for r in latest(results, "e2_validity", "auroc.json")}
    assert auc[("paraphrase", "later", "semantic_max")]["value"] > 0.95
    assert (
        auc[("paraphrase", "later", "new_phrase_share")]["value"] > 0.95
    )  # direction handled for a "more novel" indicator
    rec = latest(results, "e2_validity", "recovery.json")
    assert rec["paraphrase"]["top1_all"] == 1.0 and rec["recombination"]["top1_all"] == 0.0


def test_judgments_human_pending_and_model_correlation(results: Path) -> None:
    human = latest(results, "e3_judgments", "human.json")
    assert human["status"] == "pending" and human["correlations"] == []
    mj = latest(results, "e3_judgments", "model_judges.json")
    rho = {(c["subset"], c["indicator"]): c["rho"]["value"] for c in mj["correlations"]}
    assert rho[("all", "semantic_max")] == pytest.approx(1.0)  # the fake judge is a monotone function of similarity
    assert mj["agreement"]["novelty"]["spearman"] == pytest.approx(1.0)
    assert set(mj["per_judge"]) == {"qwen3-4b", "phi-4-mini"}
    summary = latest(results, "e3_judgments", "summary.json")
    assert any("not human judgments" in n for n in summary["notes"])


def test_groups_use_control_thresholds(results: Path) -> None:
    g = latest(results, "e4_disagreement", "groups.json")
    assert sum(c["n"] for c in g["counts"]) == 12
    assert g["thresholds"]["semantic_max"] < 0.85  # set on the paraphrase controls


def test_results_markdown_marks_missing_experiments(results: Path, tmp_path: Path) -> None:
    md = write(results, tmp_path / "r.md").read_text()
    assert md.startswith("# Measured results") and "Status: pending" in md  # E5 was not run


def test_api_reads_results_and_accepts_only_valid_annotations(results: Path, tmp_path: Path) -> None:
    items = tmp_path / "items.jsonl"
    for r in synthetic_rows()[:3]:
        append(Item(r["id"], r["topic"], r["kind"], r["model"], r["title"], r["text"]), items)
    store = tmp_path / "human.jsonl"
    c = TestClient(create_app(results, tmp_path / "static", store, items))
    assert [i["status"] for i in c.get("/api/experiments").json()["items"]] == ["complete"] * 4 + ["pending"]
    assert len(c.get("/api/overview").json()["items"]) == 48
    one = c.get("/api/items/calibration-idea-0").json()
    assert one["kind"] == "idea" and one["group"] in {"near-duplicate", "known combination", "new combination"}
    assert c.get("/api/items/nope").status_code == 404
    assert c.get("/api/items/..%2Fetc").status_code == 404
    for route in ("validity", "judgments", "disagreement"):
        assert c.get(f"/api/{route}").status_code == 200
    assert c.get("/api/robustness").status_code == 404
    q = c.get("/api/annotate/queue", params={"annotator": "rater1"}).json()
    assert (
        q["total"] == 3 and len(q["queue"]) == 3 and set(q["queue"][0]) == {"id", "topic", "title", "text"}
    )  # blinded
    body = {
        "annotator": "rater1",
        "item": q["queue"][0]["id"],
        "novelty": 3,
        "relevance": 4,
        "meaningfulness": 5,
        "comment": "",
    }
    assert c.post("/api/annotations", json=body).status_code == 200
    assert c.post("/api/annotations", json={**body, "novelty": 9}).status_code == 422
    assert c.post("/api/annotations", json={**body, "item": "unknown"}).status_code == 422
    assert (
        c.post("/api/annotations", content=b"x" * 5000, headers={"content-type": "application/json"}).status_code == 413
    )
    assert c.get("/api/annotate/queue", params={"annotator": "rater1"}).json()["done"] == 1
    assert c.get("/api/annotate/queue", params={"annotator": "bad name"}).status_code == 422
    assert c.delete("/api/annotations").status_code == 405
    assert c.post("/api/experiments").status_code == 405
    r = c.get("/api/health")
    assert r.headers["x-frame-options"] == "DENY" and "default-src 'self'" in r.headers["content-security-policy"]


def test_api_token_and_bind(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NOVELTY_API_TOKEN", raising=False)
    with pytest.raises(SystemExit):
        check_bind("0.0.0.0")
    monkeypatch.setenv("NOVELTY_API_TOKEN", "s3cret")
    c = TestClient(create_app(tmp_path, tmp_path, tmp_path / "h.jsonl", tmp_path / "i.jsonl"))
    assert c.get("/api/health").status_code == 200
    assert c.get("/api/experiments").status_code == 401
    assert c.post("/api/annotations", json={}).status_code == 401
    assert c.get("/api/experiments", headers={"Authorization": "Bearer s3cret"}).status_code == 200
