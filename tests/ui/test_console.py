"""Browser tests for the Explorer console.

The fixture builds a results tree from synthetic E1 rows (tests/conftest.py) and runs E2-E4 on it,
with fake model judgments, so the console is tested on real pipeline output without the corpus or
the language models. Run with ``uv run pytest -m ui`` after ``npm --prefix web run build``.
"""

from __future__ import annotations

import socket
import threading
import time
import urllib.request
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from novelty import judge
from novelty.experiments import e2_validity, e3_judgments, e4_disagreement
from novelty.experiments.common import load_config
from novelty.items import Item, append
from tests.conftest import synthetic_rows, write_e1

ROOT = Path(__file__).resolve().parents[2]
AXE = ROOT / "web" / "node_modules" / "axe-core" / "axe.min.js"
pytestmark = [pytest.mark.ui]
playwright_api = pytest.importorskip("playwright.sync_api")

VIEWPORTS = {"desktop": {"width": 1440, "height": 900}, "mobile": {"width": 390, "height": 844}}


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.fixture(scope="module")
def base_url(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    if not (ROOT / "web" / "dist" / "index.html").exists():
        pytest.skip("frontend not built (npm --prefix web run build)")
    import uvicorn

    from novelty.api import create_app

    mp = pytest.MonkeyPatch()
    mp.delenv("NOVELTY_API_TOKEN", raising=False)
    tmp = tmp_path_factory.mktemp("ui")
    rows = synthetic_rows()
    results = tmp / "results"
    write_e1(results, rows)
    fake = [{"judge": j, "item": r["id"], "novelty": 5 - 4 * r["values"]["semantic_max"], "relevance": 4.0,
             "meaningfulness": 3.5, "novelty_dist": [0, 0, 1, 0, 0], "relevance_dist": [0, 0, 0, 1, 0],
             "meaningfulness_dist": [0, 0, 1, 0, 0]} for j in ("qwen3-4b", "phi-4-mini") for r in rows]  # fmt: skip
    mp.setattr(judge, "read_judgments", lambda path=None: fake)
    smoke = ROOT / "configs" / "smoke"
    e2_validity.run(load_config(smoke / "e2_validity.yaml"), results)
    e3_judgments.run(load_config(smoke / "e3_judgments.yaml"), results)
    e4_disagreement.run(load_config(smoke / "e4_disagreement.yaml"), results)
    items = tmp / "items.jsonl"
    for r in rows:
        append(Item(r["id"], r["topic"], r["kind"], r["model"], r["title"], "An idea about calibration. " * 4), items)
    app = create_app(results, store=tmp / "human.jsonl", items_path=items)
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{port}"
    for _ in range(100):
        try:
            urllib.request.urlopen(f"{url}/api/health", timeout=1)
            break
        except OSError:
            time.sleep(0.1)
    yield url
    server.should_exit = True
    thread.join(timeout=5)
    mp.undo()


@pytest.fixture(scope="module")
def browser() -> Iterator[Any]:
    with playwright_api.sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


PAGES = [
    ("ideas", "/ideas", "Indicators by item kind"),
    ("item", "/items/calibration-idea-1", "Prior-art map"),
    ("validity", "/validity", "AUROC by indicator"),
    ("judgments", "/judgments", "Human study"),
    ("disagreement", "/disagreement", "Generated ideas by group"),
    ("annotate", "/annotate", "Start annotating"),
    ("e2", "/experiments/e2_validity", "Findings"),
    ("e5-pending", "/experiments/e5_robustness", "pending"),
    ("method", "/method", "Limits"),
    ("not-found", "/nowhere", "Page not found"),
]


def _open(browser: Any, base_url: str, viewport: str, path: str, marker: str, scheme: str = "light") -> Any:
    ctx = browser.new_context(viewport=VIEWPORTS[viewport], color_scheme=scheme)
    page = ctx.new_page()
    errors: list[str] = []
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" and "404" not in m.text else None)
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(base_url + path)
    page.get_by_text(marker, exact=False).first.wait_for(timeout=30000)
    page.wait_for_load_state("networkidle")
    page.errors = errors
    return page


@pytest.mark.parametrize("viewport", list(VIEWPORTS))
@pytest.mark.parametrize(("name", "path", "marker"), PAGES)
def test_page_renders(browser: Any, base_url: str, viewport: str, name: str, path: str, marker: str) -> None:
    page = _open(browser, base_url, viewport, path, marker)
    assert page.locator("h1").count() == 1
    assert not page.locator(".skeleton").count(), "loading skeleton still visible"
    if name != "e5-pending":
        assert not page.locator("[role=alert]").count(), "error state rendered"
    overflow = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
    assert overflow <= 1, f"page scrolls horizontally by {overflow}px"
    assert not page.errors, page.errors
    page.context.close()


def test_filters_and_item_navigation(browser: Any, base_url: str) -> None:
    page = _open(browser, base_url, "desktop", "/ideas", "Indicators by item kind")
    table = page.get_by_role("region", name="Items with their indicators")
    assert table.locator("tbody tr").count() == 12  # generated ideas by default
    page.get_by_role("combobox", name="Kind").select_option("all")
    assert table.locator("tbody tr").count() == 48
    page.get_by_role("group", name="Indicator").get_by_role("button", name="New phrases").click()
    table.locator("tbody tr a").first.click()
    page.get_by_text("Prior-art map").wait_for()
    assert "/items/" in page.url
    page.context.close()


def test_annotation_round_trip(browser: Any, base_url: str) -> None:
    page = _open(browser, base_url, "desktop", "/annotate", "Start annotating")
    save = page.get_by_role("button", name="Start annotating")
    assert save.is_disabled()
    page.get_by_label("Pseudonym").fill("ui_rater")
    save.click()
    page.get_by_text("0 of 48 done").wait_for()
    assert page.get_by_text("calibration-").count() == 0  # blind: no item id, kind or model on screen
    for legend in ("Novelty", "Relevance to the topic", "Meaningfulness"):
        page.get_by_role("group", name=legend).get_by_role("radio").nth(2).check()
    page.get_by_role("button", name="Save and next").click()
    page.get_by_text("1 of 48 done").first.wait_for()
    page.context.close()


@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("viewport", list(VIEWPORTS))
def test_no_wcag_violations(browser: Any, base_url: str, viewport: str, scheme: str) -> None:
    """axe-core audit (WCAG 2.1 A/AA and best practices) of every view in both themes."""
    if not AXE.exists():
        pytest.skip("axe-core not installed (npm --prefix web ci)")
    ctx = browser.new_context(viewport=VIEWPORTS[viewport], color_scheme=scheme, bypass_csp=True)
    page = ctx.new_page()
    found: dict[str, list[str]] = {}
    for _, path, marker in PAGES:
        page.goto(base_url + path)
        page.get_by_text(marker, exact=False).first.wait_for(timeout=30000)
        page.wait_for_load_state("networkidle")
        page.add_script_tag(path=str(AXE))
        violations = page.evaluate(
            """async () => (await axe.run(document, {runOnly: ['wcag2a', 'wcag2aa', 'wcag21aa',
               'best-practice']})).violations.map(v => v.id + ': ' + v.nodes.map(n => n.target.join(' ')).join(', '))"""
        )
        if violations:
            found[path] = violations
    ctx.close()
    assert not found, found
