"""Checks the built browser version really works: opens it in headless Chromium, waits for Python to start,
then opens every example, runs it for a moment and looks for errors. Used by the GitHub build before the web
version is published, and handy locally:

    python tools/build_web.py --pyodide <pyodide folder>
    python tools/web_smoke.py _site                    # needs:  pip install playwright; playwright install chromium

Exit code 0 = all good. Screenshots go to web-smoke/ (or --shots).
"""
from __future__ import annotations

import argparse
import functools
import http.server
import os
import sys
import threading


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def serve(folder):
    handler = functools.partial(_Quiet, directory=folder)
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("site", nargs="?", default="_site")
    ap.add_argument("--shots", default="web-smoke")
    ap.add_argument("--need-numpy", action="store_true", help="fail if the real numpy didn't load")
    ap.add_argument("--seconds", type=float, default=1.2, help="how long to run each example")
    a = ap.parse_args(argv)
    from playwright.sync_api import sync_playwright

    os.makedirs(a.shots, exist_ok=True)
    srv = serve(os.path.abspath(a.site))
    url = f"http://127.0.0.1:{srv.server_address[1]}/?nosw"
    problems = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1366, "height": 768})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(url)
        page.wait_for_function("() => !document.getElementById('app').classList.contains('loading') || "
                               "document.getElementById('loadText').classList.contains('error')", timeout=180_000)
        if page.evaluate("document.getElementById('loadText').classList.contains('error')"):
            print("FAILED TO START:", page.inner_text("#loadText"))
            page.screenshot(path=os.path.join(a.shots, "failed.png"))
            return 1
        maths = page.evaluate("numpyKind")
        print(f"Wirely Web started ({page.evaluate('app.version()')}, maths: {maths})")
        if a.need_numpy and maths != "numpy":
            problems.append("the real numpy didn't load")
        names = page.evaluate("examples")
        for n in names:
            page.evaluate("(n) => openExample(n)", n)
            page.wait_for_timeout(150)
            page.evaluate("() => doAction('play')")
            page.wait_for_timeout(int(a.seconds * 1000))
            t = page.inner_text("#timeLabel")
            state = page.evaluate("ui.sim")
            toasts = page.evaluate("[...document.querySelectorAll('.toast.error')].map(t => t.textContent)")
            safe = "".join(ch if ch.isalnum() else "_" for ch in n)
            page.screenshot(path=os.path.join(a.shots, f"{safe}.png"))
            page.evaluate("() => doAction('stop')")
            ok = state == "running" and t.startswith("t = ") and not t.startswith("t = 0.00") and not toasts
            print(f"  {'ok ' if ok else 'BAD'} {n:36s} {t}  {'; '.join(toasts)}")
            if not ok and "Buck" not in n:          # the buck converter is allowed to be slow
                problems.append(f"{n}: {state} {t} {toasts}")
        # a little editing: place a part from the gallery and undo it
        page.click('.tile[data-kind="resistor"]')
        box = page.locator("#sheet").bounding_box()
        page.mouse.move(box["x"] + 300, box["y"] + 300)
        page.mouse.click(box["x"] + 300, box["y"] + 300)
        page.keyboard.press("Control+z")
        if errors:
            problems += [f"page error: {e}" for e in errors]
        browser.close()
    srv.shutdown()
    if problems:
        print("PROBLEMS:")
        for p in problems:
            print("  -", p)
        return 1
    print("All good.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
