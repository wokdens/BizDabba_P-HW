import os
import sys

import string

def get_pen_drive_dir():
    """
    Detects if running directly from a Pen Drive or if a Pen Drive containing
    'BizDabba PHWP' is currently mounted on any removable/external drive (D: to Z:).
    Returns the absolute path to the Pen Drive app folder, or None.
    """
    # 1. If running as a frozen executable on a non-C drive
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        if not exe_dir.lower().startswith("c:"):
            return exe_dir
    # 2. Check external drive letters (D: through Z:)
    for d in string.ascii_uppercase:
        if d == 'C':
            continue
        candidate = f"{d}:\\BizDabba PHWP"
        if os.path.isdir(candidate):
            return candidate
    return None

# Handle both development and PyInstaller bundle environments
if getattr(sys, 'frozen', False):
    # Running as PyInstaller bundle
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # Running as script
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Pen Drive detection: If a Pen Drive is plugged in or running from it, prioritize it
PENDRIVE_DIR = get_pen_drive_dir()

# Invoices are strictly targeted to the Pen Drive whenever attached or running from it
if PENDRIVE_DIR and os.path.isdir(PENDRIVE_DIR):
    INVOICES_DIR = os.path.join(PENDRIVE_DIR, "invoices")
else:
    INVOICES_DIR = os.path.join(BASE_DIR, "invoices")

DB_DIR = os.path.join(BASE_DIR, "database")
BACKUPS_DIR = os.path.join(BASE_DIR, "backups")

# Dedicated rolling auto-backups directory strictly on Pen Drive (Zero Host Computer Footprint)
AUTO_BACKUPS_DIR = os.path.join(BACKUPS_DIR, "auto")

os.makedirs(DB_DIR, exist_ok=True)
os.makedirs(INVOICES_DIR, exist_ok=True)
os.makedirs(BACKUPS_DIR, exist_ok=True)
os.makedirs(AUTO_BACKUPS_DIR, exist_ok=True)

DATABASE_PATH = os.path.join(DB_DIR, "business.db")

# Default Shop Profile (Delhi-based Paints & Hardware)
SHOP_NAME = "Delhi Paints & Hardware Store"
SHOP_PHONE = "+91-9811234567"
SHOP_ADDRESS = "Shop No. 14, Hauz Qazi / Chawri Bazar, Delhi - 110006"

# Application Branding
APP_TITLE = "BizDabba PHWP by wokdens.com"
APP_SUBTITLE = "Paints & Hardware Wholesale & Retail Management"

# Master Password for Exported CSV & Data Archives
CSV_MASTER_EXPORT_PASSWORD = "Wokdens@CSV#2026"