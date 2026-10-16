from nicegui import ui
import database

def show_receipt_modal(invoice_id_or_num):
    """
    Displays a beautiful, printable receipt dialog with dual format support:
    1. 3-inch (80mm) Thermal Slip
    2. A4 Standard Tax Invoice
    """
    conn = database.get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT 
            i.id, 
            i.invoice_number, 
            COALESCE(c.name, 'Cash Customer'), 
            COALESCE(c.phone, ''), 
            i.total, 
            i.total, 
            0.0, 
            COALESCE(i.note, 'Cash'), 
            i.paid, 
            i.pending, 
            COALESCE(strftime('%d-%m-%Y %I:%M %p', i.invoice_date), i.invoice_date), 
            COALESCE(i.note, '')
        FROM invoices i
        LEFT JOIN customers c ON i.customer_id = c.id
        WHERE i.id = ? OR i.invoice_number = ?
        ORDER BY i.id DESC
        LIMIT 1
    """, (invoice_id_or_num, str(invoice_id_or_num)))
    invoice_data = c.fetchone()
    conn.close()
            
    if not invoice_data:
        ui.notify('Invoice record not found', type='negative')
        return

    # Unpack invoice record
    inv_id, inv_num, cust_name, cust_phone, total, subtotal, discount, pay_mode, paid, pending, date_str, note = invoice_data
    items = database.get_invoice_items(inv_id) or []
    
    with ui.dialog() as dlg, ui.card().classes('w-[680px] max-w-[95vw] max-h-[90vh] p-6 rounded-2xl flex flex-col'):
        with ui.row().classes('w-full justify-between items-center pb-3 border-b border-slate-200 no-print'):
            with ui.row().classes('items-center gap-2'):
                ui.icon('receipt', size='md').classes('text-blue-600')
                ui.label(f'Invoice: {inv_num}').classes('text-lg font-bold text-slate-800')
            with ui.row().classes('items-center gap-2'):
                ui.button('Print', icon='print', on_click=lambda: ui.run_javascript('window.print()')).props('unelevated color=primary rounded')
                ui.button(icon='close', on_click=dlg.close).props('flat round dense')

        with ui.tabs().classes('w-full no-print') as tabs:
            tab_thermal = ui.tab('3" Thermal Slip (80mm)')
            tab_a4 = ui.tab('A4 Standard Invoice')

        with ui.tab_panels(tabs, value=tab_thermal).classes('w-full flex-1 overflow-y-auto p-4'):
            # ==========================================
            # TAB 1: 3-INCH (80mm) THERMAL RECEIPT
            # ==========================================
            with ui.tab_panel(tab_thermal):
                with ui.card().classes('w-[340px] mx-auto p-4 bg-white border border-slate-300 shadow-sm font-mono text-xs'):
                    # Header
                    ui.label('DELHI PAINTS & HARDWARE').classes('font-black text-center text-sm w-full')
                    ui.label('Main Market, Delhi Road, New Delhi').classes('text-center text-[10px] w-full text-slate-600')
                    ui.label('Ph: +91 98765-43210 | GSTIN: 07AAACD1234F1Z5').classes('text-center text-[10px] w-full text-slate-600 mb-2')
                    ui.separator().classes('my-1')
                    
                    # Invoice & Customer Info
                    ui.label(f'Bill No: {inv_num}').classes('font-bold')
                    ui.label(f'Date: {date_str}')
                    ui.label(f'Customer: {cust_name or "Cash Sale"}')
                    if cust_phone:
                        ui.label(f'Phone: {cust_phone}')
                    ui.separator().classes('my-2')
                    
                    # Items Table Header
                    with ui.row().classes('w-full font-bold justify-between text-[11px] mb-1'):
                        ui.label('Item').classes('w-32 truncate')
                        ui.label('Qty').classes('w-10 text-center')
                        ui.label('Rate').classes('w-12 text-right')
                        ui.label('Total').classes('w-14 text-right')
                    ui.separator().classes('my-1')
                    
                    # Items List: (quantity, products.name, mrp, price, products.unit, discount, discount_base, total, increase)
                    for item in items:
                        qty = item[0]
                        pname = item[1]
                        price = item[3]
                        unit = item[4] or "Pcs"
                        itotal = item[7]
                        with ui.row().classes('w-full justify-between items-center text-[11px] py-0.5'):
                            ui.label(pname).classes('w-32 truncate')
                            ui.label(f'{qty} {unit}').classes('w-10 text-center')
                            ui.label(f'₹{price:.0f}').classes('w-12 text-right')
                            ui.label(f'₹{itotal:.0f}').classes('w-14 text-right font-semibold')
                    
                    ui.separator().classes('my-2')
                    
                    # Summary Totals
                    with ui.column().classes('w-full gap-1 text-[11px]'):
                        with ui.row().classes('w-full justify-between'):
                            ui.label('Subtotal:')
                            ui.label(f'₹{subtotal:,.2f}')
                        if discount > 0:
                            with ui.row().classes('w-full justify-between text-emerald-600'):
                                ui.label('Discount:')
                                ui.label(f'-₹{discount:,.2f}')
                        with ui.row().classes('w-full justify-between font-black text-sm pt-1 border-t border-dashed border-slate-400'):
                            ui.label('Net Total:')
                            ui.label(f'₹{total:,.2f}')
                        with ui.row().classes('w-full justify-between text-slate-700'):
                            ui.label(f'Paid ({pay_mode}):')
                            ui.label(f'₹{paid:,.2f}')
                        if pending > 0:
                            with ui.row().classes('w-full justify-between text-rose-600 font-bold'):
                                ui.label('Balance Due:')
                                ui.label(f'₹{pending:,.2f}')
                    
                    ui.separator().classes('my-2')
                    ui.label('Thank You! Visit Again.').classes('text-center font-bold w-full text-[10px]')
                    ui.label('⚡ BizDabba by Wokdens.com').classes('text-center font-semibold text-slate-500 w-full text-[9px] mt-1')

            # ==========================================
            # TAB 2: A4 STANDARD TAX INVOICE
            # ==========================================
            with ui.tab_panel(tab_a4):
                with ui.card().classes('w-full p-6 bg-white border border-slate-200 rounded-xl shadow-sm text-sm'):
                    with ui.row().classes('w-full justify-between items-start mb-4'):
                        with ui.column().classes('gap-1'):
                            ui.label('DELHI PAINTS & HARDWARE').classes('text-xl font-extrabold text-slate-900')
                            ui.label('Authorised Asian Paints & Nerolac Dealer').classes('text-xs text-blue-600 font-semibold')
                            ui.label('Main Market, Delhi Road, New Delhi - 110001').classes('text-xs text-slate-600')
                            ui.label('Ph: +91 98765-43210 | GSTIN: 07AAACD1234F1Z5').classes('text-xs text-slate-600')
                        with ui.column().classes('items-end gap-1'):
                            ui.label('TAX INVOICE').classes('text-lg font-black text-slate-800 tracking-wider')
                            ui.label(f'Invoice No: {inv_num}').classes('font-bold text-blue-700')
                            ui.label(f'Date: {date_str}').classes('text-xs text-slate-600')
                            ui.label(f'Mode: {pay_mode}').classes('text-xs font-semibold px-2 py-0.5 bg-slate-100 rounded')

                    ui.separator().classes('my-2')
                    
                    # Bill To Details
                    with ui.row().classes('w-full justify-between p-3 bg-slate-50 rounded-lg mb-4'):
                        with ui.column().classes('gap-0.5'):
                            ui.label('BILL TO:').classes('text-[10px] font-bold text-slate-500')
                            ui.label(cust_name or 'Cash / Counter Customer').classes('font-bold text-slate-800')
                            if cust_phone:
                                ui.label(f'Contact: {cust_phone}').classes('text-xs text-slate-600')

                    # Table
                    columns = [
                        {'name': 'sno', 'label': '#', 'field': 'sno', 'align': 'left'},
                        {'name': 'name', 'label': 'Item Description', 'field': 'name', 'align': 'left'},
                        {'name': 'qty', 'label': 'Qty', 'field': 'qty', 'align': 'center'},
                        {'name': 'unit', 'label': 'Unit', 'field': 'unit', 'align': 'center'},
                        {'name': 'mrp', 'label': 'MRP', 'field': 'mrp', 'align': 'right'},
                        {'name': 'rate', 'label': 'Rate (₹)', 'field': 'rate', 'align': 'right'},
                        {'name': 'total', 'label': 'Total (₹)', 'field': 'total', 'align': 'right'},
                    ]
                    rows = []
                    for idx, it in enumerate(items, 1):
                        rows.append({
                            'sno': idx,
                            'name': it[1],
                            'qty': it[0],
                            'unit': it[4] or 'Pcs',
                            'mrp': f'₹{it[2]:.0f}' if it[2] else '-',
                            'rate': f'₹{it[3]:.2f}',
                            'total': f'₹{it[7]:.2f}'
                        })
                    
                    ui.table(columns=columns, rows=rows, row_key='sno').classes('w-full border border-slate-200 rounded-lg').props('flat bordered dense')
                    
                    # Totals
                    with ui.row().classes('w-full justify-end mt-4'):
                        with ui.column().classes('w-64 gap-1.5 p-3 bg-slate-50 rounded-lg border border-slate-200'):
                            with ui.row().classes('w-full justify-between text-xs'):
                                ui.label('Subtotal:')
                                ui.label(f'₹{subtotal:,.2f}')
                            if discount > 0:
                                with ui.row().classes('w-full justify-between text-xs text-emerald-600'):
                                    ui.label('Discount:')
                                    ui.label(f'-₹{discount:,.2f}')
                            with ui.row().classes('w-full justify-between font-bold text-sm pt-1 border-t border-slate-300'):
                                ui.label('Grand Total:')
                                ui.label(f'₹{total:,.2f}')
                            with ui.row().classes('w-full justify-between text-xs text-slate-700'):
                                ui.label('Paid Amount:')
                                ui.label(f'₹{paid:,.2f}')
                            if pending > 0:
                                with ui.row().classes('w-full justify-between text-xs text-rose-600 font-bold'):
                                    ui.label('Balance Due:')
                                    ui.label(f'₹{pending:,.2f}')

                    with ui.row().classes('w-full justify-between items-end mt-8 pt-4 border-t border-slate-200'):
                        ui.label('Terms: Goods once sold will not be taken back without bill.').classes('text-[10px] text-slate-400')
                        with ui.column().classes('items-center gap-1'):
                            ui.label('For Delhi Paints & Hardware').classes('text-xs font-semibold text-slate-700')
                            ui.label('Authorised Signatory').classes('text-[10px] text-slate-400 pt-6')

        dlg.open()
