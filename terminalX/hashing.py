# Largely taken from https://nitratine.net/blog/post/how-to-hash-passwords-in-python/


import base64
import hashlib
import os


def hash_password(password: str) -> str:
    salt = os.urandom(32)

    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        100000
    )
    for_storage = salt + key
    return base64.b64encode(for_storage).decode()


def verify_hash(password: str, password_hash_b64: str):
    password_hash_bytes = base64.b64decode(password_hash_b64)
    salt = password_hash_bytes[:32]
    key = password_hash_bytes[32:]
    new_key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        100000
    )
    return new_key == key
