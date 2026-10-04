import os
import sys

# Handle both development and PyInstaller bundle environments
if getattr(sys, 'frozen', False):
    # Running as PyInstaller bundle
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # Running as script
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Ensure required application directories exist
DB_DIR = os.path.join(BASE_DIR, "database")
INVOICES_DIR = os.path.join(BASE_DIR, "invoices")
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