"""Presentación en terminal con criterio HIG de Apple.

Jerarquía por peso (negrita/atenuado) y no por más columnas; color semántico que
nunca va solo (forma + palabra); ancho adaptable; sin color si no hay TTY o NO_COLOR.
"""
import os, re, shutil, sys, threading, time

TTY = sys.stdout.isatty()
COLOR = TTY and "NO_COLOR" not in os.environ and os.environ.get("TERM") != "dumb"
_SGR = {"ok": "32", "warn": "33", "bad": "31", "dim": "2", "bold": "1", "accent": "36"}
MARK = {"ok": "●", "warn": "◐", "bad": "✕", "off": "○", "me": "◆"}
_ANSI = re.compile(r"\033\[[0-9;]*m")


def paint(text, style=""):
    return f"\033[{_SGR[style]}m{text}\033[0m" if COLOR and style else str(text)


def mark(state):
    return paint(MARK[state], "dim" if state == "off" else "accent" if state == "me" else state)


def width():
    return shutil.get_terminal_size((80, 24)).columns


def vlen(text):
    return len(_ANSI.sub("", text))


def fit(text, n, right=False):
    """Recorta con … y rellena por ancho visible (ignora códigos de color)."""
    plain = _ANSI.sub("", text)
    if len(plain) > n:
        return plain[: max(n - 1, 0)] + "…"
    pad = " " * (n - len(plain))
    return pad + text if right else text + pad


def title(text, extra=""):
    print("\n" + paint(text, "bold") + (paint(f" · {extra}", "dim") if extra else ""))


def line(state, text, detail=""):
    print(f"{mark(state)} {text}")
    if detail:
        print("  " + paint(detail, "dim"))


def ms(value, warn=80, bad=200):
    """Latencia con su color de estado; la cifra siempre se lee igual sin color."""
    if value is None:
        return paint("sin respuesta", "dim")
    style = "ok" if value < warn else "warn" if value < bad else "bad"
    return paint(f"{value:.0f} ms", style)


class Wait:
    """Muestra algo de inmediato mientras se mide (HIG: Loading › Show something as soon as possible)."""

    def __init__(self, text):
        self.text, self._stop = text, threading.Event()

    def __enter__(self):
        if TTY:
            threading.Thread(target=self._spin, daemon=True).start()
        return self

    def _spin(self):
        frames = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        i = 0
        while not self._stop.wait(0.1):
            sys.stderr.write(f"\r{paint(frames[i % 10], 'accent')} {paint(self.text, 'dim')}\033[K")
            sys.stderr.flush()
            i += 1

    def __exit__(self, *exc):
        self._stop.set()
        if TTY:
            time.sleep(0.12)
            sys.stderr.write("\r\033[K")
            sys.stderr.flush()
