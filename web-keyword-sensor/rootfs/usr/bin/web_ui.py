#!/usr/bin/env python3
"""Ingress UI, persistent check store, and interactive browser authentication."""
import base64
import json
import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

PATH = Path("/data/checks.json")
AUTH_DIR = Path("/data/browser-auth")
HTML = '''<!doctype html>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Web Keyword Sensor</title>
<style>
body{font:16px system-ui;max-width:900px;margin:2em auto;padding:0 1em;background:#fafafa;color:#263238}
.card{background:white;border:1px solid #ddd;border-radius:8px;padding:1em;margin:1em 0}
form{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px}
label{display:flex;flex-direction:column;gap:4px;font-weight:600}input,select,button{font:inherit;padding:8px}
button{background:#1976d2;color:#fff;border:0;border-radius:4px;cursor:pointer}.delete{background:#c62828}
.days{grid-column:1/-1;display:flex;flex-wrap:wrap;gap:10px}.days label{display:block;font-weight:400}
.browser{grid-column:1/-1;border-top:1px solid #ddd;padding-top:12px}.browser img{display:block;max-width:100%;border:1px solid #777;margin-top:8px}
.hidden{display:none}.auth-failure{color:#c62828;font-weight:700}
</style>
<h1>Web Keyword Sensor</h1>
<p>Manage page checks. Changes are saved immediately.</p><div id="list"></div>
<div class="card"><h2 id="heading">Add check</h2><form id="form">
<input id="id" type="hidden"><label>Name<input id="name" required></label>
<label>URL<input id="url" type="url" required></label><label>Phrase<input id="phrase" required></label>
<label>Entity type<select id="entity_type"><option value="binary_sensor">Binary sensor</option><option value="sensor">Sensor</option></select></label>
<label>Interval<input id="interval" type="number" min="1" max="31536000" value="15" required></label>
<label>Unit<select id="unit"><option>seconds</option><option selected>minutes</option><option>hours</option><option>days</option><option>weeks</option></select></label>
<label>From<select id="time_from"></select></label><label>To<select id="time_to"></select></label>
<div class="days"><b>Days:</b><label><input class="day" value="monday" type="checkbox" checked> Mon</label>
<label><input class="day" value="tuesday" type="checkbox" checked> Tue</label><label><input class="day" value="wednesday" type="checkbox" checked> Wed</label>
<label><input class="day" value="thursday" type="checkbox" checked> Thu</label><label><input class="day" value="friday" type="checkbox" checked> Fri</label>
<label><input class="day" value="saturday" type="checkbox" checked> Sat</label><label><input class="day" value="sunday" type="checkbox" checked> Sun</label></div>
<label>Login URL (optional)<input id="login_url" type="url"></label>
<label>Auth mode<select id="auth_mode"><option value="basic">Username/password/TOTP</option><option value="browser">Browser SSO</option></select></label>
<label>Username<input id="username" autocomplete="username"></label><label>Password<input id="password" type="password" autocomplete="current-password"></label>
<label>TOTP secret<input id="totp_secret" type="password" placeholder="Optional"></label><label>Username field<input id="username_field" value="username"></label>
<label>Password field<input id="password_field" value="password"></label><label>TOTP field<input id="totp_field" value="totp"></label>
<label>Login success text<input id="success_text"></label><label><input id="case_sensitive" type="checkbox"> Case sensitive</label>
<label><input id="verify_ssl" type="checkbox" checked> Verify TLS</label><label><input id="enabled" type="checkbox" checked> Enabled</label>
<div><button type="submit">Save check</button> <button type="button" id="cancel" onclick="reset()" hidden>Cancel</button></div>
<div id="browser" class="browser hidden"><b>Browser SSO</b><p>Start the browser, then complete the provider login in the screenshot below.</p>
<button type="button" onclick="startBrowser()">Start browser</button> <button type="button" onclick="browserAction('finish')">Finish authentication</button>
<input id="browser_text" placeholder="Text to type"><button type="button" onclick="typeBrowser()">Type</button>
<p>Click the screenshot to click the remote page.</p><img id="browser_image" alt="Browser login screenshot"></div>
</form></div>
<script>
const ids=['name','url','phrase','entity_type','interval','unit','time_from','time_to','login_url','auth_mode','username_field','password_field','totp_field','success_text','case_sensitive','verify_ssl','enabled'];
const $=x=>document.getElementById(x);let browserSession='';
const esc=x=>String(x).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
for(const id of ['time_from','time_to'])for(let h=0;h<24;h++){let o=document.createElement('option');o.value=String(h).padStart(2,'0')+':00';o.textContent=o.value;$(id).append(o)}
function showBrowser(){$('browser').classList.toggle('hidden',$('auth_mode').value!=='browser')}
$('auth_mode').onchange=showBrowser;
async function load(){const r=await fetch('./api/checks');const x=await r.json();$('list').innerHTML=x.map(c=>`<div class="card"><h2>${esc(c.name)}</h2><p>${esc(c.entity_type)} · every ${c.interval} ${esc(c.unit)} · ${esc(c.time_from||'00:00')}–${esc(c.time_to||'23:00')} · ${c.enabled?'enabled':'disabled'}</p><p>${esc(c.phrase)}<br>${esc(c.url)}<br>${c.auth_mode==='browser'?'Browser SSO':'Basic login'} · <span class="${String(c.auth_status||'').startsWith('Authentication failed')?'auth-failure':''}">${esc(c.auth_status||'Not tested')}</span></p><button onclick='edit(${JSON.stringify(c)})'>Edit</button> <button class="delete" onclick='del("${esc(c.id)}")'>Delete</button></div>`).join('')||'<p>No checks configured.</p>'}
function edit(c){$('id').value=c.id;ids.forEach(k=>$(k)[$(k).type==='checkbox'?'checked':'value']=c[k]??$(k).value);$('username').value='';$('password').value='';$('totp_secret').value='';document.querySelectorAll('.day').forEach(x=>x.checked=(c.days||[]).includes(x.value));$('heading').textContent='Edit check';$('cancel').hidden=false;showBrowser();scrollTo(0,document.body.scrollHeight)}
function reset(){$('form').reset();$('id').value='';$('time_from').value='00:00';$('time_to').value='23:00';$('auth_mode').value='basic';document.querySelectorAll('.day').forEach(x=>x.checked=true);$('heading').textContent='Add check';$('cancel').hidden=true;showBrowser()}
async function del(id){if(confirm('Delete this check?')){await fetch('./api/checks/'+encodeURIComponent(id),{method:'DELETE'});load()}}
$('form').onsubmit=async e=>{e.preventDefault();let c=Object.fromEntries(ids.map(k=>[k,$(k).type==='checkbox'?$(k).checked:$(k).value]));c.id=$('id').value||undefined;c.username=$('username').value;c.password=$('password').value;c.totp_secret=$('totp_secret').value;c.days=[...document.querySelectorAll('.day:checked')].map(x=>x.value);let saved=await (await fetch('./api/checks',{method:c.id?'PUT':'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(c)})).json();if(c.auth_mode==='browser'&&c.login_url){edit(saved);$('id').value=saved.id;$('auth_mode').value='browser';showBrowser()}else reset();load()};
async function browserAction(action,body={}){if(!browserSession)return alert('Start the browser first');let r=await fetch('./api/auth/'+browserSession+'/'+action,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});let x=await r.json();if(!r.ok)return alert(x.error||'Browser action failed');if(x.image)$('browser_image').src='data:image/png;base64,'+x.image;load()}
async function startBrowser(){let r=await fetch('./api/auth/start',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:$('id').value})});let x=await r.json();if(!r.ok)return alert(x.error||'Unable to start browser');browserSession=x.session;$('browser_image').src='data:image/png;base64,'+x.image}
function typeBrowser(){browserAction('type',{text:$('browser_text').value})}
$('browser_image').onclick=e=>{let r=$('browser_image').getBoundingClientRect();browserAction('click',{x:e.clientX-r.left,y:e.clientY-r.top,scale:$('browser_image').naturalWidth/r.width})};reset();load();
</script>'''

