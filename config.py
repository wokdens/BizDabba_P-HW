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

# Dedicated rolling auto-backups directory in LocalAppData (safe from application directory changes)
local_app_data = os.environ.get("LOCALAPPDATA")
if local_app_data:
    AUTO_BACKUPS_DIR = os.path.join(local_app_data, "BizDibba_Diwali_v2.0", "Backups")
else:
    AUTO_BACKUPS_DIR = os.path.join(BACKUPS_DIR, "auto")

os.makedirs(DB_DIR, exist_ok=True)
os.makedirs(INVOICES_DIR, exist_ok=True)
os.makedirs(BACKUPS_DIR, exist_ok=True)
os.makedirs(AUTO_BACKUPS_DIR, exist_ok=True)

DATABASE_PATH = os.path.join(DB_DIR, "business.db")

# Default Shop Profile
SHOP_NAME = "Electrical Wholesale & Retail"
SHOP_PHONE = "9876543210"
SHOP_ADDRESS = "Wholesale Electrical Market"

# Master Password for Exported CSV & Data Archives
CSV_MASTER_EXPORT_PASSWORD = "Wokdens@CSV#2026"