"""Debug script: captures all network traffic from FWW library and saves a screenshot."""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

URL = "https://fallout.maloric.com/fww/library"
OUT_DIR = Path("data")
OUT_DIR.mkdir(exist_ok=True)


async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
        )
        page = await context.new_page()

        all_requests = []
        all_responses = []

        page.on("request", lambda r: all_requests.append({"url": r.url, "method": r.method}))

        async def on_response(response):
            ct = response.headers.get("content-type", "")
            entry = {"url": response.url, "status": response.status, "content_type": ct}
            if "json" in ct:
                try:
                    data = await response.json()
                    entry["data"] = data
                    entry["data_keys"] = list(data.keys()) if isinstance(data, dict) else f"list[{len(data)}]"
                except Exception as e:
                    entry["json_error"] = str(e)
            all_responses.append(entry)
            print(f"  RESP {response.status} {ct[:30]:30s} {response.url[:80]}")

        page.on("response", on_response)

        print(f"Navigating to {URL}...")
        await page.goto(URL, wait_until="networkidle", timeout=60000)
        print("networkidle reached. Waiting 3s...")
        await page.wait_for_timeout(3000)

        # Try clicking/scrolling to trigger loads
        print("Scrolling...")
        for _ in range(5):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(1000)

        # Try Ionic scroll
        await page.evaluate("""
            const contents = document.querySelectorAll('ion-content');
            for (const c of contents) {
                const inner = c.shadowRoot && c.shadowRoot.querySelector('.inner-scroll');
                if (inner) { inner.scrollTop = inner.scrollHeight; }
            }
        """)
        await page.wait_for_timeout(2000)

        # Check DOM state
        dom_info = await page.evaluate("""() => {
            return {
                title: document.title,
                ion_items: document.querySelectorAll('ion-item').length,
                ion_cards: document.querySelectorAll('ion-card').length,
                all_imgs: document.querySelectorAll('img').length,
                app_root_children: document.querySelector('app-root')?.children.length || 0,
                body_text_len: document.body.innerText.length,
                body_text_sample: document.body.innerText.slice(0, 500),
                all_elements: document.querySelectorAll('*').length,
                classes_sample: Array.from(document.querySelectorAll('[class]')).slice(0,20).map(el => el.className).join(' | '),
            }
        }""")

        print("\n=== DOM State ===")
        for k, v in dom_info.items():
            if k != "body_text_sample":
                print(f"  {k}: {v}")
        print(f"  body_text_sample:\n{dom_info['body_text_sample'][:400]}")

        # Screenshot
        screenshot_path = OUT_DIR / "fww_debug.png"
        await page.screenshot(path=str(screenshot_path), full_page=False)
        print(f"\nScreenshot: {screenshot_path}")

        # Save all responses
        json_responses = [r for r in all_responses if "data" in r]
        print(f"\n=== JSON Responses ({len(json_responses)} total) ===")
        for r in json_responses[:20]:
            print(f"  {r['url'][:100]}")
            print(f"    keys: {r.get('data_keys', '?')}")

        # Save full network log
        net_log_path = OUT_DIR / "fww_network_log.json"
        with open(net_log_path, "w") as f:
            # Truncate large data payloads for readability
            log = []
            for r in all_responses:
                entry = {k: v for k, v in r.items() if k != "data"}
                if "data" in r:
                    d = r["data"]
                    if isinstance(d, dict):
                        entry["data_preview"] = {k: str(v)[:100] for k, v in list(d.items())[:10]}
                    elif isinstance(d, list):
                        entry["data_preview"] = [str(x)[:100] for x in d[:5]]
                    else:
                        entry["data_preview"] = str(d)[:200]
                log.append(entry)
            json.dump(log, f, indent=2)
        print(f"Network log: {net_log_path}")

        print(f"\nTotal requests: {len(all_requests)}")
        print(f"Total responses: {len(all_responses)}")

        await browser.close()


asyncio.run(main())
