"""站台主金鑰加密（移植自 finance-digest-a，未改動）。

    主金鑰 mk           隨機 32 bytes，所有報告共用；存在 keyring.json 時一定是被包起來的
    kek = PBKDF2(密碼, salt)          每次包裝都換新的 salt 與 iv
    keyring = AESGCM(kek).encrypt(mk)
    報告 = AESGCM(mk).encrypt(gzip(明文))   每份檔案都用新的隨機 iv

格式與瀏覽器 WebCrypto 相容（PBKDF2-SHA256、AES-GCM 256、密文後接 16 bytes tag、gzip 用 DecompressionStream 解）。
這裡沒有任何常數 salt 或 iv；換密碼只要重新包 mk，但 git 歷史裡的舊 keyring 仍能用舊密碼解開，
要真正停用舊密碼必須換 mk 並重新加密全部報告（寫在 README）。
"""
from __future__ import annotations

import base64
import gzip
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

VERSION = 1
ITERATIONS = 310_000   # PBKDF2 是 WebCrypto 唯一可用的 KDF，迭代數就是防線
AAD_KEY = b"fd-keyring-v1"
AAD_CONTENT = b"fd-content-v1"


class WrongPassword(ValueError):
    pass


def _b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def _unb64(s: str) -> bytes:
    return base64.b64decode(s.encode("ascii"))


def _kek(password: str, salt: bytes, iterations: int = ITERATIONS) -> bytes:
    return PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=iterations).derive(password.encode("utf-8"))


def new_master_key() -> bytes:
    return os.urandom(32)


def wrap_key(mk: bytes, password: str) -> dict:
    salt, iv = os.urandom(16), os.urandom(12)
    wrapped = AESGCM(_kek(password, salt)).encrypt(iv, mk, AAD_KEY)
    return {"v": VERSION, "kdf": {"alg": "PBKDF2-SHA256", "iter": ITERATIONS},
            "salt": _b64(salt), "iv": _b64(iv), "wrapped": _b64(wrapped)}


def unwrap_key(ring: dict, password: str) -> bytes:
    try:
        return AESGCM(_kek(password, _unb64(ring["salt"]), ring["kdf"]["iter"])).decrypt(
            _unb64(ring["iv"]), _unb64(ring["wrapped"]), AAD_KEY)
    except InvalidTag as ex:
        raise WrongPassword("密碼錯誤，解不開主金鑰") from ex


def seal(plaintext: str, mk: bytes) -> dict:
    iv = os.urandom(12)
    ct = AESGCM(mk).encrypt(iv, gzip.compress(plaintext.encode("utf-8"), mtime=0), AAD_CONTENT)
    return {"v": VERSION, "iv": _b64(iv), "ct": _b64(ct), "encoding": "gzip"}


def open_sealed(env: dict, mk: bytes) -> str:
    raw = AESGCM(mk).decrypt(_unb64(env["iv"]), _unb64(env["ct"]), AAD_CONTENT)
    return gzip.decompress(raw).decode("utf-8")
