#!/usr/bin/env python3
"""Ingress UI and persistent check store."""
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

PATH = Path("/data/checks.json")
HTML = '''<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1"><title>Web Keyword Sensor</title>
<style>body{font:16px system-ui;max-width:900px;margin:2em auto;padding:0 1em;background:#fafafa;color:#263238}.card{background:white;border:1px solid #ddd;border-radius:8px;padding:1em;margin:1em 0}form{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px}label{display:flex;flex-direction:column;gap:4px;font-weight:600}input,select,button{font:inherit;padding:8px}button{background:#1976d2;color:#fff;border:0;border-radius:4px;cursor:pointer}.delete{background:#c62828}.actions{align-self:end;display:flex;gap:8px}.days{grid-column:1/-1;display:flex;flex-wrap:wrap;gap:10px}.days label{display:block;font-weight:400}</style>
<h1>Web Keyword Sensor</h1><p>Manage page checks. Changes are saved immediately.</p><div id="list"></div><div class="card"><h2 id="heading">Add check</h2><form id="form"><input id="id" type="hidden"><label>Name<input id="name" required></label><label>URL<input id="url" type="url" required></label><label>Phrase<input id="phrase" required></label><label>Entity type<select id="entity_type"><option value="binary_sensor">Binary sensor</option><option value="sensor">Sensor</option></select></label><label>Interval<input id="interval" type="number" min="1" max="31536000" value="15" required></label><label>Unit<select id="unit"><option>seconds</option><option selected>minutes</option><option>hours</option><option>days</option><option>weeks</option></select></label><label>From<select id="time_from"></select></label><label>To<select id="time_to"></select></label><div class="days"><b>Days:</b><label><input class="day" value="monday" type="checkbox" checked> Mon</label><label><input class="day" value="tuesday" type="checkbox" checked> Tue</label><label><input class="day" value="wednesday" type="checkbox" checked> Wed</label><label><input class="day" value="thursday" type="checkbox" checked> Thu</label><label><input class="day" value="friday" type="checkbox" checked> Fri</label><label><input class="day" value="saturday" type="checkbox" checked> Sat</label><label><input class="day" value="sunday" type="checkbox" checked> Sun</label></div><label>Login URL (optional)<input id="login_url" type="url"></label><label>Username<input id="username" autocomplete="username"></label><label>Password<input id="password" type="password" autocomplete="current-password"></label><label>TOTP secret<input id="totp_secret" type="password" placeholder="Optional"></label><label>Username field<input id="username_field" value="username"></label><label>Password field<input id="password_field" value="password"></label><label>TOTP field<input id="totp_field" value="totp"></label><label>Login success text<input id="success_text" placeholder="Optional"></label><label>Case sensitive<input id="case_sensitive" type="checkbox"></label><label>Verify TLS<input id="verify_ssl" type="checkbox" checked></label><label>Enabled<input id="enabled" type="checkbox" checked></label><div class="actions"><button>Save</button><button type="button" id="cancel" hidden>Cancel</button></div></form></div>
<script>const ids=['name','url','phrase','entity_type','interval','unit','time_from','time_to','login_url','username_field','password_field','totp_field','success_text','case_sensitive','verify_ssl','enabled'];const $=x=>document.getElementById(x);const esc=x=>String(x).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));for(const id of ['time_from','time_to'])for(let h=0;h<24;h++){let o=document.createElement('option');o.value=String(h).padStart(2,'0')+':00';o.textContent=o.value;$(id).append(o)}async function load(){const x=await (await fetch('./api/checks')).json();$('list').innerHTML=x.map(c=>`<div class="card"><h2>${esc(c.name)}</h2><p>${esc(c.entity_type)} · every ${c.interval} ${esc(c.unit)} · ${esc(c.time_from||'00:00')}–${esc(c.time_to||'23:00')} · ${c.enabled?'enabled':'disabled'}</p><p>${esc(c.phrase)}<br>${esc(c.url)}<br>${c.login_configured?'Login configured':'No login configured'} · ${esc(c.auth_status||'Not tested')}</p><button onclick='edit(${JSON.stringify(c)})'>Edit</button> <button class="delete" onclick='del("${esc(c.id)}")'>Delete</button></div>`).join('')||'<p>No checks configured.</p>'}function edit(c){$('id').value=c.id;ids.forEach(k=>$(k)[$(k).type==='checkbox'?'checked':'value']=c[k]??$(k).value);document.querySelectorAll('.day').forEach(x=>x.checked=(c.days||['monday','tuesday','wednesday','thursday','friday','saturday','sunday']).includes(x.value));$('heading').textContent='Edit check';$('cancel').hidden=false;scrollTo(0,document.body.scrollHeight)}function reset(){$('form').reset();$('id').value='';$('time_from').value='00:00';$('time_to').value='23:00';document.querySelectorAll('.day').forEach(x=>x.checked=true);$('heading').textContent='Add check';$('cancel').hidden=true}async function del(id){if(confirm('Delete this check?')){await fetch('./api/checks/'+encodeURIComponent(id),{method:'DELETE'});load()}}$('form').onsubmit=async e=>{e.preventDefault();let c=Object.fromEntries(ids.map(k=>[k,$(k).type==='checkbox'?$(k).checked:$(k).value]));c.username=$('username').value;c.password=$('password').value;c.totp_secret=$('totp_secret').value;c.days=[...document.querySelectorAll('.day:checked')].map(x=>x.value);c.id=$('id').value||crypto.randomUUID();c.interval=Number(c.interval);await fetch('./api/checks',{method:$('id').value?'PUT':'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(c)});reset();load()};$('cancel').onclick=reset;reset();load();</script>'''

