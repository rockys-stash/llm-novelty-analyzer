"""Capture screenshots of the running console from the committed results.

Usage: uv run python scripts/screenshots.py [--out docs/screenshots]
Needs the built console (npm --prefix web run build), Chromium for Playwright and results/.
"""

from __future__ import annotations

import argparse
import socket
import threading
import time
import urllib.request
from pathlib import Path

import uvicorn
from playwright.sync_api import ViewportSize, sync_playwright

from novelty.api import create_app

ROOT = Path(__file__).resolve().parents[1]
VIEWPORTS: dict[str, ViewportSize] = {
    "desktop": {"width": 1440, "height": 900},
    "mobile": {"width": 390, "height": 844},
}
SHOTS = [
    ("ideas", "/ideas"),
    ("item", "/items/{item}"),
    ("validity", "/validity"),
    ("judgments", "/judgments"),
    ("disagreement", "/disagreement"),
    ("annotate", "/annotate"),
    ("method", "/method"),
]


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=ROOT / "docs" / "screenshots")
    ap.add_argument("--results", type=Path, default=ROOT / "results")
    args = ap.parse_args()
    import json

    from novelty.experiments.common import latest_run

    rows = json.loads((latest_run("e1_indicators", args.results) / "items.json").read_text(encoding="utf-8"))
    # the generated idea with the most concept pairs no prior paper combines: the most informative map
    item = max((r for r in rows if r["kind"] == "idea"), key=lambda r: (len(r["unseen_pairs"]), r["id"]))["id"]
    app = create_app(args.results)
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    base = f"http://127.0.0.1:{port}"
    for _ in range(100):
        try:
            urllib.request.urlopen(base + "/api/health", timeout=1)
            break
        except OSError:
            time.sleep(0.1)
    args.out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for vp, size in VIEWPORTS.items():
            for scheme in ("light", "dark"):
                if vp == "mobile" and scheme == "dark":
                    continue
                ctx = browser.new_context(viewport=size, color_scheme=scheme, device_scale_factor=1)
                page = ctx.new_page()
                for name, path in SHOTS:
                    page.goto(base + path.format(item=item))
                    page.locator("h1").first.wait_for(timeout=30000)
                    page.wait_for_load_state("networkidle")
                    if page.locator(".skeleton").count():
                        page.locator(".skeleton").first.wait_for(state="detached", timeout=30000)
                    if name == "item":  # open the nearest paper's abstract
                        page.get_by_role("button", name="Show abstract").first.click()
                        page.locator(".abstract").first.wait_for(timeout=30000)
                    out = args.out / f"{name}-{vp}{'-dark' if scheme == 'dark' else ''}.png"
                    page.screenshot(path=str(out), full_page=vp == "desktop")
                    print(out.relative_to(ROOT))
                ctx.close()
        browser.close()
    server.should_exit = True


if __name__ == "__main__":
    main()
