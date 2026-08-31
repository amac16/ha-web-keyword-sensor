#!/usr/bin/env python3
"""Ingress UI, persistent check store, and interactive browser authentication."""
import base64
import asyncio
import json
import logging
import os
import re
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

LOG = logging.getLogger("web_keyword_sensor.ui")

PATH = Path("/data/checks.json")
AI_PATH = Path("/data/ai-profiles.json")
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
<div class="card"><h2>AI model integrations</h2><p>Keys are stored only in protected app storage. AI checks send page text to the selected provider.</p><div id="profiles"></div><form id="profile_form"><input id="profile_id" type="hidden"><label>Name<input id="profile_name" required></label><label>Provider<select id="profile_provider"><option value="openai">OpenAI</option><option value="google">Google Gemini</option><option value="anthropic">Anthropic Claude</option></select></label><label>Model ID<input id="profile_model" placeholder="e.g. gpt-4.1-mini" required></label><label>API key<input id="profile_key" type="password" autocomplete="new-password"><small>Required for new profiles; leave blank when editing to preserve the key.</small></label><button>Save AI profile</button> <button type="button" id="test_profile" onclick="testProfile()">Test provider</button> <span id="profile_test_status"></span></form></div>
<div class="card"><h2 id="heading">Add check</h2><form id="form">
<input id="id" type="hidden"><label>Name<input id="name" required></label>
<label>URL<input id="url" type="url" required></label><label>Phrase (exact mode)<input id="phrase"></label>
<label>Entity type<select id="entity_type"><option value="binary_sensor">Binary sensor</option><option value="sensor">Sensor</option></select></label>
<label>Match mode<select id="match_mode"><option value="literal">Exact phrase</option><option value="ai_context">AI context match</option></select></label>
<label class="context hidden">AI model<select id="ai_profile_id"></select></label><label class="context hidden" style="grid-column:1/-1">What to look for<textarea id="context_prompt" rows="4" placeholder="Describe the information you want found on this page..."></textarea></label>
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
const ids=['name','url','phrase','entity_type','match_mode','ai_profile_id','context_prompt','interval','unit','time_from','time_to','login_url','auth_mode','username_field','password_field','totp_field','success_text','case_sensitive','verify_ssl','enabled'];
const $=x=>document.getElementById(x);let browserSession='',checkCache={};
const esc=x=>String(x).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
for(const id of ['time_from','time_to'])for(let h=0;h<24;h++){let o=document.createElement('option');o.value=String(h).padStart(2,'0')+':00';o.textContent=o.value;$(id).append(o)}
function showBrowser(){$('browser').classList.toggle('hidden',$('auth_mode').value!=='browser')}
$('auth_mode').onchange=showBrowser;
function showContext(){document.querySelectorAll('.context').forEach(x=>x.classList.toggle('hidden',$('match_mode').value!=='ai_context'))}
$('match_mode').onchange=showContext;
async function loadProfiles(){const x=await (await fetch('./api/ai-profiles')).json();$('ai_profile_id').innerHTML=x.filter(p=>p.enabled).map(p=>`<option value="${esc(p.id)}">${esc(p.name)} (${esc(p.provider)} / ${esc(p.model)})</option>`).join('')||'<option value="">No enabled AI profiles</option>';$('profiles').innerHTML=x.map(p=>`<p>${esc(p.name)} · ${esc(p.provider)} / ${esc(p.model)} · ${p.api_key_configured?'key configured':'missing key'} <button type="button" onclick='editProfile(${JSON.stringify(p)})'>Edit</button> <button type="button" class="delete" onclick='delProfile("${esc(p.id)}")'>Delete</button></p>`).join('')||'<p>No profiles configured.</p>';showContext()}
function editProfile(p){$('profile_id').value=p.id;$('profile_name').value=p.name;$('profile_provider').value=p.provider;$('profile_model').value=p.model;$('profile_key').value='';scrollTo(0,0)}
async function load(){const r=await fetch('./api/checks');const x=await r.json();checkCache=Object.fromEntries(x.map(c=>[c.id,c]));$('list').innerHTML=x.map(c=>`<div class="card"><h2>${esc(c.name)}</h2><p>${esc(c.entity_type)} · ${c.match_mode==='ai_context'?'AI context':'exact phrase'} · every ${c.interval} ${esc(c.unit)} · ${c.enabled?'enabled':'disabled'}</p><p>${esc(c.context_prompt||c.phrase)}<br>${esc(c.url)}<br><span class="${String(c.auth_status||'').startsWith('Authentication failed')?'auth-failure':''}">${esc(c.auth_status||'Not tested')}</span></p><button class="edit-check" data-id="${esc(c.id)}">Edit</button> <button class="test-check" data-id="${esc(c.id)}">Test</button> <button class="delete delete-check" data-id="${esc(c.id)}">Delete</button><p class="test-result" id="test-${esc(c.id)}"></p></div>`).join('')||'<p>No checks configured.</p>';document.querySelectorAll('.edit-check').forEach(b=>b.onclick=()=>edit(checkCache[b.dataset.id]));document.querySelectorAll('.test-check').forEach(b=>b.onclick=()=>testCheck(b,b.dataset.id));document.querySelectorAll('.delete-check').forEach(b=>b.onclick=()=>del(b.dataset.id));loadProfiles()}
async function testCheck(button,id){button.disabled=true;let out=$('test-'+id);out.textContent='Running...';try{let r=await fetch('./api/checks/'+encodeURIComponent(id)+'/test',{method:'POST'});let x=await r.json();if(x.ok){out.textContent='Result: state='+x.state+' · matched='+x.attributes.matched}else out.textContent='Test failed: '+(x.error||'unknown error')}catch(e){out.textContent='Test failed: request error'}finally{button.disabled=false}}
function edit(c){$('id').value=c.id;ids.forEach(k=>$(k)[$(k).type==='checkbox'?'checked':'value']=c[k]??$(k).value);$('username').value='';$('password').value='';$('totp_secret').value='';document.querySelectorAll('.day').forEach(x=>x.checked=(c.days||[]).includes(x.value));$('heading').textContent='Edit check';$('cancel').hidden=false;showBrowser();showContext();scrollTo(0,document.body.scrollHeight)}
function reset(){$('form').reset();$('id').value='';$('time_from').value='00:00';$('time_to').value='23:00';$('auth_mode').value='basic';$('match_mode').value='literal';document.querySelectorAll('.day').forEach(x=>x.checked=true);$('heading').textContent='Add check';$('cancel').hidden=true;showBrowser();showContext()}
async function del(id){if(confirm('Delete this check?')){await fetch('./api/checks/'+encodeURIComponent(id),{method:'DELETE'});load()}}
async function delProfile(id){if(confirm('Delete this AI profile?')){await fetch('./api/ai-profiles/'+encodeURIComponent(id),{method:'DELETE'});loadProfiles()}}
async function testProfile(){let b=$('test_profile');b.disabled=true;$('profile_test_status').textContent='Testing...';let p={id:$('profile_id').value||undefined,name:$('profile_name').value,provider:$('profile_provider').value,model:$('profile_model').value,api_key:$('profile_key').value};try{let r=await fetch('./api/ai-profiles/test',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(p)});let x=await r.json();$('profile_test_status').textContent=r.ok?'Provider responded successfully':(x.error||'Provider test failed')}catch(e){$('profile_test_status').textContent='Provider test failed'}finally{b.disabled=false}}
$('profile_form').onsubmit=async e=>{e.preventDefault();let p={id:$('profile_id').value||undefined,name:$('profile_name').value,provider:$('profile_provider').value,model:$('profile_model').value,api_key:$('profile_key').value};let r=await fetch('./api/ai-profiles',{method:p.id?'PUT':'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(p)});let x=await r.json();if(!r.ok)return alert(x.error||'Unable to save profile');$('profile_form').reset();loadProfiles()}
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
    def save(self):
        temporary = PATH.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(self.checks, indent=2) + "\n", encoding="utf-8")
        temporary.chmod(0o600)
        os.replace(temporary, PATH)
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
            if not isinstance(check, dict): raise ValueError("check must be an object")
            check.setdefault("id", uuid.uuid4().hex)
            old = next((x for x in self.checks if x.get("id") == check.get("id")), {})
            for secret in ("username", "password", "totp_secret"):
                if not check.get(secret): check[secret] = old.get(secret, "")
            if not check.get("name") or not check.get("url") or (not check.get("phrase") and not (check.get("match_mode") == "ai_context" and check.get("context_prompt"))):
                raise ValueError("name, URL, and phrase or AI request are required")
            replacing = any(x.get("id") == check.get("id") for x in self.checks)
            if not replacing and len(self.checks) >= 100: raise ValueError("maximum of 100 checks reached")
            self.checks = [check if x.get("id") == check.get("id") else x for x in self.checks]
            if not replacing: self.checks.append(check)
            self.save()
    def delete(self, ident):
        with self.lock: self.checks = [x for x in self.checks if x.get("id") != ident]; self.save()


class AIProfileStore:
    PROVIDERS = ("openai", "google", "anthropic")
    def __init__(self):
        self.lock = threading.RLock()
        try: self.profiles = json.loads(AI_PATH.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, json.JSONDecodeError): self.profiles = []
        if not isinstance(self.profiles, list): self.profiles = []
        if AI_PATH.exists(): AI_PATH.chmod(0o600)
    def save(self):
        temporary = AI_PATH.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(self.profiles, indent=2) + "\n", encoding="utf-8")
        temporary.chmod(0o600); os.replace(temporary, AI_PATH)
    def get_runtime(self):
        with self.lock: return [dict(x) for x in self.profiles]
    def get_public(self):
        with self.lock:
            return [{"id": x.get("id"), "name": x.get("name", x.get("id", "")), "provider": x.get("provider"), "model": x.get("model"), "enabled": x.get("enabled", True), "api_key_configured": bool(x.get("api_key"))} for x in self.profiles]
    def for_test(self, profile):
        if not isinstance(profile, dict): raise ValueError("profile must be an object")
        with self.lock:
            candidate = dict(profile)
            old = next((x for x in self.profiles if x.get("id") == candidate.get("id")), {})
            if not candidate.get("api_key"): candidate["api_key"] = old.get("api_key", "")
        provider = str(candidate.get("provider", "")).lower()
        if provider not in self.PROVIDERS: raise ValueError("unsupported AI provider")
        if not candidate.get("model"): raise ValueError("model is required")
        if not candidate.get("api_key"): raise ValueError("API key is required")
        candidate["provider"] = provider
        return candidate
    def put(self, profile):
        if not isinstance(profile, dict): raise ValueError("profile must be an object")
        with self.lock:
            ident = str(profile.get("id", "")).strip() or uuid.uuid4().hex
            if not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", ident): raise ValueError("profile ID must use letters, numbers, _ or -")
            provider = str(profile.get("provider", "")).lower()
            if provider not in self.PROVIDERS: raise ValueError("unsupported AI provider")
            model = str(profile.get("model", "")).strip()
            if not model or len(model) > 128: raise ValueError("model is required")
            old = next((x for x in self.profiles if x.get("id") == ident), {})
            profile = dict(profile); profile["id"] = ident; profile["provider"] = provider; profile["model"] = model
            if not profile.get("api_key"): profile["api_key"] = old.get("api_key", "")
            if not profile["api_key"]: raise ValueError("API key is required")
            profile["name"] = str(profile.get("name") or ident)[:80]
            profile["enabled"] = bool(profile.get("enabled", True))
            profile["endpoint"] = str(profile.get("endpoint", ""))[:256]
            replacing = any(x.get("id") == ident for x in self.profiles)
            if not replacing and len(self.profiles) >= 20: raise ValueError("maximum of 20 AI profiles reached")
            self.profiles = [profile if x.get("id") == ident else x for x in self.profiles]
            if not replacing: self.profiles.append(profile)
            self.save(); return profile
    def delete(self, ident):
        with self.lock: self.profiles = [x for x in self.profiles if x.get("id") != ident]; self.save()

class BrowserSessions:
    def __init__(self, store):
        self.store, self.sessions, self.authenticated, self.lock = store, {}, {}, threading.RLock()
        self.loop = asyncio.new_event_loop()
        self.loop_thread = threading.Thread(target=self.loop.run_forever, name="playwright-async", daemon=True)
        self.loop_thread.start()

    def _run(self, coroutine, timeout=60):
        future = asyncio.run_coroutine_threadsafe(coroutine, self.loop)
        try:
            return future.result(timeout=timeout)
        except TimeoutError:
            future.cancel()
            raise RuntimeError("browser operation timed out")

    def start(self, ident): return self._run(self._start(ident))
    async def _start(self, ident):
        check = next((x for x in self.store.get_runtime() if x.get("id") == ident), None)
        if not check or check.get("auth_mode") != "browser" or not check.get("login_url"): raise ValueError("Save a browser SSO check with a login URL first")
        # Never accumulate a browser/context for repeated authentication
        # attempts.  A check can have at most one interactive session.
        with self.lock:
            old = next((sid for sid, item in self.sessions.items() if item["check"].get("id") == ident), None)
        if old:
            with self.lock: self.authenticated.pop(ident, None)
            await self._close(old)
        try:
            from playwright.async_api import async_playwright
            pw = await async_playwright().start(); browser = await pw.chromium.launch(headless=True, executable_path=next((p for p in ("/usr/bin/chromium", "/usr/bin/chromium-browser") if os.path.exists(p)), None))
        except Exception as error: raise RuntimeError("Playwright/Chromium is unavailable: %s" % error) from error
        state_path = AUTH_DIR / f"{ident}.json"
        try:
            context = await browser.new_context(storage_state=str(state_path) if state_path.exists() else None, ignore_https_errors=not check.get("verify_ssl", True))
            page = await context.new_page(); await page.goto(check["login_url"], wait_until="domcontentloaded", timeout=30000)
        except Exception:
            await browser.close(); await pw.stop()
            raise
        sid = uuid.uuid4().hex; session = {"pw": pw, "browser": browser, "context": context, "page": page, "check": check, "lock": asyncio.Lock(), "expires": time.time() + 900}
        with self.lock: self.sessions[sid] = session
        return sid, await self.image(session)
    async def image(self, session): return base64.b64encode(await session["page"].screenshot(type="png", timeout=10000)).decode()
    def get(self, sid):
        with self.lock:
            session = self.sessions.get(sid)
            if not session: raise ValueError("Browser session expired")
            if session["expires"] < time.time():
                self.sessions.pop(sid, None)
                asyncio.create_task(self._dispose(session))
                raise ValueError("Browser session expired")
            session["expires"] = time.time() + 900; return session
    def close(self, sid):
        return self._run(self._close(sid))
    async def _close(self, sid):
        with self.lock: session = self.sessions.pop(sid, None)
        if session: await self._dispose(session)
    async def _dispose(self, session):
        for key in ("context", "browser", "pw"):
            try:
                await (session[key].close() if key != "pw" else session[key].stop())
            except Exception: pass
    async def _close_all(self):
        with self.lock: sessions = list(self.sessions.items()); self.sessions.clear(); self.authenticated.clear()
        for _, session in sessions: await self._dispose(session)
    def close_all(self):
        try: self._run(self._close_all(), timeout=15)
        except Exception: LOG.warning("Unable to close browser sessions cleanly")
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.loop_thread.join(timeout=2)
    def finish(self, sid): return self._run(self._finish(sid))
    async def _finish(self, sid):
        session = self.get(sid)
        async with session["lock"]:
            response = await session["page"].goto(session["check"]["url"], wait_until="domcontentloaded", timeout=30000)
            if response and response.status >= 400: raise ValueError("browser login rejected (HTTP %s)" % response.status)
            success_text = session["check"].get("success_text")
            if success_text and success_text not in await session["page"].content(): raise ValueError("browser login success text was not found")
            AUTH_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
            state_path = AUTH_DIR / f"{session['check']['id']}.json"
            await session["page"].context.storage_state(path=str(state_path)); state_path.chmod(0o600)
            session["check"]["auth_status"] = "Browser SSO successful"; self.store.put(session["check"])
            with self.lock: self.authenticated[session["check"]["id"]] = session
            return await self.image(session)
    def fetch(self, check): return self._run(self._fetch(check))
    async def _fetch(self, check):
        with self.lock: session = self.authenticated.get(check.get("id"))
        if session and session["expires"] < time.time():
            with self.lock: self.authenticated.pop(check.get("id"), None)
            await self._dispose(session)
            session = None
        if not session:
            state_path = AUTH_DIR / f"{check.get('id')}.json"
            if not state_path.exists(): raise ValueError("browser SSO has not been completed")
            sid, _ = await self._start(check.get("id"))
            with self.lock: session = self.sessions[sid]
            with self.lock: self.authenticated[check.get("id")] = session
        async with session["lock"]:
            response = await session["page"].goto(check["url"], wait_until="domcontentloaded", timeout=30000)
            if not response: raise ValueError("browser did not return a response")
            # Do not copy an unbounded DOM into Python.  Keyword matching only
            # needs the visible page text, capped to the same response limit as
            # regular HTTP checks.
            content = await session["page"].evaluate("document.body ? document.body.innerText.slice(0, 16777216) : ''")
            return response.status, content
    def action(self, sid, action, data): return self._run(self._action(sid, action, data))
    async def _action(self, sid, action, data):
        session = self.get(sid)
        if action == "finish": return await self._finish(sid)
        async with session["lock"]:
            if action == "click":
                scale = float(data.get("scale", 1)); await session["page"].mouse.click(float(data["x"]) * scale, float(data["y"]) * scale)
            elif action == "type": await session["page"].keyboard.type(str(data.get("text", "")))
            else: raise ValueError("Unknown browser action")
            return await self.image(session)

def notify_auth_failure(check, reason):
    check["auth_status"] = "Authentication failed: " + str(reason)
    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token: return
    try:
        import requests
        requests.post("http://supervisor/core/api/services/persistent_notification/create", headers={"Authorization": "Bearer " + token}, json={"title": "Web Keyword Sensor authentication failure", "message": "Authentication failed for %s: %s" % (check.get("name", "unnamed"), reason)}, timeout=10)
    except Exception: pass

def start_server(store, browser_sessions=None, ai_profiles=None, test_check=None):
    if browser_sessions is None: browser_sessions = BrowserSessions(store)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args): pass
        def body(self):
            length = int(self.headers.get("Content-Length", 0))
            if length > 1024 * 1024: raise ValueError("request body is too large")
            return json.loads(self.rfile.read(length))
        def reply(self, value, status=200):
            data = json.dumps(value).encode(); self.send_response(status); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
        def error(self, message, status=400): self.reply({"error": str(message)}, status)
        def do_GET(self):
            path = urlparse(self.path).path
            if path in ("/", ""):
                data = HTML.encode(); self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
            elif path == "/api/checks": self.reply(store.get())
            elif path == "/api/ai-profiles": self.reply(ai_profiles.get_public() if ai_profiles else [])
            else: self.send_error(404)
        def do_POST(self):
            path = urlparse(self.path).path
            try:
                if path.startswith("/api/checks/") and path.endswith("/test"):
                    ident = unquote(path[len("/api/checks/"):-len("/test")]); self.reply(test_check(ident) if test_check else {"ok": False, "error": "check testing is unavailable"}); return
                if path == "/api/checks":
                    check = self.body(); store.put(check); safe = next(x for x in store.get() if x.get("id") == check.get("id")); self.reply(safe, 201); return
                if path == "/api/ai-profiles/test":
                    from ai_providers import evaluate
                    profile = ai_profiles.for_test(self.body()); evaluate(profile, "Return a valid JSON result confirming that this connection works.", "This is a connection test page.", 30); self.reply({"ok": True}); return
                if path == "/api/ai-profiles":
                    profile = ai_profiles.put(self.body()); self.reply({"id": profile["id"], "name": profile["name"], "provider": profile["provider"], "model": profile["model"], "enabled": profile["enabled"], "api_key_configured": True}, 201); return
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
            path = urlparse(self.path).path
            if path == "/api/ai-profiles":
                try:
                    profile = ai_profiles.put(self.body()); self.reply({"id": profile["id"], "name": profile["name"], "provider": profile["provider"], "model": profile["model"], "enabled": profile["enabled"], "api_key_configured": True})
                except Exception as error: self.error(error)
                return
            if path != "/api/checks": self.send_error(404); return
            try:
                check = self.body(); store.put(check); self.reply(next(x for x in store.get() if x.get("id") == check.get("id")))
            except (ValueError, TypeError): self.send_error(400)
        def do_DELETE(self):
            path = urlparse(self.path).path
            if path.startswith("/api/ai-profiles/"):
                ai_profiles.delete(unquote(path.split("/", 3)[3])); self.reply({"ok": True}); return
            prefix = "/api/checks/"; path = urlparse(self.path).path
            if not path.startswith(prefix): self.send_error(404); return
            store.delete(unquote(path[len(prefix):])); self.reply({"ok": True})
    server = ThreadingHTTPServer(("0.0.0.0", 8099), Handler); server.daemon_threads = True
    threading.Thread(target=server.serve_forever, name="web-ui", daemon=True).start(); return server