class CheckStore:
    def __init__(self, initial):
        os.umask(0o077)
        self.lock = threading.RLock()
        try:
            self.checks = json.loads(PATH.read_text())
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            self.checks = initial
            self.save()
    def save(self):
        PATH.write_text(json.dumps(self.checks, indent=2) + "\n")
        PATH.chmod(0o600)
    def get(self):
        with self.lock:
            result = []
            for check in self.checks:
                item = dict(check)
                item["login_configured"] = bool(item.get("username") and item.get("password"))
                item["username"] = item.get("username", "")
                item["password"] = ""
                item["totp_secret"] = ""
                result.append(item)
            return result
    def get_runtime(self):
        with self.lock: return [dict(x) for x in self.checks]
    def put(self, check):
        with self.lock:
            old = next((x for x in self.checks if x.get("id") == check.get("id")), {})
            for secret in ("username", "password", "totp_secret"):
                if not check.get(secret): check[secret] = old.get(secret, "")
            self.checks = [check if x.get("id") == check.get("id") else x for x in self.checks]
            if not any(x.get("id") == check.get("id") for x in self.checks): self.checks.append(check)
            self.save()
    def delete(self, ident):
        with self.lock:
            self.checks = [x for x in self.checks if x.get("id") != ident]; self.save()

def start_server(store):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args): pass
        def body(self): return json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        def reply(self, value, status=200):
            data = json.dumps(value).encode(); self.send_response(status); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
        def do_GET(self):
            path = urlparse(self.path).path
            if path in ("/", ""):
                data = HTML.encode(); self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
            elif path == "/api/checks": self.reply(store.get())
            else: self.send_error(404)
        def do_POST(self):
            if urlparse(self.path).path != "/api/checks": self.send_error(404); return
            try: check = self.body(); store.put(check); self.reply(check, 201)
            except (ValueError, TypeError): self.send_error(400)
        def do_PUT(self):
            if urlparse(self.path).path != "/api/checks": self.send_error(404); return
            try: check = self.body(); store.put(check); self.reply(check)
            except (ValueError, TypeError): self.send_error(400)
        def do_DELETE(self):
            prefix = "/api/checks/"; path = urlparse(self.path).path
            if not path.startswith(prefix): self.send_error(404); return
            store.delete(unquote(path[len(prefix):])); self.reply({"ok": True})
    server = ThreadingHTTPServer(("0.0.0.0", 8099), Handler)
    threading.Thread(target=server.serve_forever, name="web-ui", daemon=True).start()
    return server
