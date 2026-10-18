"""Sondas sin root y sin procesos hijos (Android cierra Termux si crea muchos procesos).

ICMP por socket de datagrama (Android permite ping sin privilegios) leyendo el TTL,
y TCP connect no bloqueante: un RST también prueba que el equipo existe.
"""
import errno, selectors, socket, struct, time

IP_RECVTTL = 12  # Python en Android no exporta la constante
IP_TTL_CMSG = 2
PORTS = (22, 80, 443, 445, 554, 8009, 62078)


def _icmp():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_ICMP)
    s.setsockopt(socket.IPPROTO_IP, IP_RECVTTL, 1)
    s.setblocking(False)
    return s


def sweep(ips, wait=1.0, tries=2):
    """Ping a muchas IP con un solo socket -> {ip: (ms, ttl)}."""
    found = {}
    try:
        s = _icmp()
    except OSError:
        return found
    sel = selectors.DefaultSelector()
    sel.register(s, selectors.EVENT_READ)
    for n in range(tries):
        sent = {}
        for ip in ips:
            if ip not in found:
                try:
                    s.sendto(struct.pack("!BBHHH", 8, 0, 0, 0, n) + b"net-stat", (ip, 0))
                    sent[ip] = time.monotonic()
                except OSError:
                    pass
        end = time.monotonic() + wait
        while sent.keys() - found.keys() and (left := end - time.monotonic()) > 0:
            if not sel.select(left):
                break
            try:
                data, anc, _, addr = s.recvmsg(128, 64)
            except OSError:
                continue
            ip = addr[0]
            if ip in sent and ip not in found and data[:1] == b"\0":
                ttl = next((int.from_bytes(d, "little") for _, t, d in anc if t == IP_TTL_CMSG), 0)
                found[ip] = ((time.monotonic() - sent[ip]) * 1000, ttl)
    sel.close()
    s.close()
    return found


def ping(ip, wait=1.5):
    return sweep([ip], wait, 2).get(ip, (None, 0))[0]


def tcp_scan(ips, ports=PORTS, wait=1.2):
    """{ip: {puertos abiertos}} para cada IP que contestó (abierto o RST)."""
    out, sel = {}, selectors.DefaultSelector()
    for ip in ips:
        for p in ports:
            s = socket.socket()
            s.setblocking(False)
            if s.connect_ex((ip, p)) in (0, errno.EINPROGRESS):
                sel.register(s, selectors.EVENT_WRITE, (ip, p))
            else:
                s.close()
    end = time.monotonic() + wait
    while sel.get_map() and (left := end - time.monotonic()) > 0:
        for key, _ in sel.select(left) or []:
            ip, p = key.data
            err = key.fileobj.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
            if err == 0:
                out.setdefault(ip, set()).add(p)
            elif err == errno.ECONNREFUSED:
                out.setdefault(ip, set())
            sel.unregister(key.fileobj)
            key.fileobj.close()
    for key in list(sel.get_map().values()):
        key.fileobj.close()
    sel.close()
    return out


def dns_query(server, name="google.com", wait=0.8):
    """Latencia en ms de una consulta DNS tipo A a `server`, o None."""
    q = b"\x4e\x53\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00"
    q += b"".join(bytes([len(p)]) + p.encode() for p in name.split(".")) + b"\0\0\1\0\1"
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.settimeout(wait)
        t = time.monotonic()
        try:
            s.sendto(q, (server, 53))
            s.recv(512)
        except OSError:
            return None
    return (time.monotonic() - t) * 1000
