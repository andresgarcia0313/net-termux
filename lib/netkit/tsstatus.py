"""`tailscale status` en Termux: equipos e IP de la tailnet, medidos desde el teléfono."""
import json, sys, time
from concurrent.futures import ThreadPoolExecutor

from . import names, tsapi, tsdata, tslive, ui
from .fmt import ago
from .tsstate import ipv4, key_note, state_of

HELP_API = "Para la lista completa sin otro equipo: crea un cliente OAuth de solo lectura (README)."


def show_me(ip, me, tailnet):
    ui.title("Tailscale", tailnet)
    if not ip:
        ui.line("off", "Apagado en este teléfono", "Actívalo en la app de Tailscale.")
        return
    ui.line("me", "Este teléfono" + (f" · {me['name']}" if me else ""))
    v6 = next((a for a in (me or {}).get("ips", []) if ":" in a), "")
    print(f"  {ui.paint(ip, 'bold')}" + (ui.paint(f" · {v6}", "dim") if v6 else ""))
    note = key_note(me or {})
    if note:
        ui.line(note[0], note[1].capitalize(), "Renuévala en login.tailscale.com › Machines.")


def show_peer(p, live, fresh, name_w, cols, verbose):
    ms, tcp = live[0].get(ipv4(p)), ipv4(p) in live[1]
    state, right, online = state_of(p, ms, tcp, fresh, cols >= 64)
    kind = names.TS_OS.get(p["os"], p["os"].capitalize())
    row = f"{ui.mark(state)} {ui.fit(p['name'], name_w)}  {ui.fit(ipv4(p) or '—', 15)} "
    print(row + (f"{ui.fit(kind, 8)} " if cols >= 64 else "") + right)
    extra = [key_note(p)[1]] if key_note(p) else []
    if p.get("exit_node"):
        extra.append("nodo de salida en uso")
    if verbose:
        extra += [a for a in p["ips"] if ":" in a]
        if p.get("version"):
            extra.append(f"v{p['version']}" + (" (hay actualización)" if p.get("update") else ""))
    if extra:
        print("  " + ui.paint(" · ".join(extra), "dim"))
    return online


def main(argv):
    verbose = "-v" in argv or "--verbose" in argv
    with ui.Wait("Consultando la tailnet…"):
        data, fresh = tsdata.fetch()
    if "--json" in argv:
        json.dump(data or {}, sys.stdout, indent=2, ensure_ascii=False)
        print()
        return 0 if data else 1
    ip, me = tsdata.me(data)
    show_me(ip, me, (data or {}).get("tailnet", ""))
    if not data:
        ui.line("warn", "Aún no conozco los demás equipos", HELP_API)
        return 1
    peers = sorted((p for p in data["peers"] if p is not me), key=lambda p: p["name"].lower())
    targets = [ipv4(p) for p in peers if ipv4(p)] if ip else []
    with ui.Wait("Midiendo desde el teléfono…"), ThreadPoolExecutor(2) as ex:
        live_f = ex.submit(tslive.measure, targets)
        dns = ex.submit(tslive.names, targets).result() if not fresh and targets else {}
        live = live_f.result()
    for p in peers:
        p["name"] = dns.get(ipv4(p), "").split(".")[0] or p["name"]
    cols = ui.width()
    name_w = min(max(len(p["name"]) for p in peers), 20 if cols >= 64 else 14)
    reach = [p for p in peers if ipv4(p) in live[0] or ipv4(p) in live[1] or (fresh and p["online"])]
    ui.title("Equipos", f"{len(reach)} de {len(peers)} en línea")
    for p in sorted(peers, key=lambda p: p not in reach):
        show_peer(p, live, fresh, name_w, cols, verbose)
    age = time.time() - data.get("at", 0)
    origin = f"{data['source']} (ahora)" if fresh else f"copia guardada {ago(age)}"
    print("\n" + ui.paint(f"Lista: {origin} · estado medido desde aquí", "dim"))
    if not fresh and not tsapi.credentials():
        print(ui.paint(HELP_API, "dim"))
    return 0
