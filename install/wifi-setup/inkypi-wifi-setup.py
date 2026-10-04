#!/usr/local/inkypi/venv_inkypi/bin/python

from flask import Flask, request, redirect, url_for
import subprocess
import html
import uuid
import secrets
from flask import session, abort

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
app.config.update(MAX_CONTENT_LENGTH=8192, SESSION_COOKIE_SAMESITE="Strict")

@app.before_request
def protect_forms():
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(32)
    if request.method == "POST" and not secrets.compare_digest(
        request.form.get("csrf", ""), session["csrf"]
    ):
        abort(403)


HOTSPOT_PROFILE = "inkypi-hotspot"
HOTSPOT_SSID = "InkyPi-Setup"

def run(cmd):
    try:
        return subprocess.run(cmd, text=True, capture_output=True, timeout=45)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(cmd, 124, "", "Command timed out")

def split_nmcli(line):
    """NetworkManager escapes colons and backslashes in terse fields."""
    fields, field, escaped = [], "", False
    for char in line:
        if escaped:
            field += char
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == ":":
            fields.append(field)
            field = ""
        else:
            field += char
    fields.append(field)
    return fields

def scan_networks():
    result = run([
        "nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY",
        "device", "wifi", "list", "--rescan", "yes"
    ])
    networks = []
    seen = set()
    for line in result.stdout.splitlines():
        parts = split_nmcli(line)
        if not parts:
            continue
        ssid = parts[0]
        if not ssid or ssid in seen or ssid == HOTSPOT_SSID:
            continue
        seen.add(ssid)
        signal = parts[1] if len(parts) > 1 else ""
        security = parts[2] if len(parts) > 2 else ""
        networks.append((ssid, signal, security))
    return networks

def saved_wifi_profiles():
    result = run(["nmcli", "-t", "-f", "NAME,TYPE,DEVICE", "connection", "show"])
    profiles = []
    for line in result.stdout.splitlines():
        parts = split_nmcli(line)
        if len(parts) < 2:
            continue
        name = parts[0]
        conn_type = parts[1].strip()
        device = parts[2].strip() if len(parts) > 2 else ""

        if conn_type != "802-11-wireless" or name == HOTSPOT_PROFILE:
            continue

        ssid_result = run(["nmcli", "-g", "802-11-wireless.ssid", "connection", "show", "id", name])
        ssid = ssid_result.stdout.strip() or name
        profiles.append((name, ssid, device))
    return profiles

def friendly_error(stderr, stdout):
    message = (stderr + " " + stdout).lower()

    wrong_password_markers = [
        "secrets were required",
        "no secrets",
        "wrong password",
        "incorrect password",
        "authentication failed",
        "802.1x supplicant",
        "supplicant-disconnect",
    ]
    if any(marker in message for marker in wrong_password_markers):
        return "Wrong password. Please check the Wi-Fi password and try again."

    if "no network with ssid" in message or "network could not be found" in message:
        return "Network not found. Please make sure the Wi-Fi network is available and try again."

    if "activation failed" in message:
        return "Connection unsuccessful. Please check the network and password, then try again."

    return "Connection unsuccessful. Please try again."

def page_shell(body, script=""):
    # Inject the token into every form, including saved-network deletion forms.
    import re
    token = html.escape(session["csrf"], quote=True)
    body = re.sub(r"(<form\b[^>]*>)", lambda m: m[0] + f'<input type="hidden" name="csrf" value="{token}">', body)
    return f"""<!doctype html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>InkyPi Wi-Fi Setup</title>
<style>
*{{box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#f4f4f4;margin:0;padding:24px 14px;color:#111}}
.card{{max-width:460px;margin:auto;background:#fff;padding:24px;border-radius:16px;box-shadow:0 4px 20px rgba(0,0,0,.08)}}
h1{{margin:0 0 6px}}
h2{{margin-top:26px;font-size:19px}}
.muted{{color:#666;font-size:14px}}
label{{display:block;font-weight:600;margin-top:14px}}
select,input,.primary{{width:100%;padding:12px;font-size:16px;border:1px solid #ccc;border-radius:9px;margin-top:8px}}
.primary{{border:0;font-weight:700;cursor:pointer;margin-top:18px}}
.primary:disabled{{opacity:.55;cursor:default}}
.password-wrap{{position:relative}}
.password-wrap input{{padding-right:54px}}
.eye{{position:absolute;right:7px;top:13px;width:42px;height:38px;border:0;background:transparent;font-size:20px;cursor:pointer}}
.status{{display:none;margin-top:16px;padding:13px;border-radius:9px;text-align:center;font-weight:600}}
.status.connecting{{display:block;background:#f0f0f0}}
.status.success{{display:block;background:#e9f8ed}}
.status.error{{display:block;background:#fdecec}}
.spinner{{display:inline-block;width:16px;height:16px;border:2px solid #aaa;border-top-color:#111;border-radius:50%;animation:spin .8s linear infinite;vertical-align:-3px;margin-right:7px}}
@keyframes spin{{to{{transform:rotate(360deg)}}}}
.saved{{border-top:1px solid #eee;margin-top:26px;padding-top:4px}}
.network-row{{display:flex;gap:10px;align-items:center;padding:12px 0;border-bottom:1px solid #eee}}
.network-info{{flex:1;min-width:0}}
.network-name{{font-weight:650;overflow-wrap:anywhere}}
.profile-name{{color:#777;font-size:12px;overflow-wrap:anywhere}}
.delete-form{{margin:0}}
.delete{{border:1px solid #c33;background:#fff;padding:8px 11px;border-radius:8px;cursor:pointer;font-weight:600}}
.badge{{display:inline-block;font-size:11px;padding:3px 7px;border-radius:999px;background:#eee;margin-top:4px}}
.result-icon{{font-size:48px;text-align:center}}
.center{{text-align:center}}
a{{color:inherit}}
</style>
</head>
<body>
<div class="card">{body}</div>
{script}
</body>
</html>"""

