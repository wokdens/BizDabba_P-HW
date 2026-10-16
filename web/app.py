import os
import sys

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from nicegui import ui, app
import database

# Initialize database tables and migrations
database.create_tables()
database.run_migrations()

from web.pages.dashboard import dashboard_page
from web.pages.billing import billing_page
from web.pages.inventory import inventory_page
from web.pages.ledger import ledger_page
from web.pages.audit import audit_page

# Define Routes
@ui.page('/')
def index():
    dashboard_page()

@ui.page('/billing')
def billing():
    billing_page()

@ui.page('/inventory')
def inventory():
    inventory_page()

@ui.page('/ledger')
def ledger():
    ledger_page()

@ui.page('/audit')
def audit():
    audit_page()

if __name__ in {"__main__", "__mp_main__"}:
    port = int(os.environ.get("PORT", 8050))
    print("==================================================")
    print(f"  BizDabba Cloud Web App (Option 2 - NiceGUI)")
    print(f"  Listening on http://localhost:{port}")
    print("  Powered by Wokdens.com")
    print("==================================================")
    ui.run(
        title="BizDabba by Wokdens.com - Paints & Hardware Cloud POS",
        port=port,
        reload=False,
        show=False,
        favicon="⚡"
    )
