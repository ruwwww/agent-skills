---
name: servicenow-integration
description: Comprehensive guide, workflows, scripts, and best practices for interacting with ServiceNow instances via REST Table API, Background Scripts (sys.scripts.do), GlideRecord execution, and ServiceNow MCP / NowAIKit. Covers authentication (Basic Auth, OAuth, Session/CSRF), handling security restrictions (glide.authenticate.basic_auth.restriction.enforce), role assignments (snc_basic_auth_api_access), user impersonation (gs.getSession().impersonate), state machines (Incident, Problem, Normal/Standard/Emergency Change), journal fields (sys_journal_field, sys_audit, activity formatter cache clearing), and CMDB/task CI relationships (task_ci, task_cmdb_ci_service). Use when interacting with ServiceNow, querying or updating ServiceNow tables, automating ITSM workflows, debugging ServiceNow API issues, or managing ServiceNow via MCP.
---

# ServiceNow Integration & Automation

Master workflow and technical reference for interacting with ServiceNow instances (Personal Developer Instances / PDIs, enterprise instances, or local containers) through REST Table API, background script execution (`sys.scripts.do`), and ServiceNow Model Context Protocol (MCP / NowAIKit).

---

## 1. Interaction Modes: Which Tool to Use When

| Goal / Task | Best Mechanism | Why / Caveat |
| :--- | :--- | :--- |
| **Read records / filter data** | Table API (`/api/now/table/...`) or MCP `query_records` | Fast, returns clean JSON, supports `sysparm_fields`, pagination, and encoded queries. |
| **Simple field updates** | Table API (`PATCH`) or MCP `update_record` | Clean for standard fields. Fails if target state violates state transition models. |
| **User password setting** | Server-side script (`sys.scripts.do`) | REST API does **not** hash plaintext into the two-way digest; must use `GlideRecord.setDisplayValue('user_password', ...)`. |
| **State transitions with business logic** | Server-side script or UI action trigger | Avoids data policy blocks (e.g. Problem state machine requiring `fix_notes`, or CAB approval rules). |
| **User impersonation** | Server-side script (`gs.getSession().impersonate(...)`) | Guarantees audit trails (`sys_audit`), work notes author, and approval updates reflect the assigned agent or user. |
| **Affected / Impacted CIs (`task_ci`)** | Server-side script (`task_ci` / `task_cmdb_ci_service`) | REST API frequently throws 403 Forbidden due to ACLs on related list tables; GlideRecord inserts succeed reliably. |
| **Activity Stream / Cache Fixes** | Server-side script (`sys_history_set`) | Deleting cached `sys_history_set` forces the Activity Formatter to rebuild clean logs from `sys_audit`. |

---

## 2. Authentication & Security Configuration

### Basic Auth 401 Unauthorized in Modern Releases (Xanadu / Washington DC)
In modern ServiceNow releases, `glide.authenticate.basic_auth.restriction.enforce` is enabled by default. REST calls with basic credentials will fail with `401 Unauthorized` unless:
1. The user has the **`snc_basic_auth_api_access`** role assigned:
   ```javascript
   var gr = new GlideRecord('sys_user_has_role');
   gr.initialize();
   gr.user = userSysId;
   gr.role = 'f74577f10a0a0b2700e3184f47565c4f'; // snc_basic_auth_api_access sys_id
   gr.insert();
   ```
2. Or the system property `glide.authenticate.basic_auth.restriction.enforce` is set to `false`.

### Password Setting for New Users
Always set passwords on `sys_user` records using GlideRecord:
```javascript
var u = new GlideRecord('sys_user');
if (u.get(userSysId)) {
  u.setDisplayValue('user_password', 'DesiredPassword123!');
  u.password_needs_reset = false; // prevents login redirection loop
  u.update();
}
```

---

## 3. Background Script Bridge (`sys.scripts.do`)

When Table API is blocked by ACLs or strict UI Policies, execute raw GlideRecord JavaScript via the background script endpoint:

### Execution Pattern (Node.js)
```javascript
const instanceUrl = 'https://devXXXXX.service-now.com';

// 1. Authenticate web session
const loginRes = await fetch(`${instanceUrl}/login.do`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  body: new URLSearchParams({
    user_name: 'admin',
    user_password: 'YourPassword',
    sys_action: 'sysverb_login'
  }).toString(),
  redirect: 'manual'
});

const cookies = loginRes.headers.getSetCookie();
const loc = loginRes.headers.get('location');
const navRes = await fetch(`${instanceUrl}/${loc || ''}`, {
  headers: { 'Cookie': cookies.map(c => c.split(';')[0]).join('; ') },
  redirect: 'manual'
});

const allCookies = [...cookies, ...navRes.headers.getSetCookie()].map(c => c.split(';')[0]).join('; ');
const html = await navRes.text();
const tokenMatch = html.match(/g_ck\s*=\s*'([^']+)'/); // CSRF token

// 2. POST to sys.scripts.do with sysparm_ck
const resScript = await fetch(`${instanceUrl}/sys.scripts.do`, {
  method: 'POST',
  headers: {
    'Cookie': allCookies,
    'Content-Type': 'application/x-www-form-urlencoded'
  },
  body: new URLSearchParams({
    script: 'gs.print("Hello from ServiceNow!");',
    runscript: 'Run script',
    sysparm_ck: tokenMatch[1]
  }).toString()
});

const responseHtml = await resScript.text();
const preMatch = responseHtml.match(/<pre>([\s\S]*?)<\/pre>/i);
console.log(preMatch ? preMatch[1].trim() : 'Executed');
```

