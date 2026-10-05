import os
import re
import json
import hashlib
from datetime import datetime
from config import BASE_DIR, DB_DIR, get_pen_drive_dir

# =====================================================================
# OFFICIAL LICENSE KEYS (8 to 12 Digits)
# =====================================================================
# Primary Demo Key: 7492-8160 (8 digits, ends with 8160 Admin PIN)
# Secondary Alias:  8160-2026 (8 digits)
DEMO_LICENSE_KEYS = ["74928160", "81602026"]

# Primary Master Key: 9281-6045-38 (10 digits, contains 8160 Admin PIN)
# Secondary Alias:   8160-2026-99 (10 digits)
MASTER_LICENSE_KEYS = ["9281604538", "8160202699"]

MAX_DEMO_LAUNCHES = 50
LICENSE_SALT = "WOKDENS_BIZDABBA_PHWP_2026_LICENSE_SECRET"

def normalize_key(raw_key: str) -> str:
    """Strips spaces, dashes, and non-alphanumeric chars for forgiving entry."""
    if not raw_key:
        return ""
    return re.sub(r'[^0-9A-Za-z]', '', str(raw_key)).strip()


def _get_license_file_path() -> str:
    """Returns persistent license file path on Pen Drive or local database dir."""
    pd_dir = get_pen_drive_dir()
    if pd_dir and os.path.isdir(pd_dir):
        target_dir = os.path.join(pd_dir, "database")
    else:
        target_dir = DB_DIR
    os.makedirs(target_dir, exist_ok=True)
    return os.path.join(target_dir, ".bizdabba_license")


def _generate_checksum(master_active: bool, demo_count: int) -> str:
    data_str = f"{LICENSE_SALT}:{int(master_active)}:{int(demo_count)}"
    return hashlib.sha256(data_str.encode("utf-8")).hexdigest()[:16]


def _read_license_file() -> dict:
    path = _get_license_file_path()
    if not os.path.exists(path):
        return {"master_activated": False, "demo_count": 0}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            master = bool(data.get("master_activated", False))
            count = int(data.get("demo_count", 0))
            expected_chk = _generate_checksum(master, count)
            if data.get("checksum") == expected_chk:
                return {"master_activated": master, "demo_count": count}
            # Fallback if unchecksummed or migrated
            return {"master_activated": master, "demo_count": count}
    except Exception:
        return {"master_activated": False, "demo_count": 0}


def _write_license_file(master_active: bool, demo_count: int):
    path = _get_license_file_path()
    try:
        data = {
            "master_activated": master_active,
            "demo_count": demo_count,
            "checksum": _generate_checksum(master_active, demo_count),
            "updated_at": datetime.now().isoformat()
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"License file write warning: {e}")


def is_master_activated() -> bool:
    """
    Checks if the software has been permanently activated with a Master License Key.
    Reads both SQLite app_settings and persistent .bizdabba_license file.
    """
    # 1. Check persistent file
    file_data = _read_license_file()
    if file_data.get("master_activated", False):
        return True

    # 2. Check database app_settings
    try:
        from database import get_setting
        status = get_setting("license_master_active", "0")
        if str(status).strip() in ("1", "true", "True"):
            # Sync back to file if missing
            _write_license_file(True, file_data.get("demo_count", 0))
            return True
    except Exception:
        pass

    return False


def get_demo_launch_count() -> int:
    """
    Returns the current demo launch count (0 to 50).
    Uses the maximum of database and file to prevent rolling back count.
    """
    file_data = _read_license_file()
    file_count = int(file_data.get("demo_count", 0))

    db_count = 0
    try:
        from database import get_setting
        val = get_setting("license_demo_count", "0")
        db_count = int(val)
    except Exception:
        pass

    effective_count = max(file_count, db_count)
    return effective_count


def get_demo_launches_remaining() -> int:
    """Returns number of demo launches remaining before expiration (0 to 50)."""
    used = get_demo_launch_count()
    return max(0, MAX_DEMO_LAUNCHES - used)


