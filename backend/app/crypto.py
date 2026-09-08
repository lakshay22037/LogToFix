import os

from cryptography.fernet import Fernet, InvalidToken

# Encrypts secrets that must actually be protected at rest (currently: a
# user's GitHub PAT for the "Open PR" feature) — unlike cloud log-source
# config, which deliberately never collects credentials at all, a GitHub
# token is a real secret we choose to store, so it must not sit in
# plaintext. FERNET_KEY must be a urlsafe-base64 32-byte key
# (Fernet.generate_key()); set once per deployment and kept out of git.
_KEY = os.environ.get("FERNET_KEY")
_fernet = Fernet(_KEY) if _KEY else None


class CryptoNotConfigured(Exception):
    pass


def encrypt_secret(plaintext: str) -> str:
    if _fernet is None:
        raise CryptoNotConfigured("FERNET_KEY is not set")
    return _fernet.encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext: str) -> str:
    if _fernet is None:
        raise CryptoNotConfigured("FERNET_KEY is not set")
    try:
        return _fernet.decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        raise CryptoNotConfigured("Stored secret cannot be decrypted with current FERNET_KEY") from exc
