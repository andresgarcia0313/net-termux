"""Nombre y tipo de un equipo de la LAN sin MAC (Android niega la tabla ARP).

Nombre: Tailscale > mDNS > DNS del router > NetBIOS. Tipo: Tailscale > puertos > TTL.
"""
import re, socket

from .mdns import reverse as mdns

TS_OS = {"linux": "Linux", "windows": "Windows", "android": "Android", "macos": "macOS", "ios": "iPhone/iPad"}


def rdns(ip):
    try:
        name = socket.gethostbyaddr(ip)[0]
    except OSError:
        return ""
    return "" if re.fullmatch(r"[\d.-]+|.*in-addr.*", name) else re.sub(r"\.(lan|home|local)$", "", name)


def netbios(ip, wait=0.8):
    """Consulta de estado NetBIOS (UDP 137): primer nombre único de tipo <00>."""
    q = b"\x4e\x42\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x20CKAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\x00\x00\x21\x00\x01"
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.settimeout(wait)
        try:
            s.sendto(q, (ip, 137))
            data = s.recv(1024)
        except OSError:
            return ""
    for i in range(data[56] if len(data) > 56 else 0):
        entry = data[57 + 18 * i: 75 + 18 * i]
        if len(entry) == 18 and entry[15] == 0 and not entry[16] & 0x80:
            return entry[:15].decode("latin-1").strip()
    return ""


def best_name(ip):
    for source in (mdns, rdns, netbios):
        name = source(ip)
        if name:
            return name
    return ""


def kind(ttl, ports, ts_os=""):
    """Tipo de equipo legible; '' si no hay pistas."""
    if ts_os:
        return TS_OS.get(ts_os, ts_os.capitalize())
    if 62078 in ports:
        return "iPhone/iPad"
    if 8009 in ports:
        return "TV/Chromecast"
    if 554 in ports:
        return "Cámara"
    if 64 < ttl <= 128:
        return "Windows"
    if ttl > 128:
        return "Equipo de red"
    if ports and ports <= {80, 443}:
        return "Equipo de red"
    if ports & {22, 445}:
        return "Linux"
    return "Linux/Android" if ttl else ""


SERVICES = {22: "ssh", 80: "web", 443: "https", 445: "smb", 554: "rtsp", 8009: "cast", 62078: "apple"}


def services(ports):
    return " ".join(SERVICES[p] for p in sorted(ports) if p in SERVICES)
