import configparser
import os
import base64
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.fernet import Fernet, InvalidToken
from database import db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

config = configparser.ConfigParser()
config.read(os.path.join(BASE_DIR, "config.ini"))

# Datenbankpfad und Backup-Maximalzahl
DB_FILE = config.get("database", "db_file")
MAX_BACKUPS = config.getint("database", "max_backups")

# WebDAV - jetzt aus Programmvariablen und Keyring
# Diese werden durch init_webdav_config() initialisiert
WEBDAV_USER = ""
WEBDAV_PASSWORD = ""
WEBDAV_URL = ""

# Cache für lazy loading
_webdav_config_loaded = False
_derived_key = None
_passphrase_check_value = "db-unlock-check"
_passphrase_set_name = "db_passphrase_set"
_passphrase_check_name = "db_passphrase_check"


def use_passphrase_mode():
    return config.getboolean("security", "use_passphrase", fallback=False)


def _get_passphrase_salt():
    salt = config.get("security", "passphrase_salt", fallback="").strip()
    if salt:
        return base64.urlsafe_b64decode(salt.encode("utf-8"))
    raw = os.urandom(16)
    if not config.has_section("security"):
        config.add_section("security")
    config.set("security", "passphrase_salt", base64.urlsafe_b64encode(raw).decode("utf-8"))
    with open(os.path.join(BASE_DIR, "config.ini"), "w") as f:
        config.write(f)
    return raw


def _derive_key(passphrase: str) -> str:
    salt = _get_passphrase_salt()
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=200_000,
    )
    return base64.urlsafe_b64encode(kdf.derive(passphrase.encode("utf-8"))).decode("utf-8")


def set_passphrase(passphrase: str):
    global _derived_key
    _derived_key = _derive_key(passphrase)


def is_passphrase_initialized() -> bool:
    try:
        from models import Programmvariable
        check_var = Programmvariable.query.filter_by(name=_passphrase_check_name).first()
        return bool(check_var and check_var.wert)
    except Exception:
        return False


def should_force_passphrase_prompt() -> bool:
    try:
        from models import Programmvariable
        set_var = Programmvariable.query.filter_by(name=_passphrase_set_name).first()
        return bool(set_var and set_var.wert == "0")
    except Exception:
        return False


def mark_passphrase_prompt_done():
    try:
        from models import Programmvariable
        set_var = Programmvariable.query.filter_by(name=_passphrase_set_name).first()
        if set_var:
            set_var.wert = "1"
            db.session.commit()
    except Exception:
        return


def set_new_passphrase(passphrase: str):
    global _derived_key
    key = _derive_key(passphrase)
    _derived_key = key
    token = Fernet(key.encode("utf-8")).encrypt(_passphrase_check_value.encode("utf-8")).decode("utf-8")
    from models import Programmvariable
    set_var = Programmvariable.query.filter_by(name=_passphrase_set_name).first()
    check_var = Programmvariable.query.filter_by(name=_passphrase_check_name).first()
    if not set_var:
        set_var = Programmvariable(name=_passphrase_set_name, bezeichnung="DB Passwort gesetzt (0/1)", wert="1")
        db.session.add(set_var)
    if not check_var:
        check_var = Programmvariable(name=_passphrase_check_name, bezeichnung="DB Passwort Prüftoken", wert="")
        db.session.add(check_var)
    set_var.wert = "1"
    check_var.wert = token
    db.session.commit()


def verify_passphrase(passphrase: str) -> bool:
    try:
        from models import Programmvariable
        check_var = Programmvariable.query.filter_by(name=_passphrase_check_name).first()
        if not check_var or not check_var.wert:
            return False
        key = _derive_key(passphrase)
        fernet = Fernet(key.encode("utf-8"))
        fernet.decrypt(check_var.wert.encode("utf-8"))
        global _derived_key
        _derived_key = key
        return True
    except InvalidToken:
        return False
    except Exception:
        return False


def is_encryption_ready():
    if use_passphrase_mode():
        return bool(os.getenv("ENCRYPTION_KEY") or _derived_key)
    if os.getenv("ENCRYPTION_KEY"):
        return True
    if _derived_key:
        return True
    key = config.get("security", "encryption_key", fallback="").strip()
    return bool(key)


def get_encryption_key():
    """Returns encryption key for field-level encryption"""
    env_key = os.getenv("ENCRYPTION_KEY")
    if env_key and env_key.strip():
        return env_key.strip()
    if _derived_key:
        return _derived_key
    if use_passphrase_mode():
        return ""
    key = config.get("security", "encryption_key", fallback="").strip()
    if key:
        return key
    # Auto-generate and persist key if missing
    try:
        raw = os.urandom(32)
        key = base64.urlsafe_b64encode(raw).decode("utf-8")
        if not config.has_section("security"):
            config.add_section("security")
        config.set("security", "encryption_key", key)
        with open(os.path.join(BASE_DIR, "config.ini"), "w") as f:
            config.write(f)
        return key
    except Exception:
        return ""

def get_webdav_config():
    """Gibt WebDAV-Konfiguration zurück, lädt sie bei Bedarf"""
    global _webdav_config_loaded, WEBDAV_USER, WEBDAV_PASSWORD, WEBDAV_URL
    if not _webdav_config_loaded:
        init_webdav_config()
        _webdav_config_loaded = True
    return {
        'user': WEBDAV_USER,
        'password': WEBDAV_PASSWORD,
        'url': WEBDAV_URL
    }

def init_webdav_config():
    """Initialisiert WebDAV-Konfiguration aus DB und Keyring"""
    global WEBDAV_USER, WEBDAV_PASSWORD, WEBDAV_URL
    
    try:
        from models import Programmvariable
        # User aus DB
        user_var = Programmvariable.query.filter_by(name='webdav_user').first()
        WEBDAV_USER = user_var.wert if user_var else ""
        
        # URL aus DB
        url_var = Programmvariable.query.filter_by(name='webdav_pfad').first()
        WEBDAV_URL = url_var.wert if url_var else ""
        
        # Password aus Keyring
        import keyring
        WEBDAV_PASSWORD = keyring.get_password("webdav", "user") or ""
        
    except Exception as e:
        print(f"Fehler beim Laden der WebDAV-Konfiguration: {e}")
        # Bei Fehler bleiben die Werte leer