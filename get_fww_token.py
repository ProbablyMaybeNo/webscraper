"""Helper: opens a visible browser window for you to log into FWW, then captures
and saves your auth token so the scraper can use it.

Run:  py -3.13 get_fww_token.py

Steps:
  1. A browser window will open to https://fallout.maloric.com
  2. Log in with Google or Apple
  3. Once logged in, this script captures your token and saves it to .fww_token
  4. The scraper will use this token automatically via env var FWW_AUTH_TOKEN
"""
import asyncio
import os
from pathlib import Path
from playwright.async_api import async_playwright

TOKEN_FILE = Path(".fww_token")


async def main():
    print("Opening browser... Log in with Google or Apple when the window opens.")
    print("The window will close automatically once your token is captured.\n")

    token = None

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)  # visible browser
        context = await browser.new_context()
        page = await context.new_page()

        async def on_request(request):
            nonlocal token
            auth = request.headers.get("authorization", "")
            if auth.startswith("Bearer ") and not token:
                candidate = auth.split("Bearer ", 1)[1].strip()
                if len(candidate) > 100:  # real JWT tokens are long
                    token = candidate
                    print(f"Token captured! ({len(token)} chars)")

        page.on("request", on_request)

        await page.goto("https://fallout.maloric.com/fww/library")
        print("Waiting for login (up to 120 seconds)...")

        # Wait until we capture a token or timeout
        for _ in range(120):
            await asyncio.sleep(1)
            if token:
                break

            # Also check localStorage
            try:
                t = await page.evaluate("""() => {
                    try {
                        return Object.values(localStorage)
                            .map(v => { try { return JSON.parse(v) } catch { return null } })
                            .filter(Boolean)
                            .find(v => v?.stsTokenManager?.accessToken)
                            ?.stsTokenManager?.accessToken || null;
                    } catch { return null; }
                }""")
                if t and len(t) > 100:
                    token = t
                    print(f"Token found in localStorage! ({len(token)} chars)")
                    break
            except Exception:
                pass

        await browser.close()

    if token:
        TOKEN_FILE.write_text(token)
        print(f"\nToken saved to: {TOKEN_FILE}")
        print(f"Token preview: {token[:40]}...")
        print("\nTo use it, run the scraper with:")
        print(f"  set FWW_AUTH_TOKEN={token[:40]}...")
        print("\nOr the token file will be loaded automatically by the scraper.")
    else:
        print("\nNo token captured. Make sure you logged in within 120 seconds.")


if __name__ == "__main__":
    asyncio.run(main())
