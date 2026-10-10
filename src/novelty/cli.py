"""Command line: ``novelty fetch | models | generate | judge | experiment | results | serve``."""

from __future__ import annotations

import argparse
import importlib
import os
import sys
from pathlib import Path

from novelty.experiments.common import ROOT, load_config

EXPERIMENTS = {"e1": "e1_indicators", "e2": "e2_validity", "e3": "e3_judgments", "e4": "e4_disagreement",
               "e5": "e5_robustness"}  # fmt: skip


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="novelty")
    sub = p.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch", help="rebuild the literature corpus from the DOI manifest (Crossref)")
    f.add_argument("--retrieve", action="store_true", help="search Crossref afresh and overwrite the manifest")
    mo = sub.add_parser("models", help="download the local language models (GGUF) and check their SHA-256")
    mo.add_argument("names", nargs="*")
    g = sub.add_parser("generate", help="write the generated ideas and controls (items/items.jsonl; resumable)")
    g.add_argument("--models", nargs="*")
    g.add_argument("--limit", type=int)
    j = sub.add_parser("judge", help="model-judge pilot: rate every item with the annotation rubric (resumable)")
    j.add_argument("--judges", nargs="*", default=["qwen3-4b", "phi-4-mini"])
    j.add_argument("--limit", type=int)
    e = sub.add_parser("experiment", help="run one experiment (e1..e5) or all of them in order")
    e.add_argument("name", choices=[*EXPERIMENTS, "all"])
    e.add_argument("--configs", type=Path, default=ROOT / "configs")
    e.add_argument("--results", type=Path)
    e.add_argument("--items", type=Path)
    r = sub.add_parser("results", help="render docs/generated/results.md from the latest runs")
    r.add_argument("--results", type=Path)
    r.add_argument("--out", type=Path)
    sv = sub.add_parser("serve", help="serve the Explorer console and API")
    sv.add_argument("--host", default=os.environ.get("NOVELTY_HOST", "127.0.0.1"))
    sv.add_argument("--port", type=int, default=int(os.environ.get("NOVELTY_PORT", "8000")))
    a = p.parse_args(argv)
    if a.cmd == "fetch":
        from novelty import corpus

        for k, n in corpus.fetch(a.retrieve).items():
            print(f"ok {k}: {n} papers")
    elif a.cmd == "models":
        from novelty.llm import fetch_models

        for path in fetch_models(a.names or None):
            print(f"ok {path.name}")
    elif a.cmd == "generate":
        from novelty import generate

        print(
            f"{generate.run(load_config(ROOT / 'configs' / 'generate.yaml'), models=a.models, limit=a.limit)} new items"
        )
    elif a.cmd == "judge":
        from novelty import judge

        print(f"{judge.run(a.judges, limit=a.limit)} new judgments")
    elif a.cmd == "experiment":
        for name in EXPERIMENTS if a.name == "all" else [a.name]:
            mod = importlib.import_module(f"novelty.experiments.{EXPERIMENTS[name]}")
            print(f"{name}: running", file=sys.stderr, flush=True)
            print(mod.run(load_config(a.configs / f"{EXPERIMENTS[name]}.yaml"), a.results, a.items), flush=True)
    elif a.cmd == "results":
        from novelty.results_md import write

        print(write(a.results, a.out))
    elif a.cmd == "serve":
        import uvicorn

        from novelty.api import check_bind, create_app

        check_bind(a.host)
        uvicorn.run(create_app(), host=a.host, port=a.port, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
