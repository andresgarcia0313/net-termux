"""Estado de cada equipo de la tailnet: fuente + medición en vivo + vencimiento de clave."""
from . import ui
from .fmt import seconds_from_now, span

KEY_WARN_DAYS = 30


def key_note(peer):
    """(estado, texto) del vencimiento de la clave, o None si no preocupa."""
    when = peer.get("key_expiry") or ""
    s = seconds_from_now(when)
    if s is None or s > KEY_WARN_DAYS * 86400:
        return None
    return ("bad", "clave vencida") if s <= 0 else ("warn", f"la clave vence {span(when)}")


def ipv4(peer):
    return next((a for a in peer["ips"] if "." in a), "")


def state_of(p, ms, tcp, fresh, wide):
    """(estado, texto de la derecha, en_línea) combinando la fuente y lo medido en vivo."""
    note = key_note(p)
    if ms is not None or tcp:
        return (note[0] if note else "ok"), ui.ms(ms, 60, 200) if ms is not None else ui.paint("sin ping", "dim"), True
    if fresh and p["online"]:
        return "warn", ui.paint("no responde desde aquí", "warn"), True
    if fresh or p["last_seen"]:
        seen = span(p["last_seen"])
        text = (f"desconectado {seen}" if wide else seen) if seen else "desconectado"
        return ("bad" if note and note[0] == "bad" else "off"), ui.paint(text, "dim"), False
    return "off", ui.paint("sin respuesta", "dim"), False
