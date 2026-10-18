import os, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
os.environ["NO_COLOR"] = "1"

from netkit import tsapi, tsstate as tsstatus  # noqa: E402

PEER = {"name": "nas", "ips": ["100.64.0.20", "fd7a::20"], "os": "linux", "online": True,
        "last_seen": "", "key_expiry": "", "endpoints": []}


def test_api_device_is_normalized():
    d = {"name": "nas.ejemplo.ts.net", "hostname": "NAS", "addresses": ["100.64.0.20"], "os": "linux",
         "connectedToControl": True, "lastSeen": "2026-01-01T00:00:00Z", "keyExpiryDisabled": True,
         "expires": "2026-02-01T00:00:00Z", "clientVersion": "1.80.2-t123", "updateAvailable": True,
         "clientConnectivity": {"endpoints": ["192.168.1.20:41641"]}}
    p = tsapi._device(d)
    assert (p["name"], p["ips"], p["online"], p["key_expiry"], p["version"], p["update"]) == (
        "nas", ["100.64.0.20"], True, "", "1.80.2", True)
    assert p["endpoints"] == ["192.168.1.20:41641"]


def test_credentials_order(tmp_path, monkeypatch):
    for k in ("TS_API_KEY", "TS_OAUTH_CLIENT_ID", "TS_OAUTH_CLIENT_SECRET"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr(tsapi, "CONF", str(tmp_path / "no-existe"))
    assert tsapi.credentials() is None
    conf = tmp_path / "api"
    conf.write_text("id123 tskey-client-x-y\n")
    monkeypatch.setattr(tsapi, "CONF", str(conf))
    assert tsapi.credentials() == ("oauth", ("id123", "tskey-client-x-y"))
    monkeypatch.setenv("TS_API_KEY", "tskey-api-z")
    assert tsapi.credentials() == ("key", "tskey-api-z")


def test_state_combines_source_and_live():
    assert tsstatus.state_of(PEER, 12.0, False, True, True)[0::2] == ("ok", True)
    assert tsstatus.state_of(PEER, None, True, False, True)[0::2] == ("ok", True)
    assert tsstatus.state_of(PEER, None, False, True, True)[0::2] == ("warn", True)
    off = dict(PEER, online=False, last_seen="2000-01-01T00:00:00Z")
    state, text, online = tsstatus.state_of(off, None, False, True, True)
    assert (state, online) == ("off", False) and text.startswith("desconectado hace")
    assert tsstatus.state_of(dict(PEER, online=False), None, False, False, True)[0::2] == ("off", False)
    assert tsstatus.ipv4(PEER) == "100.64.0.20"
