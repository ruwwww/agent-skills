# ServiceNow Deep Technical Reference

## 1. Core Tables Reference

| Function / Module | Table Name | Key Fields |
| :--- | :--- | :--- |
| **Users** | `sys_user` | `user_name`, `first_name`, `last_name`, `email`, `user_password`, `active`, `password_needs_reset` |
| **User Roles** | `sys_user_has_role` | `user` (ref: `sys_user`), `role` (ref: `sys_user_role`), `state` |
| **Groups** | `sys_user_group` | `name`, `description`, `manager`, `active` |
| **Group Membership** | `sys_user_grmember` | `user`, `group` |
| **Incidents** | `incident` | `number`, `caller_id`, `cmdb_ci`, `impact`, `urgency`, `priority`, `state`, `assigned_to`, `assignment_group`, `close_code`, `close_notes` |
| **Problems** | `problem` | `number`, `first_reported_by_task`, `cmdb_ci`, `state`, `cause_notes`, `workaround`, `known_error`, `fix_notes`, `resolution_code`, `close_notes` |
| **Change Requests** | `change_request` | `number`, `type`, `parent`, `cmdb_ci`, `state`, `approval`, `justification`, `risk_impact_analysis`, `backout_plan`, `test_plan`, `start_date`, `end_date`, `requested_by`, `opened_by`, `assigned_to`, `assignment_group` |
| **Approvals** | `sysapproval_approver` | `sysapproval` (ref: `task`), `approver` (ref: `sys_user`), `group`, `state` (`requested`, `approved`, `rejected`), `comments` |
| **Affected CIs** | `task_ci` | `task`, `ci_item`, `manually_added` |
| **Impacted Services** | `task_cmdb_ci_service` | `task`, `cmdb_ci_service`, `manually_added` |
| **Journal Fields** | `sys_journal_field` | `name`, `element` (`work_notes`, `comments`), `element_id` (record sys_id), `value`, `sys_created_by` |
| **Audit Log** | `sys_audit` | `tablename`, `documentkey`, `fieldname`, `oldvalue`, `newvalue`, `user` |
| **History Set Cache** | `sys_history_set` | `id` (record sys_id), `table`, `updates` |

---

## 2. GlideRecord Server-Side APIs Cheatsheet

### 1. Bypassing Automatic System Fields (`autoSysFields`)
To update a record without overwriting `sys_updated_by`, `sys_updated_on`, `sys_mod_count`:
```javascript
var gr = new GlideRecord('change_request');
if (gr.get(sysId)) {
  gr.autoSysFields(false); // Disables automatic timestamps and user overrides
  gr.setValue('sys_created_by', 'target.username');
  gr.setValue('sys_updated_by', 'target.username');
  gr.update();
}
```

### 2. Bypassing Workflow & Business Rules (`setWorkflow`)
When you need raw data correction without triggering notifications or validation engines:
```javascript
var gr = new GlideRecord('incident');
if (gr.get(sysId)) {
  gr.setWorkflow(false); // Suppresses Business Rules, Workflows, Flow Designer
  gr.setValue('state', 6);
  gr.update();
}
```

### 3. Setting User Password Safely
Plain text assignment does not work. Use `setDisplayValue`:
```javascript
var userGr = new GlideRecord('sys_user');
if (userGr.get(userSysId)) {
  userGr.setDisplayValue('user_password', 'MySecretPassword123!');
  userGr.password_needs_reset = false;
  userGr.update();
}
```

### 4. Impersonating Users
```javascript
var session = gs.getSession();
var prev = session.impersonate(userSysId);
try {
  // Logic here runs strictly in target user's context
} finally {
  session.impersonate(prev);
}
```

---

## 3. REST Table API URL Query Cheatsheet

### Query Format
`GET /api/now/table/{tableName}?sysparm_query={encodedQuery}&sysparm_fields={fields}&sysparm_limit={limit}`

### Useful Encoded Queries
- Active high priority: `active=true^priority=1`
- By number: `number=INC0010008`
- Multiple sys_ids: `sys_idIN<id1>,<id2>,<id3>`
- Parent problem tasks: `parent=<problem_sys_id>`
- Approvals requested for user: `approver=<user_sys_id>^state=requested`

### Return Display Values & References
To get human-readable labels instead of raw sys_ids:
`sysparm_display_value=all` or `sysparm_display_value=true`
