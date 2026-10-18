"""Recolecta lo de `net status` con hilos (un solo proceso: Android cierra Termux si crea muchos)."""
from concurrent.futures import ThreadPoolExecutor

from . import link, names, probe


def link_info(ip):
    """Wi-Fi, router e Internet medidos a la vez."""
    with ThreadPoolExecutor(3) as ex:
        wifi_f, net_f = ex.submit(link.wifi), ex.submit(link.internet)
        gw, gw_ms = link.router(ip) if ip else ("", None)
        return {"ip": ip, "wifi": wifi_f.result(), "router": gw, "router_ms": gw_ms,
                "internet": net_f.result(), "tun0": link.ifaddr("tun0")}


def scan(ips):
    """(icmp, tcp) de toda la subred. El barrido descubre; la latencia se mide
    después en calma, porque junto a cientos de sondeos TCP sale inflada."""
    with ThreadPoolExecutor(2) as ex:
        icmp_f, tcp_f = ex.submit(probe.sweep, ips), ex.submit(probe.tcp_scan, ips)
        icmp, tcp = icmp_f.result(), tcp_f.result()
    calm = probe.sweep(list(icmp), wait=0.8, tries=1)
    return {ip: calm.get(ip, v) for ip, v in icmp.items()}, tcp


def devices(ip, gw, icmp, tcp, ts_map):
    """Equipos vivos con nombre, tipo, latencia y servicios, ordenados por IP."""
    alive = sorted(set(icmp) | set(tcp) | {ip}, key=lambda a: tuple(map(int, a.split("."))))
    unnamed = [a for a in alive if a not in ts_map and a != ip]
    with ThreadPoolExecutor(16) as ex:
        found = dict(zip(unnamed, ex.map(names.best_name, unnamed)))
    out = []
    for a in alive:
        ts_name, ts_os = ts_map.get(a, ("", ""))
        latency, ttl = icmp.get(a, (None, 0))
        ports = tcp.get(a, set())
        out.append({
            "ip": a, "me": a == ip, "router": a == gw, "ms": latency, "ttl": ttl,
            "name": ts_name or found.get(a, "") or ("router" if a == gw else ""),
            "kind": "Router" if a == gw else "Android" if a == ip else names.kind(ttl, ports, ts_os),
            "services": names.services(ports), "tailscale": bool(ts_name),
        })
    return out
