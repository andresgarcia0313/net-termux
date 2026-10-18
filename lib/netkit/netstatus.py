"""`net status`: cómo está conectado el teléfono y quién más hay en la red."""
import json, sys, time
from concurrent.futures import ThreadPoolExecutor

from . import gather, link, tsdata, tsstatus, ui
from .fmt import num


def isp(org):
    """'AS64500 RED EJEMPLO S.A.' -> 'RED Ejemplo'."""
    words = [w for w in org.split()[1:] if w.upper() not in ("S.A.", "S.A.S.", "SAS", "S.A")]
    return " ".join(w.capitalize() if len(w) > 3 else w for w in words)


def show_link(info, me_ts):
    ui.title("Red")
    w, ip = info["wifi"], info["ip"]
    if not ip:
        ui.line("bad", "Sin Wi-Fi", "Conéctate a una red para ver los equipos cercanos.")
        return
    state, word = link.signal(w.get("rssi", -100)) if w else ("ok", "")
    ssid = w.get("ssid", "")
    head = " · ".join(x for x in (
        "Wi-Fi" + (f" «{ssid}»" if ssid and "unknown" not in ssid else ""),
        link.band(w.get("frequency_mhz", 0)),
        f"señal {word} ({w['rssi']} dBm)" if w else "",
        f"{w['link_speed_mbps']} Mbps" if w.get("link_speed_mbps") else "") if x)
    gw = f" · router .{info['router'].rsplit('.', 1)[1]} · {ui.ms(info['router_ms'])}" if info["router"] else ""
    ui.line(state, head)
    print(f"  {ui.paint('Este teléfono ' + ip, 'dim')}{gw}")
    net, pub = info["internet"], info["internet"]["public"]
    if net["ping"] is None and net["dns"] is None:
        ui.line("bad", "Sin Internet", "El Wi-Fi funciona, pero no sale a Internet. Revisa el router o el proveedor.")
    else:
        slow = net["ping"] is None or net["ping"] > 150 or net["dns"] is None
        dns = f"DNS {ui.ms(net['dns'], 100, 400)}" if net["dns"] is not None else ui.paint("DNS no resuelve", "bad")
        ui.line("warn" if slow else "ok", f"Internet · {ui.ms(net['ping'], 60, 150)} · {dns}",
                " · ".join(x for x in (isp(pub.get("org", "")), pub.get("city", ""), pub.get("ip", "")) if x))
    if info["tun0"]:
        note = tsstatus.key_note(me_ts or {})
        ui.line(note[0] if note else "ok", f"Tailscale · {info['tun0']}" + (f" · {note[1]}" if note else ""),
                "tailscale status → equipos de la VPN")
    else:
        ui.line("off", "Tailscale apagado en este teléfono", "Actívalo en la app de Tailscale.")


def show_devices(devs, subnet):
    ui.title("Equipos", f"{len(devs)} en {subnet}")
    cols = ui.width()
    name_w = min(max((len(d["name"] or "sin nombre") for d in devs), default=10), 20 if cols >= 60 else 14)
    ip_w = max(len(d["ip"].rsplit(".", 1)[1]) for d in devs) + 1
    for d in devs:
        state = "me" if d["me"] else "ok" if d["ms"] is not None else "off"
        label = "este teléfono" if d["me"] else d["name"]
        name = ui.paint(label, "bold" if d["tailscale"] else "") if label else ui.paint("sin nombre", "dim")
        lat = "" if d["me"] else ui.ms(d["ms"]) if d["ms"] is not None else ui.paint("sin ping", "dim")
        row = (f"{ui.mark(state)} {ui.fit(name, name_w)}  {ui.paint(ui.fit('.' + d['ip'].rsplit('.', 1)[1], ip_w), 'dim')}"
               f"  {ui.fit(d['kind'] or '—', 13)} {ui.fit(lat, 8, right=True)}")
        rest = cols - ui.vlen(row) - 2
        if d["services"] and rest >= 8:
            row += "  " + ui.paint(ui.fit(d["services"], rest).rstrip(), "dim")
        print(row.rstrip())


def main(argv):
    as_json = "--json" in argv
    ip, ips = link.subnet("wlan0")
    with ThreadPoolExecutor(3) as ex:
        ts_f, info_f = ex.submit(tsdata.fetch), ex.submit(gather.link_info, ip)
        scan_f = ex.submit(gather.scan, ips) if ips else None
        t0 = time.monotonic()
        with ui.Wait("Midiendo la conexión…"):
            info = info_f.result()
            ts = ts_f.result()[0]
        if not as_json:
            show_link(info, tsdata.me(ts)[1] if ts else None)
        with ui.Wait("Buscando equipos en la red…"):
            icmp, tcp = scan_f.result() if scan_f else ({}, {})
            devs = gather.devices(ip, info["router"], icmp, tcp, tsdata.lan_names(ts)) if ip else []
    if as_json:
        json.dump({**info, "devices": devs}, sys.stdout, ensure_ascii=False, indent=2)
        print()
        return 0
    if devs:
        show_devices(devs, f"{ip.rsplit('.', 1)[0]}.0/24")
    legend = " · en negrita, los de Tailscale" if ui.COLOR else ""
    print("\n" + ui.paint(f"Medido en {num(time.monotonic() - t0)} s{legend}", "dim"))
    return 0
