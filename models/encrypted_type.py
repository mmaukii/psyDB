from sqlalchemy.types import TypeDecorator, Text
from cryptography.fernet import Fernet, InvalidToken
from config import get_encryption_key


def _get_fernet():
    key = get_encryption_key()
    if not key:
        raise RuntimeError(
            "Missing ENCRYPTION_KEY. Set environment variable ENCRYPTION_KEY or "
            "[security].encryption_key in config.ini."
        )
    if isinstance(key, str):
        key = key.encode("utf-8")
    return Fernet(key)


class EncryptedString(TypeDecorator):
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value == "":
            return ""
        fernet = _get_fernet()
        token = fernet.encrypt(str(value).encode("utf-8"))
        return token.decode("utf-8")

    def process_result_value(self, value, dialect):
        if value is None or value == "":
            return value
        fernet = _get_fernet()
        try:
            return fernet.decrypt(value.encode("utf-8")).decode("utf-8")
        except InvalidToken:
            # Fallback for legacy plaintext values
            return value