class CheckStore:
    def __init__(self, initial):
        os.umask(0o077)
        self.lock = threading.RLock()
        try: self.checks = json.loads(PATH.read_text())
        except (FileNotFoundError, OSError, json.JSONDecodeError): self.checks = initial; self.save()
    def save(self): PATH.write_text(json.dumps(self.checks, indent=2) + "\n"); PATH.chmod(0o600)
    def get(self):
        with self.lock:
            result = []
            for check in self.checks:
                item = dict(check); item["login_configured"] = bool(item.get("username") and item.get("password"))
                item["username"] = item.get("username", ""); item["password"] = ""; item["totp_secret"] = ""; result.append(item)
            return result
    def get_runtime(self):
        with self.lock: return [dict(x) for x in self.checks]
    def put(self, check):
        with self.lock:
            check.setdefault("id", uuid.uuid4().hex)
            old = next((x for x in self.checks if x.get("id") == check.get("id")), {})
            for secret in ("username", "password", "totp_secret"):
                if not check.get(secret): check[secret] = old.get(secret, "")
            self.checks = [check if x.get("id") == check.get("id") else x for x in self.checks]
            if not any(x.get("id") == check.get("id") for x in self.checks): self.checks.append(check)
            self.save()
    def delete(self, ident):
        with self.lock: self.checks = [x for x in self.checks if x.get("id") != ident]; self.save()

