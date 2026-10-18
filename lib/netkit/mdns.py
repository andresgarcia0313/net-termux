"""Nombre mDNS de una IP: consulta PTR a 224.0.0.251:5353, sin dependencias.

Se envía desde un puerto efímero, así el responder (Avahi, Bonjour) contesta en
unicast de vuelta (respuesta "legacy unicast" del RFC 6762, sección 6.7).
"""
import socket, struct, time

MDNS = ("224.0.0.251", 5353)
PTR, CLASS_IN = 12, 1


def _query(ip):
    labels = list(reversed(ip.split("."))) + ["in-addr", "arpa"]
    qname = b"".join(bytes([len(p)]) + p.encode() for p in labels) + b"\0"
    return struct.pack("!6H", 0x6E73, 0, 1, 0, 0, 0) + qname + struct.pack("!HH", PTR, CLASS_IN)


def _read_name(data, off, depth=0):
    labels = []
    while off < len(data) and depth < 10:
        n = data[off]
        if n == 0:
            break
        if n & 0xC0 == 0xC0:  # puntero de compresión
            labels.append(_read_name(data, ((n & 0x3F) << 8) | data[off + 1], depth + 1))
            break
        labels.append(data[off + 1: off + 1 + n].decode("utf-8", "replace"))
        off += 1 + n
    return ".".join(x for x in labels if x)


def _skip_name(data, off):
    while data[off]:
        if data[off] & 0xC0 == 0xC0:
            return off + 2
        off += 1 + data[off]
    return off + 1


def _ptr_answer(data):
    try:
        qd, an = struct.unpack("!HH", data[4:8])
        off = 12
        for _ in range(qd):
            off = _skip_name(data, off) + 4
        for _ in range(an):
            off = _skip_name(data, off)
            rtype, _, _, rdlen = struct.unpack("!HHIH", data[off: off + 10])
            off += 10
            if rtype == PTR:
                return _read_name(data, off)
            off += rdlen
    except (IndexError, struct.error):
        pass
    return ""


def reverse(ip, wait=0.8):
    """'192.168.1.20' -> 'nas' (sin '.local'), o '' si nadie responde."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 255)
        end = time.monotonic() + wait
        try:
            s.sendto(_query(ip), MDNS)
            while (left := end - time.monotonic()) > 0:
                s.settimeout(left)
                name = _ptr_answer(s.recv(4096))
                if name:
                    return name.removesuffix(".local")
        except OSError:
            pass
    return ""