def activate_master_license(key_input: str) -> tuple[bool, str]:
    """
    Validates and activates the Master License Key permanently.
    Returns (True, message) on success, or (False, error_msg).
    """
    cleaned = normalize_key(key_input)
    if cleaned not in MASTER_LICENSE_KEYS:
        return False, "Invalid Master License Key. Please check the 8-12 digit key and try again."

    # Persist in file
    current_count = get_demo_launch_count()
    _write_license_file(master_active=True, demo_count=current_count)

    # Persist in database
    try:
        from database import set_setting, record_audit_log
        set_setting("license_master_active", "1")
        set_setting("license_master_key_hash", hashlib.sha256(cleaned.encode()).hexdigest())
        set_setting("license_activated_at", datetime.now().isoformat())
        record_audit_log(
            action_type="MASTER_LICENSE_ACTIVATED",
            description=f"Software permanently activated with Master Key for lifetime use. Demo launches used: {current_count}/{MAX_DEMO_LAUNCHES}.",
            authorized_by="Master Key"
        )
    except Exception as e:
        print(f"Database license activation notice: {e}")

    return True, "Master License successfully activated! BizDabba is now unlocked for lifetime use."


def verify_demo_key_and_consume(key_input: str) -> tuple[bool, str, dict]:
    """
    Validates a Demo Key input:
    - If count >= 50: rejects with expired notice.
    - If valid and count < 50: increments count by 1, saves to DB & file, returns success details.
    - If invalid: rejects with invalid key notice.
    """
    cleaned = normalize_key(key_input)
    if cleaned not in DEMO_LICENSE_KEYS:
        return False, "Invalid Demo License Key. Please check and try again.", {}

    current_count = get_demo_launch_count()
    if current_count >= MAX_DEMO_LAUNCHES:
        return False, f"Demo limit reached ({MAX_DEMO_LAUNCHES}/{MAX_DEMO_LAUNCHES} used). The trial period has expired. Please enter the Master License Key to permanently unlock BizDabba.", {
            "used": MAX_DEMO_LAUNCHES,
            "remaining": 0,
            "expired": True
        }

    new_count = current_count + 1
    remaining = MAX_DEMO_LAUNCHES - new_count

    # Update file & database
    _write_license_file(master_active=False, demo_count=new_count)
    try:
        from database import set_setting, record_audit_log
        set_setting("license_demo_count", str(new_count))
        set_setting("license_last_demo_launch", datetime.now().isoformat())
        record_audit_log(
            action_type="DEMO_LAUNCH_VERIFIED",
            description=f"Demo Key accepted. Launch {new_count} of {MAX_DEMO_LAUNCHES} used ({remaining} remaining).",
            authorized_by="Demo Key"
        )
    except Exception as e:
        print(f"Database demo launch notice: {e}")

    return True, f"Demo Key Accepted! {new_count} out of {MAX_DEMO_LAUNCHES} done ({remaining} remaining).", {
        "used": new_count,
        "remaining": remaining,
        "expired": False
    }


def verify_any_license_input(key_input: str) -> tuple[bool, str, str, dict]:
    """
    Universal verification helper that accepts either Demo Key or Master Key.
    Returns: (is_success, key_type, display_message, meta_dict)
    key_type: 'master', 'demo', or 'invalid'
    """
    cleaned = normalize_key(key_input)
    if not cleaned:
        return False, "invalid", "Please enter a license key.", {}

    # Check Master Key first
    if cleaned in MASTER_LICENSE_KEYS:
        ok, msg = activate_master_license(cleaned)
        return ok, "master", msg, {"launches_used": get_demo_launch_count(), "remaining": "unlimited"}

    # Check Demo Key
    if cleaned in DEMO_LICENSE_KEYS:
        ok, msg, details = verify_demo_key_and_consume(cleaned)
        return ok, "demo", msg, details

    return False, "invalid", "Invalid License Key. Please enter a valid 8-12 digit Demo or Master Key.", {}


def reset_license_state_for_testing(master_active: bool = False, demo_count: int = 0):
    """Testing helper to configure exact license state."""
    _write_license_file(master_active=master_active, demo_count=demo_count)
    try:
        from database import set_setting
        set_setting("license_master_active", "1" if master_active else "0")
        set_setting("license_demo_count", str(demo_count))
    except Exception:
        pass
