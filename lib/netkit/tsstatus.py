"""`tailscale status` en Termux: la tailnet con latencia medida desde el teléfono."""
import json, os, sys

from . import names, probe, tsdata, ui
from .fmt import seconds_from_now, size, span

KEY_WARN_DAYS = 30


def key_note(node):
    """(estado, texto) del vencimiento de la clave, o None si no preocupa."""
    s = seconds_from_now(node.get("KeyExpiry") or "")
    if s is None or s > KEY_WARN_DAYS * 86400:
        return None
    return ("bad", "clave vencida") if s <= 0 else ("warn", f"la clave vence {span(node['KeyExpiry'])}")


def show_me(ip, me, data):
    ui.title("Tailscale", data.get("MagicDNSSuffix", ""))
    if not ip:
        ui.line("off", "Apagado en este teléfono", "Actívalo en la app de Tailscale para entrar a los equipos.")
        return
    ui.line("me", f"Este teléfono · {tsdata.short(me) if me else ''} · {ip}".replace(" ·  ·", " ·"))
    note = key_note(me or {})
    if note:
        ui.line(note[0], note[1][0].upper() + note[1][1:], "Renuévala en login.tailscale.com › Machines.")


def peer_row(n, lat, name_w, cols, verbose, source):
    online = n.get("Online")
    note = key_note(n)
    if online:
        state, right = ("warn" if note else "ok"), ui.ms(lat, 60, 200)
    else:
        state, right = ("bad" if note and note[0] == "bad" else "off"), ui.paint(
            f"{'desconectado' if cols >= 64 else 'visto'} {span(n.get('LastSeen', ''))}".strip(), "dim")
    ip4 = next((a for a in n.get("TailscaleIPs", []) if "." in a), "")
    kind = names.TS_OS.get(n.get("OS", ""), n.get("OS", "").capitalize())
    row = f"{ui.mark(state)} {ui.fit(tsdata.short(n), name_w)}  "
    row += (f"{ui.paint(ui.fit(ip4, 15), 'dim')} " if cols >= 64 else "") + f"{ui.fit(kind, 8)} {right}"
    print(row)
    extra = [note[1]] if note else []
    if n.get("ExitNode"):
        extra.append("nodo de salida en uso")
    if verbose and online and (n.get("RxBytes") or n.get("TxBytes")):
        extra.append(f"tráfico con {source}: ↓ {size(n['RxBytes'])} ↑ {size(n['TxBytes'])}")
    if extra:
        print("  " + ui.paint(" · ".join(extra), "dim"))


def main(argv):
    verbose = "-v" in argv or "--verbose" in argv
    with ui.Wait("Consultando la tailnet…"):
        data, source, age = tsdata.fetch()
    if not data:
        hosts = tsdata.sources()
        if not hosts:
            ui.line("warn", "Falta un equipo con el CLI de Tailscale",
                    f"Escribe su nombre SSH en {tsdata.CONFIG.replace(os.path.expanduser('~'), '~')} (uno por línea).")
        else:
            ui.line("bad", "No pude leer el estado de Tailscale",
                    f"Ninguno contestó por SSH: {', '.join(hosts)}. Prueba: ssh {hosts[0]} tailscale status")
        return 1
    if "--json" in argv:
        json.dump(data, sys.stdout, indent=2)
        print()
        return 0
    ip, me = tsdata.me(data)
    show_me(ip, me, data)
    peers = [n for n in tsdata.nodes(data) if n is not me]
    online = [n for n in peers if n.get("Online")]
    targets = {n["TailscaleIPs"][0]: n for n in online if ip and n.get("TailscaleIPs")}
    with ui.Wait("Midiendo latencia desde el teléfono…"):
        lat = probe.sweep(list(targets), wait=1.5)
    peers.sort(key=lambda n: (not n.get("Online"), tsdata.short(n).lower()))
    ui.title("Equipos", f"{len(online)} de {len(peers)} en línea")
    cols = ui.width()
    name_w = min(max(len(tsdata.short(n)) for n in peers), 20 if cols >= 60 else 16)
    for n in peers:
        first = (n.get("TailscaleIPs") or [""])[0]
        peer_row(n, lat.get(first, (None, 0))[0], name_w, cols, verbose, source)
    when = "ahora" if age < 60 else f"guardado {span_secs(age)}"
    print("\n" + ui.paint(f"Datos vistos desde {source} ({when}) · latencia medida desde aquí", "dim"))
    return 0


def span_secs(age):
    m = int(age // 60)
    return f"hace {m} min" if m < 120 else f"hace {m // 60} h"
