import os, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
os.environ["NO_COLOR"] = "1"

from netkit import fmt, link, names, netstatus, tsdata, ui
from netkit import tsstate as tsstatus  # noqa: E402


def test_fmt_es_co():
    assert fmt.num(3.14159) == "3,1"
    assert fmt.size(97261452) == "92,8 MB"
    assert fmt.size(512) == "512 B"
    assert fmt.span("2000-01-01T00:00:00Z").startswith("hace ")
    assert fmt.span("2999-01-01T00:00:00Z").startswith("en ")
    assert fmt.span("no es fecha") == ""


def test_fit_keeps_visible_width():
    assert ui.fit("hola mundo", 6) == "hola …"
    assert ui.fit("ab", 4) == "ab  "
    assert ui.fit("ab", 4, right=True) == "  ab"
    assert ui.vlen("\033[32mok\033[0m") == 2


def test_signal_and_band():
    assert link.signal(-40) == ("ok", "excelente")
    assert link.signal(-70) == ("warn", "regular")
    assert link.signal(-85) == ("bad", "débil")
    assert link.band(5745) == "5 GHz" and link.band(2437) == "2,4 GHz" and link.band(0) == ""


def test_kind_prefers_tailscale_then_ports_then_ttl():
    assert names.kind(64, {22, 445}, "windows") == "Windows"
    assert names.kind(64, {62078}) == "iPhone/iPad"
    assert names.kind(128, {445}) == "Windows"
    assert names.kind(64, {22, 445}) == "Linux"
    assert names.kind(63, {80, 443}) == "Equipo de red"
    assert names.kind(0, set()) == ""
    assert names.services({445, 22}) == "ssh smb"


def test_isp_is_readable():
    assert netstatus.isp("AS64500 EJEMPLO TELECOMUNICACIONES S.A.") == "Ejemplo Telecomunicaciones"
    assert netstatus.isp("") == ""


def test_key_note():
    assert tsstatus.key_note({"key_expiry": "2000-01-01T00:00:00Z"}) == ("bad", "clave vencida")
    assert tsstatus.key_note({"key_expiry": "2999-01-01T00:00:00Z"}) is None
    assert tsstatus.key_note({}) is None


def test_lan_names_from_curaddr_and_self_addrs():
    data = {"Self": {"DNSName": "nas.example.ts.net.", "OS": "linux", "Addrs": ["192.168.1.17:41641"]},
            "Peer": {"a": {"HostName": "laptop", "OS": "linux", "CurAddr": "192.168.1.31:41641"}}}
    norm = tsdata.from_status(data, "nas por SSH")
    assert tsdata.lan_names(norm) == {"192.168.1.17": ("nas", "linux"), "192.168.1.31": ("laptop", "linux")}
    assert [p["online"] for p in norm["peers"]] == [True, False]
    assert tsdata.lan_names(None) == {}


def test_sources_from_env_and_file(tmp_path, monkeypatch):
    monkeypatch.setenv("NET_TERMUX_TS_HOSTS", "nas, laptop")
    assert tsdata.sources() == ("nas", "laptop")
    monkeypatch.delenv("NET_TERMUX_TS_HOSTS")
    conf = tmp_path / "hosts"
    conf.write_text("# comentario\nservidor  # el 24/7\nportatil\n")
    monkeypatch.setattr(tsdata, "CONFIG", str(conf))
    assert tsdata.sources() == ("servidor", "portatil")
    monkeypatch.setattr(tsdata, "CONFIG", str(tmp_path / "no-existe"))
    assert tsdata.sources() == ()


def test_mdns_ptr_answer_with_compression():
    from netkit import mdns
    q = mdns._query("192.168.1.20")
    assert b"\x0220\x011\x03168\x03192\x07in-addr\x04arpa\x00" in q
    qname = q[12:-4]
    answer = (b"\x00\x00\x84\x00\x00\x00\x00\x01\x00\x00\x00\x00" + qname
              + b"\x00\x0c\x80\x01\x00\x00\x00\x78\x00\x0c" + b"\x04caja\x05local\x00")
    assert mdns._ptr_answer(answer) == "caja.local"
    assert mdns._ptr_answer(b"\x00" * 5) == ""
