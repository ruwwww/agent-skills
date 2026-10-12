import json
import time
import re
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

CREDENTIALS_FILE = Path.home() / ".its_classroom" / "credentials.json"
SESSION_FILE = Path.home() / ".its_classroom" / "session.json"
PROFILE_DIR = Path.home() / ".its_classroom" / "browser_profile"
LOGIN_SSO_URL = "https://classroom.its.ac.id/auth/oidc/?source=loginpage"

def main():
    if not CREDENTIALS_FILE.exists():
        print("Credentials file not found at", CREDENTIALS_FILE, file=sys.stderr)
        sys.exit(1)

    with open(CREDENTIALS_FILE) as f:
        creds = json.load(f)

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-infobars",
            ],
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 850},
        )
        page = context.pages[0] if context.pages else context.new_page()

        try:
            page.goto(LOGIN_SSO_URL, wait_until="domcontentloaded", timeout=15000)
        except Exception:
            pass

        time.sleep(2)

        # Check if already authenticated via KMSI
        if "classroom.its.ac.id" in page.url and "/login/" not in page.url and "/auth/oidc/" not in page.url:
            cookies = {c["name"]: c["value"] for c in context.cookies("https://classroom.its.ac.id")}
            if "MoodleSession" in cookies:
                print("ALREADY_AUTHENTICATED")
                context.close()
                return

        # Enter email if prompted
        if page.locator("input[name=\"loginfmt\"], input[type=\"email\"]").count() > 0:
            page.fill("input[name=\"loginfmt\"], input[type=\"email\"]", creds["email"])
            page.click("input[type=\"submit\"], #idSIButton9")
            time.sleep(2)

        # Enter password if prompted
        if page.locator("input[name=\"passwd\"], input[type=\"password\"]").count() > 0:
            page.fill("input[name=\"passwd\"], input[type=\"password\"]", creds["password"])
            page.click("input[type=\"submit\"], #idSIButton9")
            time.sleep(4)

        # Check if on "Verify your identity" list
        if page.locator("text=Approve a request on my Microsoft Authenticator app").count() > 0:
            page.locator("text=Approve a request on my Microsoft Authenticator app").first.click()
            time.sleep(3)

        # Extract 2-digit number code
        num_el = page.locator("#idRichContext_DisplaySign, #displaySign, div[data-bind*=\"displaySign\"]")
        number = ""
        if num_el.count() > 0:
            number = num_el.first.inner_text().strip()
        else:
            m = re.search(r"\b(\d{2})\b", page.inner_text("body"))
            if m:
                number = m.group(1)

        print(f"NUMBER_MATCHING_CODE:{number}", flush=True)

        # Wait for user approval
        for _ in range(90):
            if page.locator("#idSIButton9").count() > 0 and page.locator("#idSIButton9").first.is_visible():
                try:
                    page.locator("#idSIButton9").click()
                    time.sleep(3)
                except Exception:
                    pass

            if "classroom.its.ac.id" in page.url and "/login/" not in page.url and "/auth/oidc/" not in page.url:
                break
            time.sleep(1)

        cookies = {c["name"]: c["value"] for c in context.cookies("https://classroom.its.ac.id")}
        if "MoodleSession" in cookies:
            session_data = {
                "cookies": cookies,
                "moodle_session": cookies["MoodleSession"],
                "updated_at": int(time.time()),
                "metadata": {
                    "method": "fast_trigger_number_matching",
                    "email": creds["email"],
                },
            }
            with open(SESSION_FILE, "w") as f:
                json.dump(session_data, f, indent=2)
            print("SUCCESS_SESSION_SAVED", flush=True)
        else:
            print("FAILED_NO_SESSION", flush=True)

        context.close()

if __name__ == "__main__":
    main()