@app.route("/")
def index():
    networks = scan_networks()
    options = []

    for ssid, signal, security in networks:
        safe_ssid = html.escape(ssid, quote=True)
        safe_security = html.escape(security)
        label = f"{safe_ssid} - {html.escape(signal)}%"
        if safe_security:
            label += f" - {safe_security}"
        options.append(f'<option value="{safe_ssid}">{label}</option>')

    if not options:
        options.append('<option value="">No Wi-Fi networks found</option>')

    saved_rows = []
    for profile, ssid, device in saved_wifi_profiles():
        safe_profile = html.escape(profile, quote=True)
        safe_ssid = html.escape(ssid)
        status = '<span class="badge">Connected</span>' if device else '<span class="badge">Saved</span>'
        profile_note = "" if profile == ssid else f'<div class="profile-name">Profile: {html.escape(profile)}</div>'

        saved_rows.append(f"""
<div class="network-row">
  <div class="network-info">
    <div class="network-name">{safe_ssid}</div>
    {profile_note}
    {status}
  </div>
  <form class="delete-form" method="post" action="/delete-network"
        onsubmit="return confirm('Delete this saved Wi-Fi network?');">
    <input type="hidden" name="profile" value="{safe_profile}">
    <button class="delete" type="submit">Delete</button>
  </form>
</div>""")

    saved_section = "".join(saved_rows) if saved_rows else '<p class="muted">No saved Wi-Fi networks.</p>'

    body = f"""
<h1>InkyPi Wi-Fi Setup</h1>
<p class="muted">Choose a Wi-Fi network for your InkyPi.</p>

<form id="wifi-form" method="post" action="/connect" onsubmit="showConnecting()">
<label for="ssid">Wi-Fi network</label>
<select id="ssid" name="ssid" required>
{''.join(options)}
</select>

<label for="wifi-password">Password</label>
<div class="password-wrap">
  <input id="wifi-password" name="password" type="password" autocomplete="current-password">
  <button class="eye" id="password-eye" type="button" onclick="togglePassword()" aria-label="Show or hide password">
    <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
      <path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6S2 12 2 12"/>
      <circle cx="12" cy="12" r="3"/>
      <path d="M3 3l18 18"/>
    </svg>
  </button>
</div>

<button id="connect-button" class="primary" type="submit">Connect</button>
<div id="status" class="status"></div>
</form>

<div class="saved">
<h2>Saved Wi-Fi Networks</h2>
{saved_section}
</div>
"""

    js = """
<script>
function togglePassword() {
    const field = document.getElementById("wifi-password");
    const eye = document.getElementById("password-eye");

    if (field.type === "password") {
        field.type = "text";
        eye.innerHTML = `
          <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6S2 12 2 12"/>
            <circle cx="12" cy="12" r="3"/>
          </svg>`;
    } else {
        field.type = "password";
        eye.innerHTML = `
          <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6S2 12 2 12"/>
            <circle cx="12" cy="12" r="3"/>
            <path d="M3 3l18 18"/>
          </svg>`;
    }
}
function showConnecting() {
    const button = document.getElementById("connect-button");
    const status = document.getElementById("status");
    button.disabled = true;
    button.textContent = "Connecting...";
    status.className = "status connecting";
    status.innerHTML = '<span class="spinner"></span>Connecting to Wi-Fi...';
}
</script>
"""
    return page_shell(body, js)

