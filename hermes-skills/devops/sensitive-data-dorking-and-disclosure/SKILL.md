---
name: sensitive-data-dorking-and-disclosure
description: Dorking sensitive data and drafting responsible disclosure.
---

# Sensitive Data Dorking and Responsible Disclosure

## Overview
Standardized workflow for conducting passive information gathering (Google Dorking / OSINT), verifying real sensitive data exposure (PII, financial, credentials), ensuring deterministic proof-of-concept (PoC) redaction, and preparing structured *Responsible Disclosure* notifications.

## Workflow

### 1. Verification of Findings (Eliminating False Positives)
- **Inspect Live Content:** Never rely solely on search engine snippet text or empty web form templates (e.g. blank input forms, registration stubs, dummy placeholders).
- **Confirm Populated PII:** Ensure the target document/endpoint actually contains unauthenticated, populated sensitive fields (e.g. NIK/National ID, full names, phone numbers, tax filings, salaries, credentials).

### 2. PoC Artifact Creation & Strict Redaction
- **Deterministic Masking:** Mask/redact all high-risk PII elements (names, ID numbers, phone numbers, physical addresses, financial figures, private emails).
- **Target URL Masking:** Redact specific internal IDs/tokens or sensitive path segments in public reports (e.g., `https://target.domain/path/[REDACTED].pdf`).
- **Visual Consistency:** Cross-check image outputs against captions. Never claim an item is redacted if raw values remain visible in the image.

### 4. Integration with Cloud Docs & Composio
- **Google Docs Creation via Composio:** When the user requests the report in Google Docs with placeholders for manual screenshot insertion:
  - Generate the document using `composio execute GOOGLEDOCS_CREATE_DOCUMENT_MARKDOWN` with the connected account (e.g. `googledocs_nace-donald`).
  - Provide clear visual ASCII/block placeholders for screenshots (e.g. `[ PLACEHOLDER TANGKAPAN LAYAR DATA POC ]`) so the user can easily paste screenshots directly into Google Docs.
  - Return the direct Google Docs edit URL to the user.
