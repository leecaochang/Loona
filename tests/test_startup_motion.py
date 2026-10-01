"""Exercise startup motion using real browser animations and pinned native HuiCard."""

import asyncio
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import shutil
import subprocess
from threading import Thread

import aiohttp
import pytest


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        """Keep local fixture access logging out of test output."""


async def test_native_browser_startup_motion(tmp_path):
    """Keep actual Animation ownership, restoration, and HA propagation observable."""
    browser = next(
        (path for path in (
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            shutil.which("chromium"), shutil.which("google-chrome"),
        ) if path and Path(path).is_file()), None
    )
    if browser is None:
        pytest.skip("A Chromium browser is required for native animation acceptance")
    built = subprocess.run(
        ["node", "tests/build_startup_motion.mjs", str(tmp_path / "fixture.js")],
        capture_output=True, text=True, timeout=30,
    )
    assert built.returncode == 0, built.stderr
    (tmp_path / "wall-panel").mkdir()
    (tmp_path / "wall-panel" / "main.html").write_text(
        '<!doctype html><html><body><script type="module" src="/fixture.js"></script></body></html>'
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(_QuietHandler, directory=str(tmp_path)))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    profile = tmp_path / "browser"
    # Use real time: virtual-time animation rendering can deadlock on macOS
    # without an attached display. Only the isolated fixture is accessible here.
    with (tmp_path / "browser.log").open("w") as log:
        process = subprocess.Popen(
            [browser, "--headless", "--disable-gpu", "--no-sandbox", "--no-first-run", "--no-default-browser-check",
             "--disable-background-timer-throttling", "--disable-renderer-backgrounding",
             f"--user-data-dir={profile}", "--remote-debugging-port=0", "about:blank"],
            stdout=log, stderr=log,
        )
        try:
            port_file = profile / "DevToolsActivePort"
            for _ in range(100):
                if port_file.exists():
                    break
                await asyncio.sleep(0.1)
            assert port_file.exists(), (tmp_path / "browser.log").read_text()
            port = int(port_file.read_text().splitlines()[0])
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(f"http://127.0.0.1:{port}/json/list") as response:
                    tabs = await response.json()
                tab = next(item for item in tabs if item["type"] == "page")
                async with session.ws_connect(tab["webSocketDebuggerUrl"]) as socket:
                    sequence = 0

                    async def command(method, **params):
                        nonlocal sequence
                        sequence += 1
                        await socket.send_json({"id": sequence, "method": method, "params": params})
                        while True:
                            value = await asyncio.wait_for(socket.receive_json(), 10)
                            if value.get("id") == sequence:
                                assert "error" not in value, value
                                return value["result"]

                    await command("Page.navigate", url=f"http://127.0.0.1:{server.server_port}/wall-panel/main.html")
                    last = None
                    for _ in range(200):
                        last = await command("Runtime.evaluate", expression="JSON.stringify({result: document.body?.dataset.result, text: document.body?.textContent})", returnByValue=True)
                        if '"result"' in last.get("result", {}).get("value", ""):
                            break
                        await asyncio.sleep(0.05)
                    assert '"result":"passed"' in last["result"].get("value", ""), last
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            server.shutdown()
            server.server_close()
            thread.join()
