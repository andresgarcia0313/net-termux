"""Formato es-CO: coma decimal, tamaños y fechas relativas."""
from datetime import datetime, timezone


def num(x, dec=1):
    """Número en es-CO: coma decimal."""
    return f"{x:.{dec}f}".replace(".", ",")


def size(b):
    for unit in ("B", "KB", "MB", "GB"):
        if b < 1024 or unit == "GB":
            return f"{num(b, 0 if unit == 'B' else 1)} {unit}"
        b /= 1024


def seconds_from_now(iso):
    """Segundos hasta una fecha ISO (negativo si ya pasó); None si no es fecha."""
    try:
        t = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None
    return (t - datetime.now(timezone.utc)).total_seconds()


def span(iso):
    """'hace 2 meses' o 'en 50 días'."""
    s = seconds_from_now(iso)
    if s is None:
        return ""
    a = abs(s)
    for limit, div, one, many in ((3600, 60, "minuto", "minutos"), (86400, 3600, "hora", "horas"),
                                  (5184000, 86400, "día", "días"), (63072000, 2592000, "mes", "meses"),
                                  (1e12, 31536000, "año", "años")):
        if a < limit:
            n = max(int(a // div), 1)
            return f"{'en' if s > 0 else 'hace'} {n} {one if n == 1 else many}"
