"""Estado de la tailnet visto desde un equipo con CLI de Tailscale.

La app de Android no expone CLI ni API local: se pide `tailscale status --json` por
SSH a los equipos configurados (en serie, para no crear procesos en lote) y se guarda
copia para cuando ninguno conteste. Equipos: variable NET_TERMUX_TS_HOSTS o el fichero
~/.config/net-termux/tailscale-hosts (uno por línea, en orden de preferencia).
"""
import json, os, subprocess, time

from . import link

CONFIG = os.path.expanduser("~/.config/net-termux/tailscale-hosts")
CACHE = os.path.expanduser("~/.cache/net-termux/tailscale.json")
SSH = ["ssh", "-o", "ControlMaster=no", "-o", "BatchMode=yes", "-o", "ConnectTimeout=4"]


def sources():
    """Equipos con CLI de Tailscale a los que preguntar, en orden."""
    raw = os.environ.get("NET_TERMUX_TS_HOSTS", "")
    if not raw and os.path.exists(CONFIG):
        with open(CONFIG) as f:
            raw = " ".join(l.split("#", 1)[0] for l in f)
    return tuple(raw.replace(",", " ").split())


def _remote(host):
    try:
        r = subprocess.run(SSH + [host, "tailscale status --json"], capture_output=True,
                           text=True, timeout=9, stdin=subprocess.DEVNULL)
        return json.loads(r.stdout) if r.returncode == 0 else None
    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
        return None


def _save(data):
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    tmp = CACHE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f)
    os.replace(tmp, CACHE)


def cached():
    try:
        with open(CACHE) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def fetch(hosts=None):
    """Datos frescos del primer equipo que conteste; si ninguno, la copia guardada.

    Devuelve (data, origen, edad_en_segundos) o (None, '', 0).
    """
    for host in sources() if hosts is None else hosts:
        data = _remote(host)
        if data and data.get("Self"):
            data["_from"], data["_at"] = host, time.time()
            _save(data)
            return data, host, 0
    data = cached()
    if data:
        return data, data.get("_from", "?"), time.time() - data.get("_at", 0)
    return None, "", 0


def nodes(data):
    """Todos los nodos de la tailnet, incluido el que respondió."""
    return [data["Self"]] + list((data.get("Peer") or {}).values())


def short(node):
    return (node.get("DNSName") or node.get("HostName", "?")).split(".")[0]


def me(data):
    """Este teléfono dentro de la tailnet, reconocido por su IP de tun0."""
    ip = link.ifaddr("tun0")
    return ip, next((n for n in nodes(data) if ip and ip in n.get("TailscaleIPs", [])), None)


def lan_names(data):
    """{IP LAN: (nombre, os)} a partir de la dirección por la que cada nodo es visto."""
    out = {}
    for n in nodes(data) if data else []:
        for ep in [n.get("CurAddr")] + (n.get("Addrs") or []):
            addr = (ep or "").rsplit(":", 1)[0]
            if addr and addr not in out:
                out[addr] = (short(n), n.get("OS", ""))
    return out
