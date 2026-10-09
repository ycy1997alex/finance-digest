import pytest

from fd.crypto import WrongPassword, new_master_key, open_sealed, seal, unwrap_key, wrap_key


def test_keyring_roundtrip_and_wrong_password():
    mk = new_master_key()
    ring = wrap_key(mk, "正確密碼")
    assert unwrap_key(ring, "正確密碼") == mk
    with pytest.raises(WrongPassword):
        unwrap_key(ring, "錯誤密碼")
    assert "正確密碼" not in str(ring) and mk.hex() not in str(ring)


def test_every_wrap_and_seal_uses_fresh_salt_and_iv():
    # AES-GCM 在同一把金鑰下重用 IV 會直接洩漏明文，所以每次都要不同
    mk = new_master_key()
    a, b = wrap_key(mk, "pw"), wrap_key(mk, "pw")
    assert a["salt"] != b["salt"] and a["iv"] != b["iv"]
    s1, s2 = seal("同一份報告", mk), seal("同一份報告", mk)
    assert s1["iv"] != s2["iv"] and s1["ct"] != s2["ct"]


def test_seal_roundtrip_and_tamper_detection():
    mk = new_master_key()
    env = seal("📅 2026/10/03 財經節目綜合摘要\n" * 50, mk)
    assert open_sealed(env, mk).startswith("📅 2026/10/03")
    assert "財經" not in str(env)
    bad = dict(env, ct=env["ct"][:-4] + ("AAAA" if not env["ct"].endswith("AAAA") else "BBBB"))
    with pytest.raises(Exception):
        open_sealed(bad, mk)
    with pytest.raises(Exception):
        open_sealed(env, new_master_key())
