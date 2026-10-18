"""Lista de equipos de la tailnet, normalizada, desde la mejor fuente disponible.

Orden: API de Tailscale (si hay credencial) > SSH a un equipo con el CLI (opcional,
NET_TERMUX_TS_HOSTS o ~/.config/net-termux/tailscale-hosts) > copia local. La copia
permite que `tailscale status` funcione sin Internet y sin ningún otro equipo.
"""
import json, os, subprocess, time

from . import link, tsapi

CONFIG = os.path.expanduser("~/.config/net-termux/tailscale-hosts")
CACHE = os.path.expanduser("~/.cache/net-termux/tailnet.json")
OLD_CACHE = os.path.expanduser("~/.cache/net-termux/tailscale.json")  # formato 1.0
SSH = ["ssh", "-o", "ControlMaster=no", "-o", "BatchMode=yes", "-o", "ConnectTimeout=4"]


def sources():
    """Equipos opcionales con CLI de Tailscale a los que preguntar por SSH, en orden."""
    raw = os.environ.get("NET_TERMUX_TS_HOSTS", "")
    if not raw and os.path.exists(CONFIG):
        with open(CONFIG) as f:
            raw = " ".join(l.split("#", 1)[0] for l in f)
    return tuple(raw.replace(",", " ").split())


def from_status(st, origin):
    """Convierte `tailscale status --json` al formato común."""
    nodes = [st["Self"]] + list((st.get("Peer") or {}).values())
    return {"tailnet": st.get("MagicDNSSuffix", ""), "source": origin, "at": st.get("_at", time.time()),
            "peers": [{
                "name": (n.get("DNSName") or n.get("HostName", "?")).split(".")[0],
                "fqdn": (n.get("DNSName") or "").rstrip("."), "ips": n.get("TailscaleIPs") or [],
                "os": n.get("OS", ""), "online": bool(n.get("Online")) or n is st["Self"],
                "last_seen": "" if n.get("LastSeen", "0001").startswith("0001") else n["LastSeen"],
                "key_expiry": n.get("KeyExpiry") or "",
                "endpoints": ([n["CurAddr"]] if n.get("CurAddr") else []) + (n.get("Addrs") or []),
                "exit_node": bool(n.get("ExitNode")), "rx": n.get("RxBytes"), "tx": n.get("TxBytes"),
                "version": "", "update": False} for n in nodes]}


def _ssh(host):
    try:
        r = subprocess.run(SSH + [host, "tailscale status --json"], capture_output=True,
                           text=True, timeout=9, stdin=subprocess.DEVNULL)
        st = json.loads(r.stdout) if r.returncode == 0 else None
    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
        return None
    return from_status(st, f"{host} por SSH") if st and st.get("Self") else None


def _save(data):
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    with open(CACHE + ".tmp", "w") as f:
        json.dump(data, f)
    os.replace(CACHE + ".tmp", CACHE)


def cached():
    for path, convert in ((CACHE, None), (OLD_CACHE, from_status)):
        try:
            with open(path) as f:
                data = json.load(f)
            return convert(data, data.get("_from", "?") + " por SSH") if convert else data
        except (OSError, ValueError, KeyError):
            continue
    return None


def fetch(hosts=None):
    """(datos, en_vivo): en_vivo es False si salen de la copia local."""
    data = tsapi.fetch()
    for host in () if data else (sources() if hosts is None else hosts):
        data = _ssh(host)
        if data:
            break
    if data:
        _save(data)
        return data, True
    return cached(), False


def me(data):
    """(IP de tun0, este teléfono dentro de la tailnet o None)."""
    ip = link.ifaddr("tun0")
    return ip, next((p for p in (data or {}).get("peers", []) if ip and ip in p["ips"]), None)


def lan_names(data):
    """{IP LAN: (nombre, os)} según las direcciones por las que se ve cada equipo."""
    out = {}
    for p in (data or {}).get("peers", []):
        for ep in p["endpoints"]:
            addr = ep.rsplit(":", 1)[0]
            if addr and addr not in out:
                out[addr] = (p["name"], p["os"])
    return out
