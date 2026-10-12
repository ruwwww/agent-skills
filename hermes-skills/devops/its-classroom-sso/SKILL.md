---
name: its-classroom-sso
description: Use when managing ITS Classroom MCP or SSO auth.
---

# ITS Classroom SSO & MCP Workflow

Workflow and architecture guide for managing `its_classroom` MCP server, Microsoft Entra ID SSO, and Moodle session handling for ITS (Institut Teknologi Sepuluh Nopember).

## Session Architecture & Lifecycles
* **Microsoft SSO Token (Entra ID KMSI):** Valid for 30–90 days, persisted inside Chromium profile at `~/.its_classroom/browser_profile/`.
* **Moodle Session (`MoodleSession` cookie):** Short-lived (2–4 hours).
* **Silent Auto-Refresh:** When `MoodleSession` expires, `ITSClassroomClient` automatically triggers `refresh_moodle_session_via_sso()` to perform a headless background handshake via the persistent browser profile, fetching a fresh cookie without user interaction.

## Environment & Paths
* **Venv Python:** `/home/kuroko/its_classroom_mcp/venv/bin/python`
* **Source Code:** `/home/kuroko/its_classroom_mcp/src/its_classroom/`
* **Session Storage:** `~/.its_classroom/session.json`
* **Browser Profile:** `~/.its_classroom/browser_profile/`
* **Credentials:** `~/.its_classroom/credentials.json`

## Number Matching MFA Re-Authentication Flow
If the Microsoft SSO token expires after 30–90 days:
1. Trigger fast login script via `fast_trigger.py` (persistent context with anti-bot flags).
2. Extract the 2-digit number match code from `#idRichContext_DisplaySign` or `.display-sign`.
3. Immediately send the 2-digit code to the user to approve in Microsoft Authenticator app.
4. Auto-click "Stay signed in? Yes" and save fresh cookies to `session.json`.

## Common CLI Commands
```bash
# Check current session & student info
/home/kuroko/its_classroom_mcp/venv/bin/python -m its_classroom check

# List courses
/home/kuroko/its_classroom_mcp/venv/bin/python -m its_classroom courses

# List upcoming deadlines
/home/kuroko/its_classroom_mcp/venv/bin/python -m its_classroom deadlines

# View course details (e.g. PSTI: 19519)
/home/kuroko/its_classroom_mcp/venv/bin/python -m its_classroom course 19519
```