@app.route("/delete-network", methods=["POST"])
def delete_network():
    profile = request.form.get("profile", "")

    if not profile or profile == HOTSPOT_PROFILE:
        return page_shell("""
<div class="result-icon">⚠️</div>
<h2 class="center">Cannot delete network</h2>
<p class="center">This Wi-Fi profile cannot be deleted.</p>
<p class="center"><a href="/">Back to Wi-Fi setup</a></p>
"""), 400

    existing = {name for name, _, _ in saved_wifi_profiles()}
    if profile not in existing:
        return page_shell("""
<div class="result-icon">⚠️</div>
<h2 class="center">Network not found</h2>
<p class="center">The saved Wi-Fi profile no longer exists.</p>
<p class="center"><a href="/">Back to Wi-Fi setup</a></p>
"""), 404

    active = run(["nmcli", "-t", "-f", "NAME,DEVICE", "connection", "show", "--active"])
    active_profiles = {
        split_nmcli(line)[0]
        for line in active.stdout.splitlines()
        if line.endswith(":wlan0")
    }

    if profile in active_profiles:
        scheduled = run([
            "systemd-run",
            "--collect",
            "--unit=inkypi-delete-active-wifi-" + uuid.uuid4().hex,
            "--on-active=2s",
            "/usr/local/sbin/inkypi-delete-active-wifi.sh",
            profile
        ])

        if scheduled.returncode:
            return page_shell("Unable to schedule the network change. Please retry."), 500
        return page_shell("""
<div class="result-icon">✓</div>
<h2 class="center">Switching to setup mode</h2>
<div class="status success">The current Wi-Fi network is being removed.</div>
<p class="center">InkyPi-Setup will become available again in a few seconds.</p>
<p class="muted center">Connect to <strong>InkyPi-Setup</strong>, then open <strong>http://192.168.4.1</strong>.</p>
""")

    result = run(["nmcli", "connection", "delete", "id", profile])
    if result.returncode != 0:
        return page_shell(f"""
<div class="result-icon">⚠️</div>
<h2 class="center">Delete failed</h2>
<p class="center">{html.escape(result.stderr.strip() or 'Unable to delete this saved network.')}</p>
<p class="center"><a href="/">Back to Wi-Fi setup</a></p>
"""), 500

    return redirect(url_for("index"))

@app.route("/connect", methods=["POST"])
def connect():
    ssid = request.form.get("ssid", "")
    password = request.form.get("password", "")

    if not ssid:
        return page_shell("""
<div class="result-icon">⚠️</div>
<h2 class="center">Select a network</h2>
<p class="center">Please select a Wi-Fi network and try again.</p>
<p class="center"><a href="/">Back to Wi-Fi setup</a></p>
"""), 400

    cmd = ["nmcli", "--wait", "30", "device", "wifi", "connect", ssid, "ifname", "wlan0"]
    if password:
        cmd += ["password", password]

    result = run(cmd)

    if result.returncode != 0:
        # Restore the setup hotspot if NetworkManager dropped it during the failed attempt.
        run(["nmcli", "connection", "up", HOTSPOT_PROFILE])

        message = friendly_error(result.stderr, result.stdout)
        return page_shell(f"""
<div class="result-icon">✕</div>
<h2 class="center">Connection unsuccessful</h2>
<div class="status error">{html.escape(message)}</div>
<p class="center"><a href="/">Try again</a></p>
"""), 400

    # Schedule the handoff after giving the browser a moment to receive this page.
    scheduled = run([
        "systemd-run",
        "--collect",
        "--unit=inkypi-wifi-connected-handoff-" + uuid.uuid4().hex,
        "--on-active=3s",
        "/usr/local/sbin/inkypi-wifi-connected.sh"
    ])

    if scheduled.returncode:
        run(["nmcli", "connection", "up", HOTSPOT_PROFILE])
        return page_shell("Unable to resume InkyPi. Please retry."), 500
    safe_ssid = html.escape(ssid)
    body = f"""
<div class="result-icon">✓</div>
<h2 class="center">Connection successful</h2>
<div class="status success">Connected to <strong>{safe_ssid}</strong>.</div>
<p class="center">InkyPi will now resume its normal display.</p>
<p class="muted center">You can close this page.</p>
"""
    js = """
<script>
setTimeout(function() { window.close(); }, 2500);
</script>
"""
    return page_shell(body, js)

if __name__ == "__main__":
    from waitress import serve
    serve(app, host="192.168.4.1", port=80, threads=1)