---

## 4. User Impersonation in Background Scripts

To run logic, trigger approvals, or write audit trails on behalf of a specific user:

```javascript
var targetUserSysId = '0e48e26c936c57502adbf24cdd03d600'; // e.g. Faisal Rahman

// Impersonate
var prevUser = gs.getSession().impersonate(targetUserSysId);
gs.print('Active user context: ' + gs.getUserName() + ' (' + gs.getUserDisplayName() + ')');

// Perform actions (all sys_updated_by and journal fields will log as targetUser)
var chg = new GlideRecord('change_request');
if (chg.get(changeSysId)) {
  chg.work_notes = 'Testing performed and verified successfully.';
  chg.update();
}

// Restore admin context
gs.getSession().impersonate(prevUser);
```

---

## 5. State Machine Lifecycles & Field Requirements

### Incident Management (`incident`)
| State Value | State Label | Mandatory Fields / Conditions |
| :---: | :--- | :--- |
| `1` | New | `caller_id`, `short_description` |
| `2` | In Progress | `assigned_to` |
| `3` | On Hold | `on_hold_reason` |
| `6` | Resolved | `close_code`, `close_notes`, `resolved_by`, `resolved_at` |
| `7` | Closed | Auto-closed by system or manual close |

### Problem Management (`problem`)
| State Value | State Label | Transition Rules & Mandatory Fields |
| :---: | :--- | :--- |
| `101` | New | Initial report |
| `102` | Assess | Confirming problem impact |
| `103` | Root Cause Analysis | 5 Whys, `cause_notes`, workaround |
| `104` | Fix in Progress | **Requires `fix_notes`** before transitioning |
| `106` | Resolved | **Requires `resolution_code`** (e.g. `fix_applied`) and `close_notes` |
| `107` | Closed | Mark completed |

### Change Management (`change_request` - Normal Change)
| State Value | State Label | Approval / Transition Requirements |
| :---: | :--- | :--- |
| `-5` | New | Fill Planning (justification, risk, backout, test) & Schedule |
| `-4` | Assess | Click "Request Approval" -> Technical / Peer approval in `sysapproval_approver` |
| `-3` | Authorize | Technical approved -> CAB Group approval requested in `sysapproval_approver` |
| `-2` | Scheduled | CAB approved with comments -> Ready for implementation window |
| `-1` | Implement | Work start recorded |
| `0` | Review | Work end recorded, post-implementation validation notes added |
| `3` | Closed | `close_code` = `successful`, `close_notes` populated |

---

## 6. Journal Fields, Audit Logs & Activity Stream Cache

### Fixing Author Attribution on Work Notes
Work notes are stored in `sys_journal_field` with matching entries in `sys_audit`:
```javascript
// 1. Update sys_journal_field
var jf = new GlideRecord('sys_journal_field');
jf.addQuery('element_id', recordSysId);
jf.addQuery('element', 'work_notes');
jf.query();
while (jf.next()) {
  jf.autoSysFields(false);
  jf.setValue('sys_created_by', 'correct.username');
  jf.update();
}

// 2. Update sys_audit
var audit = new GlideRecord('sys_audit');
audit.addQuery('documentkey', recordSysId);
audit.query();
while (audit.next()) {
  if (audit.getValue('user') === 'admin') {
    audit.autoSysFields(false);
    audit.setValue('user', 'correct.username');
    audit.update();
  }
}
```

### Busting the Activity Stream Cache
ServiceNow caches the rendered Activity stream in `sys_history_set`. If edited notes still display the old author:
```javascript
var hs = new GlideRecord('sys_history_set');
hs.addQuery('id', recordSysId);
hs.query();
while (hs.next()) {
  hs.deleteRecord(); // Forces dynamic rebuild on next page view
}
```

---

## 7. CMDB & Task CI Relationships

### Adding Affected CIs
Table: `task_ci`
```javascript
var gr = new GlideRecord('task_ci');
gr.initialize();
gr.task = taskSysId;
gr.ci_item = ciSysId;
gr.manually_added = true;
gr.insert();
```

### Adding Impacted Services / CIs
Table: `task_cmdb_ci_service`
```javascript
var gr = new GlideRecord('task_cmdb_ci_service');
gr.initialize();
gr.task = taskSysId;
gr.cmdb_ci_service = serviceCiSysId;
gr.manually_added = true;
gr.insert();
```

---

## 8. Bundled Helper Scripts

Use the pre-packaged Node.js helper in `scripts/sn_client.js`:

```bash
# Run raw background script
node scripts/sn_client.js --action script --file my_script.js

# Query table
node scripts/sn_client.js --action query --table incident --query "active=true^priority=1"

# Clear history cache for a record
node scripts/sn_client.js --action clear-cache --table change_request --sys_id <SYS_ID>
```

For full reference on schemas and GlideRecord APIs, see [REFERENCE.md](REFERENCE.md).
