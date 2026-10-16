from nicegui import ui
import database
from web.layout import render_header, render_footer, is_admin

def get_customer_summary():
    conn = database.get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT 
            c.id, 
            c.name, 
            COALESCE(c.phone, ''), 
            COALESCE(c.address, ''),
            COUNT(i.id) as invoice_count,
            COALESCE(SUM(i.total), 0) as total_billed,
            COALESCE(SUM(i.paid), 0) as total_paid,
            COALESCE(SUM(i.pending), 0) as total_pending
        FROM customers c
        LEFT JOIN invoices i ON c.id = i.customer_id AND COALESCE(i.status, 'ACTIVE') != 'CANCELLED'
        GROUP BY c.id, c.name, c.phone, c.address
        ORDER BY total_pending DESC, c.name ASC
    """)
    rows = c.fetchall()
    conn.close()
    return rows

def apply_customer_payment(customer_name, payment_amount, pay_mode="Cash", notes=""):
    """Applies payment amount against customer's pending invoices in FIFO order."""
    rem_payment = float(payment_amount)
    if rem_payment <= 0:
        return
    
    conn = database.get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT i.id, i.total, i.paid, i.pending
        FROM invoices i
        JOIN customers c ON i.customer_id = c.id
        WHERE c.name = ? AND i.pending > 0 AND COALESCE(i.status, 'ACTIVE') != 'CANCELLED'
        ORDER BY i.id ASC
    """, (customer_name,))
    unpaid_invoices = c.fetchall()
    
    for inv_id, inv_total, inv_paid, inv_pending in unpaid_invoices:
        if rem_payment <= 0:
            break
        pay_chunk = min(rem_payment, inv_pending)
        new_paid = inv_paid + pay_chunk
        new_pending = max(0.0, inv_total - new_paid)
        
        c.execute("UPDATE invoices SET paid = ?, pending = ? WHERE id = ?", (new_paid, new_pending, inv_id))
        rem_payment -= pay_chunk

    conn.commit()
    conn.close()
    
    database.record_audit_log(
        action_type="PAYMENT_RECEIVED",
        description=f"Received payment of ₹{payment_amount:,.2f} from {customer_name} via {pay_mode}. Notes: {notes or 'Ledger settlement'}",
        authorized_by="Admin" if is_admin() else "Operator"
    )

def ledger_page():
    render_header(active_page="ledger")
    
    total_pending = database.get_total_pending_amount()
    search_state = {'val': ''}
    
    with ui.column().classes('w-full max-w-7xl mx-auto p-6 gap-6'):
        # Header & Summary Banner
        with ui.row().classes('w-full justify-between items-center'):
            with ui.column().classes('gap-1'):
                ui.label('👥 Customer Khata & Ledger Accounts').classes('text-2xl font-black text-slate-900')
                ui.label('Track customer credit, outstanding balances, and payment collections').classes('text-sm text-slate-500 font-medium')
            
            with ui.card().classes('px-5 py-2.5 bg-rose-50 border border-rose-200 rounded-2xl flex items-center gap-3'):
                ui.icon('account_balance_wallet', size='md').classes('text-rose-600')
                with ui.column().classes('gap-0'):
                    ui.label('Total Market Outstanding').classes('text-[11px] font-bold text-rose-600 uppercase tracking-wider')
                    ui.label(f'₹{total_pending:,.0f}').classes('text-xl font-black text-rose-700')

        # Search Bar
        with ui.card().classes('w-full p-4 rounded-2xl bg-white border border-slate-200 shadow-sm'):
            with ui.row().classes('w-full items-center gap-3'):
                s_input = ui.input(placeholder='Search customer by name, mobile number, or address...').classes('flex-1').props('outlined dense clearable')
                ui.icon('search', size='sm').classes('text-slate-400')

        table_container = ui.column().classes('w-full')

    def on_search(e):
        search_state['val'] = s_input.value or ''
        refresh_ledger_table()

    s_input.on_value_change(on_search)

    def refresh_ledger_table():
        table_container.clear()
        cust_records = get_customer_summary()
        
        sq = search_state['val'].strip().lower()
        if sq:
            cust_records = [r for r in cust_records if sq in str(r[1]).lower() or sq in str(r[2]).lower() or sq in str(r[3]).lower()]
            
        with table_container:
            with ui.card().classes('w-full p-4 rounded-2xl bg-white border border-slate-200 shadow-sm'):
                with ui.row().classes('w-full justify-between items-center mb-3'):
                    ui.label(f'Displaying {len(cust_records)} Customer Accounts').classes('text-xs font-bold text-slate-500')
                    
                columns = [
                    {'name': 'name', 'label': 'Customer Name', 'field': 'name', 'align': 'left'},
                    {'name': 'phone', 'label': 'Contact / Phone', 'field': 'phone', 'align': 'left'},
                    {'name': 'bills', 'label': 'Bills', 'field': 'bills', 'align': 'center'},
                    {'name': 'billed', 'label': 'Total Billed (₹)', 'field': 'billed', 'align': 'right'},
                    {'name': 'paid', 'label': 'Total Paid (₹)', 'field': 'paid', 'align': 'right'},
                    {'name': 'pending', 'label': 'Pending Balance (₹)', 'field': 'pending', 'align': 'right'},
                    {'name': 'actions', 'label': 'Actions', 'field': 'actions', 'align': 'center'},
                ]
                
                rows = []
                for c in cust_records:
                    # c: (id, name, phone, address, invoice_count, total_billed, total_paid, total_pending)
                    cid, cname, cphone, caddr, inv_count, tbilled, tpaid, tpending = c
                    try:
                        tbilled_f = float(tbilled or 0)
                        tpaid_f = float(tpaid or 0)
                        tpending_f = float(tpending or 0)
                    except Exception:
                        tbilled_f, tpaid_f, tpending_f = 0.0, 0.0, 0.0
                    rows.append({
                        'id': cid,
                        'name': cname,
                        'phone': cphone or '-',
                        'address': caddr,
                        'bills': inv_count,
                        'billed': f'₹{tbilled_f:,.0f}',
                        'paid': f'₹{tpaid_f:,.0f}',
                        'pending': f'₹{tpending_f:,.0f}',
                        'raw_pending': tpending_f,
                        'raw_name': cname
                    })

                tbl = ui.table(columns=columns, rows=rows, row_key='id').classes('w-full').props('flat bordered dense')
                
                tbl.add_slot('body-cell-pending', '''
                    <q-td :props="props">
                        <q-badge :color="props.row.raw_pending > 0 ? 'rose-500' : 'emerald-500'" text-color="white" rounded>
                            {{ props.row.pending }}
                        </q-badge>
                    </q-td>
                ''')
                
                tbl.add_slot('body-cell-actions', '''
                    <q-td :props="props">
                        <div class="row items-center justify-center q-gutter-x-sm">
                            <q-btn v-if="props.row.raw_pending > 0" unelevated dense size="sm" color="emerald-600" label="Collect Payment" icon="add_card" @click="$parent.$emit('collect_payment', props.row)" />
                            <q-btn flat dense round size="sm" color="primary" icon="visibility" @click="$parent.$emit('view_statement', props.row)" />
                        </div>
                    </q-td>
                ''')

                def open_collect_payment_dialog(row_data):
                    cname = row_data['raw_name']
                    cpending = row_data['raw_pending']
                    with ui.dialog() as dlg, ui.card().classes('w-96 p-6 rounded-2xl'):
                        ui.label('💰 Collect Customer Payment').classes('text-lg font-bold text-slate-800')
                        ui.label(f'Customer: {cname}').classes('text-xs text-slate-500 font-semibold truncate')
                        ui.badge(f'Current Due: ₹{cpending:,.2f}', color='rose-500').props('rounded').classes('my-2')
                        
                        amt_input = ui.number('Payment Amount Received (₹)', value=cpending, min=1, max=cpending).classes('w-full').props('outlined dense autofocus')
                        mode_select = ui.select(options=['Cash', 'UPI / QR', 'Bank Transfer', 'Cheque'], label='Payment Mode', value='Cash').classes('w-full').props('outlined dense')
                        note_input = ui.input('Reference / Notes (Optional)').classes('w-full').props('outlined dense')

                        def record_pay():
                            amt = float(amt_input.value or 0)
                            if amt <= 0:
                                ui.notify('Please enter a valid payment amount', type='warning')
                                return
                            apply_customer_payment(cname, amt, mode_select.value, note_input.value.strip())
                            ui.notify(f'Payment of ₹{amt:,.2f} recorded for {cname}!', type='positive', icon='check_circle')
                            dlg.close()
                            refresh_ledger_table()

                        with ui.row().classes('w-full justify-end gap-2 mt-4'):
                            ui.button('Cancel', on_click=dlg.close).props('flat text-slate-600')
                            ui.button('Confirm Payment', on_click=record_pay).props('unelevated color=emerald-600')
                    dlg.open()

                def open_statement_dialog(row_data):
                    cname = row_data['raw_name']
                    with ui.dialog() as dlg, ui.card().classes('w-[680px] max-w-[95vw] p-6 rounded-2xl flex flex-col max-h-[85vh]'):
                        with ui.row().classes('w-full justify-between items-center pb-2 border-b border-slate-200'):
                            with ui.row().classes('items-center gap-2'):
                                ui.icon('receipt_long', size='md').classes('text-blue-600')
                                ui.label(f'Statement: {cname}').classes('text-lg font-bold text-slate-800')
                            ui.button(icon='close', on_click=dlg.close).props('flat round dense')
                        
                        invoices = database.get_customer_invoices(cname) or []
                        with ui.column().classes('w-full flex-1 overflow-y-auto mt-4 gap-2'):
                            if not invoices:
                                ui.label('No billing history found for this customer.').classes('text-slate-400 italic text-sm py-4')
                            else:
                                for inv in invoices:
                                    # inv: (id, invoice_number, date, total, paid, pending)
                                    with ui.row().classes('w-full justify-between items-center p-3 bg-slate-50 border border-slate-200 rounded-xl'):
                                        with ui.column().classes('gap-0'):
                                            ui.label(f'Bill #{inv[1]}').classes('font-bold text-slate-800 text-sm')
                                            ui.label(f'Date: {inv[2]}').classes('text-[10px] text-slate-500')
                                        with ui.row().classes('items-center gap-4'):
                                            ui.label(f'Total: ₹{inv[3]:,.0f}').classes('text-xs font-semibold text-slate-700')
                                            ui.label(f'Paid: ₹{inv[4]:,.0f}').classes('text-xs text-emerald-600 font-semibold')
                                            if inv[5] > 0:
                                                ui.badge(f'Due: ₹{inv[5]:,.0f}', color='rose-500').props('rounded')
                                            else:
                                                ui.badge('Cleared', color='emerald-500').props('rounded')

                tbl.on('collect_payment', lambda e: open_collect_payment_dialog(e.args))
                tbl.on('view_statement', lambda e: open_statement_dialog(e.args))

    refresh_ledger_table()
    render_footer()
