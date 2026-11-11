#!/usr/bin/env node

/**
 * ServiceNow Automation Client (sn_client.js)
 * Helper CLI & library for REST Table API and sys.scripts.do GlideRecord execution.
 */

const fs = require('fs');
const path = require('path');

class ServiceNowClient {
  constructor(instanceUrl, username, password) {
    this.instanceUrl = instanceUrl.replace(/\/$/, '');
    this.username = username;
    this.password = password;
    this.cookies = '';
    this.csrfToken = '';
  }

  get basicAuthHeader() {
    return 'Basic ' + Buffer.from(`${this.username}:${this.password}`).toString('base64');
  }

  async login() {
    const loginBody = new URLSearchParams({
      user_name: this.username,
      user_password: this.password,
      sys_action: 'sysverb_login'
    });

    const res1 = await fetch(`${this.instanceUrl}/login.do`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: loginBody.toString(),
      redirect: 'manual'
    });

    const setCookies1 = res1.headers.getSetCookie();
    const loc = res1.headers.get('location');

    const res2 = await fetch(`${this.instanceUrl}/${loc || ''}`, {
      headers: { 'Cookie': setCookies1.map(c => c.split(';')[0]).join('; ') },
      redirect: 'manual'
    });

    const allCookies = [...setCookies1, ...res2.headers.getSetCookie()].map(c => c.split(';')[0]).join('; ');
    this.cookies = allCookies;

    const html = await res2.text();
    const tokenMatch = html.match(/g_ck\s*=\s*'([^']+)'/);
    if (tokenMatch) {
      this.csrfToken = tokenMatch[1];
    } else {
      throw new Error('Failed to retrieve g_ck CSRF token from ServiceNow session');
    }
  }

  async runBackgroundScript(scriptContent) {
    if (!this.cookies || !this.csrfToken) {
      await this.login();
    }

    const scriptBody = new URLSearchParams({
      script: scriptContent,
      runscript: 'Run script',
      sysparm_ck: this.csrfToken
    });

    const res = await fetch(`${this.instanceUrl}/sys.scripts.do`, {
      method: 'POST',
      headers: {
        'Cookie': this.cookies,
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      body: scriptBody.toString()
    });

    const html = await res.text();
    const preMatch = html.match(/<pre>([\s\S]*?)<\/pre>/i);
    return preMatch ? preMatch[1].trim() : html;
  }

  async queryTable(table, query = '', fields = '', limit = 10) {
    const url = new URL(`${this.instanceUrl}/api/now/table/${table}`);
    if (query) url.searchParams.set('sysparm_query', query);
    if (fields) url.searchParams.set('sysparm_fields', fields);
    url.searchParams.set('sysparm_limit', String(limit));

    const res = await fetch(url.toString(), {
      headers: {
        'Authorization': this.basicAuthHeader,
        'Accept': 'application/json'
      }
    });

    if (!res.ok) {
      const err = await res.text();
      throw new Error(`Table API Error (${res.status}): ${err}`);
    }

    return await res.json();
  }

  async clearHistoryCache(recordSysId) {
    const script = `
var hs = new GlideRecord('sys_history_set');
hs.addQuery('id', '${recordSysId}');
hs.query();
var count = 0;
while (hs.next()) {
  hs.deleteRecord();
  count++;
}
gs.print('CLEARED_CACHE_COUNT: ' + count);
`;
    return await this.runBackgroundScript(script);
  }
}

// CLI Interface
if (require.main === module) {
  const args = process.argv.slice(2);
  const getArg = (name) => {
    const idx = args.indexOf(`--${name}`);
    return idx !== -1 ? args[idx + 1] : process.env[name.toUpperCase()];
  };

  const instance = getArg('instance') || process.env.SN_INSTANCE || 'https://dev353565.service-now.com';
  const user = getArg('user') || process.env.SN_USER || 'admin';
  const pass = getArg('pass') || process.env.SN_PASS || '@FaruqFaruq45';
  const action = getArg('action') || 'help';

  const client = new ServiceNowClient(instance, user, pass);

  (async () => {
    try {
      if (action === 'script') {
        const file = getArg('file');
        const code = file ? fs.readFileSync(path.resolve(file), 'utf8') : getArg('code');
        if (!code) throw new Error('Provide --file or --code for script execution');
        const out = await client.runBackgroundScript(code);
        console.log(out);
      } else if (action === 'query') {
        const table = getArg('table') || 'incident';
        const query = getArg('query') || '';
        const fields = getArg('fields') || '';
        const limit = parseInt(getArg('limit') || '10', 10);
        const res = await client.queryTable(table, query, fields, limit);
        console.log(JSON.stringify(res, null, 2));
      } else if (action === 'clear-cache') {
        const sysId = getArg('sys_id');
        if (!sysId) throw new Error('Provide --sys_id to clear history cache');
        const out = await client.clearHistoryCache(sysId);
        console.log(out);
      } else {
        console.log(`
ServiceNow CLI Helper
Usage:
  node sn_client.js --action script --file <path_to_js>
  node sn_client.js --action query --table incident --query "active=true" --limit 5
  node sn_client.js --action clear-cache --sys_id <record_sys_id>
        `);
      }
    } catch (e) {
      console.error('Error:', e.message);
      process.exit(1);
    }
  })();
}

module.exports = ServiceNowClient;
