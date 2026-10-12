---
name: its-classroom-sso-automation
description: Use when automating Microsoft SSO for ITS Classroom Moodle.
---

# ITS Classroom & Microsoft SSO Automation Guide

Guides reliable automation of Microsoft Entra ID / Azure AD Single Sign-On (SSO) for `classroom.its.ac.id` (Moodle) via Playwright.

## Key Session Concepts & Lifecycles
* **Microsoft SSO Session (Entra ID KMSI Token):**
  * Stored in persistent browser profile: `~/.its_classroom/browser_profile/`
  * Valid for **30 to 90 days** once authenticated with "Stay signed in? Yes".
* **Moodle ITS Classroom Session (`MoodleSession` cookie):**
  * Short-lived (expires after **2 to 4 hours** or idle timeout).

## Scripts & Automation Helpers
* `scripts/fast_trigger.py`: Deterministically triggers the Microsoft Number Matching prompt, outputs `NUMBER_MATCHING_CODE:<2-digit>`, waits for mobile approval, and updates `session.json`.

## Authentication Workflow & MFA Handling
1. **Interactive / Push MFA Trigger (Number Matching):**
   * The user uses **Microsoft Authenticator Number Matching (2-digit code)** via push notification on their phone.
   * **Do NOT send or guess 6-digit TOTP codes.** Microsoft Entra ID rejects manual TOTP input when Number Matching is enforced.
   * If the selection screen ("Verify your identity") appears, click `"Approve a request on my Microsoft Authenticator app"` to trigger the push notification.
   * **IMMEDIATE CODE DELIVERY RULE:** As soon as the 2-digit number appears (in `#idRichContext_DisplaySign`, `#displaySign`, or the display card), **immediately stop all intermediate activities and send the 2-digit code to the user**.
   * Run the browser wait loop in a background subprocess so the browser stays alive waiting for the user to approve on their mobile app.
   * Once approved, detect and click `"Stay signed in? Yes"` (`#idSIButton9`) and save the resulting `MoodleSession` cookie to `~/.its_classroom/session.json`.
2. **Silent Background Handshake (Auto-Refresh):**
   * Use `launch_persistent_context(user_data_dir=~/.its_classroom/browser_profile)` with headless mode and standard user agent (`Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 ...`).
   * When `MoodleSession` expires, navigate to `https://classroom.its.ac.id/auth/oidc/?source=loginpage` using the persistent profile.
   * **Interpreter & Environment:** Run Playwright via `/home/kuroko/its_classroom_mcp/venv/bin/python` where Playwright and its browser dependencies are installed, or invoke via `uv run --with playwright`.
   * **Pitfall with `networkidle`:** Never use `wait_until='networkidle'` on `page.goto()`! Microsoft Entra ID and `my.its.ac.id/authorize/callback` hold persistent network connections/polling, causing `Timeout 30000ms exceeded`. Always use `wait_until='domcontentloaded', timeout=15000` (wrapped in `try...except`), followed by a loop checking `page.url` until it lands back on `classroom.its.ac.id` outside `/login/` and `/auth/oidc/`.
   * **Exceeded 30 Redirects Diagnostic & Execution Command:** When `classroom_get_course` or Moodle tools fail with `"Exceeded 30 redirects"`, it indicates an expired/invalid `MoodleSession` cookie causing an infinite loop between Moodle login redirect and callback. Immediately run the silent background handshake via the MCP venv interpreter:
     ```bash
     /home/kuroko/its_classroom_mcp/venv/bin/python -c "from its_classroom.auth import refresh_moodle_session_via_sso; print(refresh_moodle_session_via_sso(20))"
     ```
     This captures the fresh cookie from the persistent Chromium profile (`~/.its_classroom/browser_profile/`) and writes it to `~/.its_classroom/session.json` without prompting for MFA.
   * Entra ID will silently validate the KMSI token and redirect back to Classroom, providing a fresh `MoodleSession` tanpa prompting for credentials or MFA.
3. **Anti-Bot & Server Execution Flags:**
   * Pass args: `--disable-blink-features=AutomationControlled`, `--no-sandbox`, `--disable-setuid-sandbox`.
