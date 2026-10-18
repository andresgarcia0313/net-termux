"""Medición en vivo desde el teléfono, por el túnel de Tailscale.

No necesita otro equipo ni Internet: ping ICMP y TCP a cada IP de la tailnet, y el
nombre de cada IP preguntado al DNS interno de Tailscale (100.100.100.100).
"""
import socket
from concurrent.futures import ThreadPoolExecutor

from . import mdns, probe

QUAD100 = "100.100.100.100"
PORTS = (22, 80, 443, 445, 3389, 5900, 8080)


def ptr(ip, wait=1.0):
    """Nombre completo de una IP de la tailnet según MagicDNS, o ''."""
    query = b"\x74\x73\x01\x00" + mdns._query(ip)[4:]  # misma consulta, con recursión
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.settimeout(wait)
        try:
            s.sendto(query, (QUAD100, 53))
            return mdns._ptr_answer(s.recv(2048)).rstrip(".")
        except OSError:
            return ""


def measure(ips):
    """({ip: ms} de los que respondieron ping, {ip} de los que solo respondieron TCP)."""
    icmp = probe.sweep(ips, wait=1.5)
    rest = [ip for ip in ips if ip not in icmp]
    tcp = probe.tcp_scan(rest, PORTS, wait=1.5) if rest else {}
    return {ip: v[0] for ip, v in icmp.items()}, set(tcp)


def names(ips):
    """{ip: nombre completo} vigentes según MagicDNS."""
    with ThreadPoolExecutor(8) as ex:
        return {ip: n for ip, n in zip(ips, ex.map(ptr, ips)) if n}
