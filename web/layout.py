import sys
import os
from nicegui import ui, app

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import database

# In-memory admin session state
admin_session = {"authenticated": False}

def is_admin():
    return admin_session["authenticated"]

def set_admin_authenticated(val: bool):
    admin_session["authenticated"] = val

def require_admin_dialog(on_success=None):
    """Opens a PIN authentication modal for admin actions."""
    with ui.dialog() as dlg, ui.card().classes('w-96 p-6 rounded-2xl shadow-2xl'):
        ui.label('🔒 Admin Authentication').classes('text-lg font-bold text-slate-800')
        ui.label('Enter 4-digit Owner/Admin PIN to continue:').classes('text-sm text-slate-500 mb-2')
        pin_input = ui.input(placeholder='Enter PIN (e.g. 8160)', password=True).classes('w-full').props('autofocus outlined dense')
        
        def try_auth():
            pin = pin_input.value.strip()
            if database.verify_admin_pin(pin):
                set_admin_authenticated(True)
                dlg.close()
                ui.notify('Admin Access Granted', type='positive', icon='check_circle')
                if on_success:
                    on_success()
            else:
                ui.notify('Invalid Admin PIN', type='negative', icon='lock')
                pin_input.value = ''
        
        with ui.row().classes('w-full justify-end gap-2 mt-4'):
            ui.button('Cancel', on_click=dlg.close).props('flat text-slate-600')
            ui.button('Verify', on_click=try_auth).props('unelevated color=primary')
        dlg.open()


def render_header(active_page: str = "dashboard"):
    """Renders the top branding, navigation links, and KPI quick badges."""
    # Custom head styling
    ui.add_head_html('''
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
        <style>
            body { font-family: 'Inter', sans-serif; background-color: #f8fafc; }
            @media print {
                header, footer, .no-print { display: none !important; }
                .print-only { display: block !important; }
            }
        </style>
    ''')

    # Fetch live stats for header badges
    try:
        today_sales = database.get_today_sales()
        total_pending = database.get_total_pending_amount()
    except Exception:
        today_sales = 0.0
        total_pending = 0.0

    with ui.header().classes('bg-slate-900 text-white items-center justify-between px-6 py-3 shadow-lg z-50'):
        # Brand Logo & Tagline
        with ui.row().classes('items-center gap-3 cursor-pointer').on('click', lambda: ui.navigate.to('/')):
            with ui.avatar(color='amber-500', text_color='slate-900', icon='bolt').classes('font-black shadow-md'):
                pass
            with ui.column().classes('gap-0'):
                ui.label('BizDabba').classes('text-xl font-extrabold tracking-tight text-white leading-tight')
                ui.label('by Wokdens.com • Paints & Hardware').classes('text-[11px] text-amber-400 font-semibold uppercase tracking-wider')

        # Desktop Navigation Links
        nav_items = [
            ("dashboard", "Dashboard", "dashboard", "/"),
            ("billing", "Billing & POS", "receipt_long", "/billing"),
            ("inventory", "Inventory", "inventory_2", "/inventory"),
            ("ledger", "Khata / Ledger", "menu_book", "/ledger"),
            ("audit", "Audit Trails", "verified_user", "/audit"),
        ]

        with ui.row().classes('items-center gap-1 max-md:hidden'):
            for page_id, label, icon, path in nav_items:
                is_active = (active_page == page_id)
                btn_classes = 'text-sm font-semibold px-4 py-2 rounded-xl transition-all '
                if is_active:
                    btn_classes += 'bg-blue-600 text-white shadow-sm'
                else:
                    btn_classes += 'text-slate-300 hover:text-white hover:bg-slate-800'
                ui.button(label, icon=icon, on_click=lambda p=path: ui.navigate.to(p)).classes(btn_classes).props('flat dense')

        # Live KPI Badges & Admin State
        with ui.row().classes('items-center gap-3'):
            with ui.row().classes('items-center gap-2 bg-slate-800 px-3 py-1.5 rounded-xl border border-slate-700 max-lg:hidden'):
                ui.icon('point_of_sale', size='sm').classes('text-emerald-400')
                with ui.column().classes('gap-0'):
                    ui.label('Today\'s Sales').classes('text-[10px] text-slate-400 uppercase font-semibold')
                    ui.label(f'₹{today_sales:,.0f}').classes('text-xs font-bold text-emerald-400')

            with ui.row().classes('items-center gap-2 bg-slate-800 px-3 py-1.5 rounded-xl border border-slate-700 max-lg:hidden'):
                ui.icon('account_balance_wallet', size='sm').classes('text-rose-400')
                with ui.column().classes('gap-0'):
                    ui.label('Pending Dues').classes('text-[10px] text-slate-400 uppercase font-semibold')
                    ui.label(f'₹{total_pending:,.0f}').classes('text-xs font-bold text-rose-400')

            # Admin status indicator
            if is_admin():
                def logout_admin():
                    set_admin_authenticated(False)
                    ui.notify('Logged out from Admin Mode', type='info')
                    ui.navigate.to('/')
                ui.button('Admin Active', icon='lock_open', on_click=logout_admin).props('unelevated rounded dense color=amber-500 text-color=slate-900').classes('text-xs font-bold')
            else:
                ui.button('Admin Login', icon='lock', on_click=lambda: require_admin_dialog(on_success=lambda: ui.navigate.to('/audit'))).props('outline rounded dense color=slate-400 text-color=white').classes('text-xs font-semibold')


def render_footer():
    """Renders persistent footer."""
    with ui.footer().classes('bg-slate-900 text-slate-400 text-xs py-3 px-6 justify-between items-center border-t border-slate-800 no-print'):
        ui.label('⚡ BizDabba Cloud POS • Delhi Paints & Hardware Demo').classes('font-medium')
        with ui.row().classes('gap-4'):
            ui.label('Licensed to: Delhi Paints & Hardware').classes('text-slate-400 font-medium')
            ui.link('Built by Wokdens.com', 'https://wokdens.com', new_tab=True).classes('text-blue-400 font-semibold hover:underline')