class BrowserSessions:
    def __init__(self, store): self.store, self.sessions, self.authenticated, self.lock, self.executor = store, {}, {}, threading.RLock(), ThreadPoolExecutor(max_workers=1, thread_name_prefix="playwright")
    def start(self, ident): return self.executor.submit(self._start, ident).result()
    def _start(self, ident):
        check = next((x for x in self.store.get_runtime() if x.get("id") == ident), None)
        if not check or check.get("auth_mode") != "browser" or not check.get("login_url"): raise ValueError("Save a browser SSO check with a login URL first")
        try:
            from playwright.sync_api import sync_playwright
            pw = sync_playwright().start(); browser = pw.chromium.launch(headless=True, executable_path=next((p for p in ("/usr/bin/chromium", "/usr/bin/chromium-browser") if os.path.exists(p)), None))
        except Exception as error: raise RuntimeError("Playwright/Chromium is unavailable: %s" % error) from error
        state_path = AUTH_DIR / f"{ident}.json"
        context = browser.new_context(storage_state=str(state_path) if state_path.exists() else None, ignore_https_errors=not check.get("verify_ssl", True))
        page = context.new_page(); page.goto(check["login_url"], wait_until="domcontentloaded", timeout=30000)
        sid = uuid.uuid4().hex; session = {"pw": pw, "browser": browser, "page": page, "check": check, "lock": threading.RLock(), "expires": time.time() + 900}
        with self.lock: self.sessions[sid] = session
        return sid, self.image(session)
    @staticmethod
    def image(session): return base64.b64encode(session["page"].screenshot(type="png")).decode()
    def get(self, sid):
        with self.lock:
            session = self.sessions.get(sid)
            if not session or session["expires"] < time.time(): raise ValueError("Browser session expired")
            session["expires"] = time.time() + 900; return session
    def close(self, sid):
        with self.lock: session = self.sessions.pop(sid, None)
        if session: session["browser"].close(); session["pw"].stop()
    def finish(self, sid): return self.executor.submit(self._finish, sid).result()
    def _finish(self, sid):
        session = self.get(sid)
        with session["lock"]:
            response = session["page"].goto(session["check"]["url"], wait_until="domcontentloaded", timeout=30000)
            if response and response.status >= 400: raise ValueError("browser login rejected (HTTP %s)" % response.status)
            success_text = session["check"].get("success_text")
            if success_text and success_text not in session["page"].content(): raise ValueError("browser login success text was not found")
            AUTH_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
            state_path = AUTH_DIR / f"{session['check']['id']}.json"
            session["page"].context.storage_state(path=str(state_path)); state_path.chmod(0o600)
            session["check"]["auth_status"] = "Browser SSO successful"; self.store.put(session["check"])
            with self.lock: self.authenticated[session["check"]["id"]] = session
            return self.image(session)
    def fetch(self, check): return self.executor.submit(self._fetch, check).result()
    def _fetch(self, check):
        with self.lock: session = self.authenticated.get(check.get("id"))
        if not session:
            state_path = AUTH_DIR / f"{check.get('id')}.json"
            if not state_path.exists(): raise ValueError("browser SSO has not been completed")
            sid, _ = self._start(check.get("id"))
            with self.lock: session = self.sessions[sid]
            with self.lock: self.authenticated[check.get("id")] = session
        with session["lock"]:
            response = session["page"].goto(check["url"], wait_until="domcontentloaded", timeout=30000)
            if not response: raise ValueError("browser did not return a response")
            return response.status, session["page"].content()
    def action(self, sid, action, data): return self.executor.submit(self._action, sid, action, data).result()
    def _action(self, sid, action, data):
        session = self.get(sid)
        with session["lock"]:
            if action == "click":
                scale = float(data.get("scale", 1)); session["page"].mouse.click(float(data["x"]) * scale, float(data["y"]) * scale)
            elif action == "type": session["page"].keyboard.type(str(data.get("text", "")))
            elif action == "finish": return self._finish(sid)
            else: raise ValueError("Unknown browser action")
            return self.image(session)

