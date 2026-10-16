from nicegui import ui
import database
from web.layout import render_header, render_footer
from web.components.receipt_modal import show_receipt_modal

def dashboard_page():
    render_header(active_page="dashboard")
    
    # Live stats
    today_sales = database.get_today_sales()
    total_pending = database.get_total_pending_amount()
    total_customers = database.get_total_customers()
    total_products = database.get_total_products()
    low_stock_items = database.get_low_stock_items() or []
    
    with ui.column().classes('w-full max-w-7xl mx-auto p-6 gap-6'):
        # Welcome & Quick Action Header
        with ui.row().classes('w-full justify-between items-center'):
            with ui.column().classes('gap-1'):
                ui.label('⚡ Dashboard Overview').classes('text-2xl font-black text-slate-900')
                ui.label('Delhi Paints & Hardware • Real-Time Business Snapshot').classes('text-sm text-slate-500 font-medium')
            with ui.row().classes('gap-2'):
                ui.button('New Invoice (POS)', icon='add_shopping_cart', on_click=lambda: ui.navigate.to('/billing')).props('unelevated color=primary rounded').classes('font-bold')
                ui.button('Khata / Ledger', icon='menu_book', on_click=lambda: ui.navigate.to('/ledger')).props('outline color=slate-700 rounded').classes('font-semibold')

        # 4 KPI Summary Cards
        with ui.grid().classes('w-full grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4'):
            # Card 1: Today's Sales
            with ui.card().classes('p-5 rounded-2xl bg-white border border-slate-200 shadow-sm flex flex-col justify-between hover:shadow-md transition-all'):
                with ui.row().classes('w-full justify-between items-start'):
                    ui.label('Today\'s Sales').classes('text-xs font-bold text-slate-500 uppercase tracking-wider')
                    with ui.avatar(color='emerald-100', text_color='emerald-600', icon='payments', size='sm'):
                        pass
                ui.label(f'₹{today_sales:,.0f}').classes('text-2xl font-black text-emerald-600 mt-2')
                ui.label('Billed transactions today').classes('text-[11px] text-slate-400 font-medium mt-1')

            # Card 2: Pending Udhar / Ledger
            with ui.card().classes('p-5 rounded-2xl bg-white border border-slate-200 shadow-sm flex flex-col justify-between hover:shadow-md transition-all'):
                with ui.row().classes('w-full justify-between items-start'):
                    ui.label('Total Pending Dues').classes('text-xs font-bold text-slate-500 uppercase tracking-wider')
                    with ui.avatar(color='rose-100', text_color='rose-600', icon='account_balance_wallet', size='sm'):
                        pass
                ui.label(f'₹{total_pending:,.0f}').classes('text-2xl font-black text-rose-600 mt-2')
                ui.label('Uncollected Khata balance').classes('text-[11px] text-slate-400 font-medium mt-1')

            # Card 3: Customers Count
            with ui.card().classes('p-5 rounded-2xl bg-white border border-slate-200 shadow-sm flex flex-col justify-between hover:shadow-md transition-all'):
                with ui.row().classes('w-full justify-between items-start'):
                    ui.label('Registered Customers').classes('text-xs font-bold text-slate-500 uppercase tracking-wider')
                    with ui.avatar(color='blue-100', text_color='blue-600', icon='group', size='sm'):
                        pass
                ui.label(f'{total_customers}').classes('text-2xl font-black text-slate-800 mt-2')
                ui.label('Active client accounts').classes('text-[11px] text-slate-400 font-medium mt-1')

            # Card 4: Catalog Products
            with ui.card().classes('p-5 rounded-2xl bg-white border border-slate-200 shadow-sm flex flex-col justify-between hover:shadow-md transition-all'):
                with ui.row().classes('w-full justify-between items-start'):
                    ui.label('Products in Catalog').classes('text-xs font-bold text-slate-500 uppercase tracking-wider')
                    with ui.avatar(color='amber-100', text_color='amber-600', icon='format_paint', size='sm'):
                        pass
                ui.label(f'{total_products}').classes('text-2xl font-black text-slate-800 mt-2')
                ui.label('Paints, primers & hardware').classes('text-[11px] text-slate-400 font-medium mt-1')

        # Split Section: Recent Bills & Low Stock Alerts
        with ui.row().classes('w-full items-start gap-6'):
            # Left Column (2/3 width): Recent Invoices
            with ui.card().classes('flex-1 min-w-[340px] p-6 rounded-2xl bg-white border border-slate-200 shadow-sm'):
                with ui.row().classes('w-full justify-between items-center mb-4'):
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('history', size='md').classes('text-blue-600')
                        ui.label('Recent Invoices').classes('text-lg font-bold text-slate-800')
                    ui.button('View All', on_click=lambda: ui.navigate.to('/billing')).props('flat dense color=primary')
                
                # Fetch recent invoices from DB
                conn = database.get_connection()
                c = conn.cursor()
                c.execute("""
                    SELECT i.id, i.invoice_number, COALESCE(c.name, 'Cash Customer'), i.total, i.paid, i.pending, COALESCE(i.note, 'Cash'), 
                           COALESCE(strftime('%d-%m-%Y %I:%M %p', i.invoice_date), i.invoice_date)
                    FROM invoices i
                    LEFT JOIN customers c ON i.customer_id = c.id
                    WHERE COALESCE(i.status, 'ACTIVE') != 'CANCELLED'
                    ORDER BY i.id DESC
                    LIMIT 8
                """)
                recent_bills = c.fetchall()
                conn.close()
                
                if recent_bills:
                    columns = [
                        {'name': 'num', 'label': 'Invoice #', 'field': 'num', 'align': 'left'},
                        {'name': 'cust', 'label': 'Customer', 'field': 'cust', 'align': 'left'},
                        {'name': 'total', 'label': 'Total (₹)', 'field': 'total', 'align': 'right'},
                        {'name': 'mode', 'label': 'Mode', 'field': 'mode', 'align': 'center'},
                        {'name': 'status', 'label': 'Status', 'field': 'status', 'align': 'center'},
                        {'name': 'action', 'label': 'Action', 'field': 'action', 'align': 'center'},
                    ]
                    rows = []
                    for b in recent_bills:
                        # b: (id, num, cust, total, paid, pending, mode, date)
                        bid, bnum, bcust, btotal, bpaid, bpending, bmode, bdate = b
                        is_paid = (bpending <= 0.01)
                        rows.append({
                            'id': bid,
                            'num': bnum,
                            'cust': bcust or 'Cash Customer',
                            'total': f'₹{btotal:,.0f}',
                            'mode': bmode,
                            'status': 'Paid' if is_paid else f'Due: ₹{bpending:,.0f}',
                            'is_paid': is_paid
                        })
                    
                    table = ui.table(columns=columns, rows=rows, row_key='id').classes('w-full').props('flat bordered dense')
                    table.add_slot('body-cell-status', '''
                        <q-td :props="props">
                            <q-badge :color="props.row.is_paid ? 'emerald-500' : 'rose-500'" text-color="white" rounded>
                                {{ props.row.status }}
                            </q-badge>
                        </q-td>
                    ''')
                    table.add_slot('body-cell-action', '''
                        <q-td :props="props">
                            <q-btn flat dense round icon="receipt" color="primary" @click="$parent.$emit('view_receipt', props.row.id)" />
                        </q-td>
                    ''')
                    table.on('view_receipt', lambda e: show_receipt_modal(e.args))
                else:
                    ui.label('No recent invoices found.').classes('text-slate-400 italic text-sm py-4')

            # Right Column (1/3 width): Low Stock Warnings
            with ui.card().classes('w-full lg:w-96 p-6 rounded-2xl bg-white border border-slate-200 shadow-sm'):
                with ui.row().classes('w-full justify-between items-center mb-4'):
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('warning', size='md').classes('text-amber-500')
                        ui.label('Low Stock Alerts').classes('text-lg font-bold text-slate-800')
                    ui.badge(f'{len(low_stock_items)} items', color='amber').props('rounded')
                
                if low_stock_items:
                    with ui.column().classes('w-full gap-2 max-h-[380px] overflow-y-auto'):
                        for itm in low_stock_items[:10]:
                            # itm: (id, name, stock, unit, selling_price, mrp, category)
                            pid, pname, pstock, punit, pprice = itm[0], itm[1], itm[2], itm[3], itm[4]
                            with ui.row().classes('w-full justify-between items-center p-2.5 bg-amber-50/50 border border-amber-200 rounded-xl'):
                                with ui.column().classes('gap-0 flex-1 pr-2'):
                                    ui.label(pname).classes('text-xs font-bold text-slate-800 truncate')
                                    ui.label(f'Selling: ₹{pprice:.0f} • {punit}').classes('text-[10px] text-slate-500')
                                with ui.row().classes('items-center gap-1'):
                                    ui.badge(f'{pstock} left', color='red-500').props('rounded')
                else:
                    ui.label('All items are adequately stocked!').classes('text-emerald-600 font-medium text-xs py-4')

    render_footer()
