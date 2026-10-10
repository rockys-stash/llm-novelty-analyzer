"""Shared experiment plumbing: versioned result directories with provenance, and summary tables."""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import subprocess
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path
from typing import Any

import yaml

from novelty import corpus as _corpus

ROOT = Path(__file__).resolve().parents[3]
CPU = platform.processor() or platform.machine()


def git_commit(root: Path = ROOT) -> tuple[str, bool]:
    """The current commit and whether the work tree has uncommitted changes."""
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True
        ).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain", "--", "src", "configs"], cwd=root,
                                    capture_output=True, text=True, check=True).stdout.strip())  # fmt: skip
    except (OSError, subprocess.CalledProcessError):
        return "unknown", True
    return sha, dirty


def table(id_: str, caption: str, columns: list[tuple[str, str, str]], rows: list[dict[str, Any]]) -> dict[str, Any]:
    """A summary table; ``columns`` are (key, label, align) with align "l" or "r"."""
    return {"id": id_, "caption": caption, "columns": [{"key": k, "label": lab, "align": a} for k, lab, a in columns],
            "rows": rows}  # fmt: skip


def clean(v: Any) -> Any:
    if isinstance(v, float):
        return v if math.isfinite(v) else None
    if isinstance(v, dict):
        return {k: clean(x) for k, x in v.items()}
    if isinstance(v, list | tuple):
        return [clean(x) for x in v]
    if hasattr(v, "item") and not isinstance(v, str):  # numpy scalar
        return clean(v.item())
    return v


@dataclass
class Summary:
    title: str
    question: str
    findings: list[str] = field(default_factory=list)
    tables: list[dict[str, Any]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass
class ResultDir:
    experiment: str
    path: Path
    run_id: str
    config: dict[str, Any]

    def write_json(self, name: str, data: Any) -> Path:
        """Write JSON; NaN and infinities become null (they are not valid JSON and mean "undefined" here)."""
        p = self.path / name
        p.write_text(
            json.dumps(clean(data), indent=1, ensure_ascii=False, default=str, allow_nan=False), encoding="utf-8"
        )
        return p


@contextmanager
def result_dir(
    experiment: str, config: dict[str, Any], description: str, results: Path | None = None
) -> Iterator[tuple[ResultDir, Summary]]:
    """Create the versioned directory, yield it, then write provenance and point ``LATEST`` at it.

    If the body raises, the directory is kept with ``FAILED`` in it and ``LATEST`` is not moved, so a
    failed run can never be mistaken for a result.
    """
    results = results or ROOT / "results"
    sha, dirty = git_commit()
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"{stamp}-{sha[:7]}"
    path = results / experiment / run_id
    path.mkdir(parents=True, exist_ok=False)
    (path / "config.yaml").write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    rd, summary = ResultDir(experiment, path, run_id, config), Summary(title="", question="")
    t0 = time.perf_counter()
    try:
        yield rd, summary
    except BaseException as exc:
        (path / "FAILED").write_text(f"{type(exc).__name__}: {exc}\n", encoding="utf-8")
        raise
    prov = {
        "experiment": experiment,
        "run_id": run_id,
        "commit": sha,
        "dirty": dirty,
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "runtime_seconds": round(time.perf_counter() - t0, 2),
        "description": description,
        "config_sha256": hashlib.sha256((path / "config.yaml").read_bytes()).hexdigest(),
        "python": platform.python_version(),
        "machine": CPU,
        "cpus": os.cpu_count(),
        "packages": {p: metadata.version(p) for p in ("scikit-learn", "numpy", "scipy", "sentence-transformers")},
        "inputs_sha256": _corpus.input_hashes(),
    }
    rd.write_json("provenance.json", prov)
    rd.write_json("summary.json", summary.__dict__)
    (results / experiment / "LATEST").write_text(run_id + "\n", encoding="utf-8")


class _Loader(yaml.SafeLoader):
    """Safe YAML with ``!include other.yaml`` (resolved relative to the including file)."""


def load_config(path: Path) -> dict[str, Any]:
    """Read an experiment config, resolving ``!include`` so the saved config is self-contained."""

    def include(loader: _Loader, node: yaml.Node) -> Any:
        target = (path.parent / str(loader.construct_scalar(node))).resolve()  # type: ignore[arg-type]
        if ROOT.resolve() / "configs" not in target.parents:
            raise ValueError(f"!include outside configs/: {target}")
        return load_config(target)

    loader: type[_Loader] = type("L", (_Loader,), {})
    loader.add_constructor("!include", include)
    data = yaml.load(path.read_text(encoding="utf-8"), Loader=loader)
    if not isinstance(data, dict):
        raise ValueError(f"{path} is not a mapping")
    return data


def latest_run(experiment: str, results: Path | None = None) -> Path:
    """The directory ``LATEST`` points at; an experiment that depends on another reads it from here."""
    base = (results or ROOT / "results") / experiment
    marker = base / "LATEST"
    if not marker.exists():
        raise FileNotFoundError(f"{experiment} has not been run (results/{experiment}/LATEST missing)")
    return base / marker.read_text(encoding="utf-8").strip()


def fmt(v: Any, digits: int = 3) -> str:
    if v is None or (isinstance(v, float) and v != v):
        return "–"
    return f"{v:.{digits}f}"


def ci(d: dict[str, Any], digits: int = 3) -> str:
    if d.get("lo") is None:
        return fmt(d["value"], digits)
    return f"{fmt(d['value'], digits)} [{fmt(d['lo'], digits)}, {fmt(d['hi'], digits)}]"