def notify_auth_failure(check, reason):
    check["auth_status"] = "Authentication failed: " + str(reason)
    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token: return
    try:
        import requests
        requests.post("http://supervisor/core/api/services/persistent_notification/create", headers={"Authorization": "Bearer " + token}, json={"title": "Web Keyword Sensor authentication failure", "message": "Authentication failed for %s: %s" % (check.get("name", "unnamed"), reason)}, timeout=10)
    except Exception: pass

def start_server(store, browser_sessions=None):
    if browser_sessions is None: browser_sessions = BrowserSessions(store)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args): pass
        def body(self): return json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        def reply(self, value, status=200):
            data = json.dumps(value).encode(); self.send_response(status); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
        def error(self, message, status=400): self.reply({"error": str(message)}, status)
        def do_GET(self):
            path = urlparse(self.path).path
            if path in ("/", ""):
                data = HTML.encode(); self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
            elif path == "/api/checks": self.reply(store.get())
            else: self.send_error(404)
        def do_POST(self):
            path = urlparse(self.path).path
            try:
                if path == "/api/checks": check = self.body(); store.put(check); self.reply(check, 201); return
                if path == "/api/auth/start": sid, image = browser_sessions.start(self.body().get("id")); self.reply({"session": sid, "image": image}); return
                parts = path.split("/")
                if len(parts) == 5 and parts[1:3] == ["api", "auth"]:
                    action = parts[4]; image = browser_sessions.action(unquote(parts[3]), action, self.body()); self.reply({"ok": True, "image": image}); return
                self.send_error(404)
            except Exception as error:
                if path.startswith("/api/auth/"):
                    parts = path.split("/")
                    session = browser_sessions.sessions.get(unquote(parts[3])) if len(parts) > 3 else None
                    ident = session["check"].get("id") if session else None
                    if ident:
                        check = next((x for x in store.get_runtime() if x.get("id") == ident), None)
                        if check: notify_auth_failure(check, error); store.put(check)
                self.error(error)
        def do_PUT(self):
            if urlparse(self.path).path != "/api/checks": self.send_error(404); return
            try: check = self.body(); store.put(check); self.reply(check)
            except (ValueError, TypeError): self.send_error(400)
        def do_DELETE(self):
            prefix = "/api/checks/"; path = urlparse(self.path).path
            if not path.startswith(prefix): self.send_error(404); return
            store.delete(unquote(path[len(prefix):])); self.reply({"ok": True})
    server = ThreadingHTTPServer(("0.0.0.0", 8099), Handler); threading.Thread(target=server.serve_forever, name="web-ui", daemon=True).start(); return server
