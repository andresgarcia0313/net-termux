"""Enlace del teléfono: Wi-Fi, IP propias, router e Internet (todo sin root)."""
import fcntl, json, socket, struct, subprocess, time, urllib.request

from . import probe

SIOCGIFADDR, SIOCGIFNETMASK = 0x8915, 0x891B


def ifaddr(name, req=SIOCGIFADDR):
    """IPv4 de una interfaz por ioctl ('' si no existe); netlink está vetado en Android."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            raw = fcntl.ioctl(s.fileno(), req, struct.pack("256s", name[:15].encode()))
        except OSError:
            return ""
    return socket.inet_ntoa(raw[20:24])


def subnet(name="wlan0"):
    """Lista de IP de la subred /24 o menor de la interfaz (vacía si no hay Wi-Fi)."""
    ip, mask = ifaddr(name), ifaddr(name, SIOCGIFNETMASK)
    if not ip:
        return ip, []
    m = struct.unpack("!I", socket.inet_aton(mask))[0] | 0xFFFFFF00  # tope /24: no barrer un /16
    base = struct.unpack("!I", socket.inet_aton(ip))[0] & m
    return ip, [socket.inet_ntoa(struct.pack("!I", base + i)) for i in range(1, (~m & 0xFFFFFFFF))]


def wifi():
    """Datos de Termux:API; {} si la app no está o tarda."""
    try:
        out = subprocess.run(["termux-wifi-connectioninfo"], capture_output=True, text=True, timeout=8).stdout
        return json.loads(out or "{}")
    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
        return {}


def signal(rssi):
    """(estado, palabra) según la intensidad en dBm."""
    if rssi >= -55:
        return "ok", "excelente"
    if rssi >= -67:
        return "ok", "buena"
    if rssi >= -75:
        return "warn", "regular"
    return "bad", "débil"


def band(mhz):
    return "6 GHz" if mhz >= 5925 else "5 GHz" if mhz >= 4900 else "2,4 GHz" if mhz else ""


def router(ip):
    """El router es el .1 o el .254 que contesta DNS (sin /proc/net/route en Android)."""
    prefix = ip.rsplit(".", 1)[0]
    for host in (f"{prefix}.1", f"{prefix}.254"):
        latency = probe.dns_query(host)
        if latency is not None:
            return host, latency
    return "", None


def internet():
    """Latencia a 1.1.1.1, tiempo de resolución DNS e IP pública con su proveedor."""
    out = {"ping": probe.ping("1.1.1.1")}
    t = time.monotonic()
    try:
        socket.getaddrinfo("www.google.com", 443)
        out["dns"] = (time.monotonic() - t) * 1000
    except OSError:
        out["dns"] = None
    try:
        with urllib.request.urlopen("https://ipinfo.io/json", timeout=4) as r:
            out["public"] = json.load(r)
    except (OSError, ValueError):
        out["public"] = {}
    return out
