"""Fuente oficial: la API de Tailscale. No depende de ningún otro equipo.

Credencial (la primera que exista):
  TS_API_KEY="tskey-api-..."                       llave de API (vence a los 90 días como máximo)
  TS_OAUTH_CLIENT_ID + TS_OAUTH_CLIENT_SECRET      cliente OAuth de solo lectura (no vence)
  ~/.config/net-termux/tailscale-api               una línea: la llave, o "<client_id> <secret>"
"""
import json, os, time, urllib.parse, urllib.request

API = "https://api.tailscale.com/api/v2"
CONF = os.path.expanduser("~/.config/net-termux/tailscale-api")
TOKEN_CACHE = os.path.expanduser("~/.cache/net-termux/api-token.json")


def credentials():
    """('key', llave) | ('oauth', (id, secreto)) | None."""
    if os.environ.get("TS_API_KEY"):
        return "key", os.environ["TS_API_KEY"]
    if os.environ.get("TS_OAUTH_CLIENT_ID") and os.environ.get("TS_OAUTH_CLIENT_SECRET"):
        return "oauth", (os.environ["TS_OAUTH_CLIENT_ID"], os.environ["TS_OAUTH_CLIENT_SECRET"])
    try:
        with open(CONF) as f:
            parts = f.read().split()
    except OSError:
        return None
    if len(parts) == 1:
        return "key", parts[0]
    return ("oauth", (parts[0], parts[1])) if len(parts) == 2 else None


def _oauth_token(client_id, secret):
    """Token de acceso de 1 hora, guardado con permisos 600 mientras sirva."""
    try:
        with open(TOKEN_CACHE) as f:
            cached = json.load(f)
        if cached.get("client_id") == client_id and cached.get("until", 0) > time.time() + 60:
            return cached["token"]
    except (OSError, ValueError):
        pass
    body = urllib.parse.urlencode({"client_id": client_id, "client_secret": secret}).encode()
    with urllib.request.urlopen(f"{API}/oauth/token", body, timeout=8) as r:
        reply = json.load(r)
    os.makedirs(os.path.dirname(TOKEN_CACHE), exist_ok=True)
    fd = os.open(TOKEN_CACHE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump({"client_id": client_id, "token": reply["access_token"],
                   "until": time.time() + reply.get("expires_in", 3600)}, f)
    return reply["access_token"]


def _device(d):
    conn = d.get("clientConnectivity") or {}
    return {
        "name": (d.get("name") or d.get("hostname") or "?").split(".")[0],
        "fqdn": d.get("name", ""), "ips": d.get("addresses") or [], "os": d.get("os", ""),
        "online": bool(d.get("connectedToControl")), "last_seen": d.get("lastSeen", ""),
        "key_expiry": "" if d.get("keyExpiryDisabled") else d.get("expires", ""),
        "endpoints": conn.get("endpoints") or [], "exit_node": False, "rx": None, "tx": None,
        "version": (d.get("clientVersion") or "").split("-")[0], "update": bool(d.get("updateAvailable")),
    }


def fetch():
    """Datos normalizados de la tailnet, o None si no hay credencial o falla."""
    cred = credentials()
    if not cred:
        return None
    try:
        token = cred[1] if cred[0] == "key" else _oauth_token(*cred[1])
        req = urllib.request.Request(f"{API}/tailnet/-/devices?fields=all",
                                     headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req, timeout=8) as r:
            devices = json.load(r).get("devices", [])
    except (OSError, ValueError, KeyError):
        return None
    fqdn = next((d["name"] for d in devices if d.get("name", "").count(".") > 1), "")
    return {"tailnet": fqdn.split(".", 1)[1] if fqdn else "", "source": "API de Tailscale",
            "at": time.time(), "peers": [_device(d) for d in devices]}
