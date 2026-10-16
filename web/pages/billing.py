from nicegui import ui
import database
from web.layout import render_header, render_footer
from web.components.receipt_modal import show_receipt_modal

def billing_page():
    render_header(active_page="billing")
    
    # State for the active bill
    cart_items = []
    customer_options = database.get_customer_names_with_phone() or []
    product_options = database.get_product_names() or []
    
    with ui.column().classes('w-full max-w-7xl mx-auto p-6 gap-6'):
        with ui.row().classes('w-full justify-between items-center'):
            with ui.column().classes('gap-1'):
                ui.label('🧾 Billing & Point of Sale (POS)').classes('text-2xl font-black text-slate-900')
                ui.label('Create fast retail invoices with instant Thermal and A4 receipts').classes('text-sm text-slate-500 font-medium')
            ui.button('Clear Cart', icon='delete_sweep', on_click=lambda: clear_cart()).props('flat color=negative rounded')

        # Split: Left side (Item entry & Cart table) | Right side (Totals & Checkout)
        with ui.row().classes('w-full items-start gap-6'):
            # LEFT SIDE (2/3 width)
            with ui.column().classes('flex-1 min-w-[340px] gap-4'):
                # 1. Customer Selection Card
                with ui.card().classes('w-full p-5 rounded-2xl bg-white border border-slate-200 shadow-sm'):
                    ui.label('1. Customer Information').classes('text-sm font-bold text-slate-700 uppercase tracking-wider mb-2')
                    with ui.row().classes('w-full items-center gap-3'):
                        cust_select = ui.select(
                            options=customer_options,
                            label='Select Customer (or Cash Customer)',
                            with_input=True
                        ).classes('flex-1').props('outlined dense')
                        
                        def open_add_customer_dialog():
                            with ui.dialog() as dlg, ui.card().classes('w-96 p-6 rounded-2xl'):
                                ui.label('➕ Register New Customer').classes('text-lg font-bold text-slate-800 mb-2')
                                c_name = ui.input('Customer Full Name').classes('w-full').props('outlined dense autofocus')
                                c_phone = ui.input('Mobile Number (Optional)').classes('w-full').props('outlined dense')
                                c_addr = ui.input('Address / Locality (Optional)').classes('w-full').props('outlined dense')
                                
                                def save_new_cust():
                                    name = c_name.value.strip()
                                    if not name:
                                        ui.notify('Customer name is required', type='warning')
                                        return
                                    phone = c_phone.value.strip()
                                    addr = c_addr.value.strip()
                                    database.get_or_create_customer(name, phone, addr)
                                    ui.notify(f'Customer "{name}" registered!', type='positive')
                                    # Refresh options
                                    new_opts = database.get_customer_names_with_phone()
                                    cust_select.options = new_opts
                                    # Select the newly added customer
                                    for opt in new_opts:
                                        if name in opt:
                                            cust_select.value = opt
                                            break
                                    dlg.close()
                                
                                with ui.row().classes('w-full justify-end gap-2 mt-4'):
                                    ui.button('Cancel', on_click=dlg.close).props('flat text-slate-600')
                                    ui.button('Save Customer', on_click=save_new_cust).props('unelevated color=primary')
                            dlg.open()

                        ui.button('+ Add New', icon='person_add', on_click=open_add_customer_dialog).props('outline color=primary rounded').classes('font-semibold')

                # 2. Item Entry Card
                with ui.card().classes('w-full p-5 rounded-2xl bg-white border border-slate-200 shadow-sm'):
                    ui.label('2. Add Products to Cart').classes('text-sm font-bold text-slate-700 uppercase tracking-wider mb-2')
                    
                    with ui.row().classes('w-full items-center gap-3'):
                        prod_select = ui.select(
                            options=product_options,
                            label='Search Product (Paints, Hardware, Thinners...)',
                            with_input=True
                        ).classes('w-full md:flex-1').props('outlined dense')

                    with ui.row().classes('w-full items-center gap-3 mt-2'):
                        qty_input = ui.number('Qty', value=1, min=1, step=1).classes('w-24').props('outlined dense')
                        unit_label = ui.label('Unit: -').classes('text-xs text-slate-500 font-semibold w-20 self-center')
                        price_input = ui.number('Selling Rate (₹)', value=0.0, format='%.2f').classes('w-36').props('outlined dense')
                        mrp_label = ui.label('MRP: -').classes('text-xs text-slate-400 w-24 self-center')
                        stock_badge = ui.badge('Stock: -', color='slate').props('rounded').classes('self-center text-xs')
                        disc_input = ui.number('Discount %', value=0.0, min=0, max=100, step=0.5).classes('w-28').props('outlined dense')
                        
                        def on_product_changed(e):
                            pname = prod_select.value
                            if not pname:
                                return
                            prod_details = database.get_product_complete_details(pname)
                            if prod_details:
                                # prod_details: (id, name, cat, mrp, selling_price, stock, unit, ...)
                                price_input.value = float(prod_details[4])
                                qty_input.value = 1
                                unit_str = prod_details[6] or "Pcs"
                                unit_label.text = f'Unit: {unit_str}'
                                mrp_label.text = f'MRP: ₹{prod_details[3]:.0f}'
                                curr_stock = prod_details[5]
                                stock_badge.text = f'Stock: {curr_stock}'
                                stock_badge.props(f'color={"emerald" if curr_stock > 10 else "amber" if curr_stock > 0 else "red"}')
                        
                        prod_select.on_value_change(on_product_changed)

                        def add_item_to_cart():
                            pname = prod_select.value
                            if not pname:
                                ui.notify('Please select a product first', type='warning')
                                return
                            prod_details = database.get_product_complete_details(pname)
                            if not prod_details:
                                ui.notify('Product not found in database', type='negative')
                                return
                            
                            qty = int(qty_input.value or 1)
                            price = float(price_input.value or 0.0)
                            disc = float(disc_input.value or 0.0)
                            unit_str = prod_details[6] or "Pcs"
                            mrp_val = float(prod_details[3] or price)
                            
                            effective_price = price - (price * disc / 100.0)
                            item_total = effective_price * qty
                            
                            # Check if already in cart
                            existing = next((item for item in cart_items if item['product_id'] == prod_details[0]), None)
                            if existing:
                                existing['quantity'] += qty
                                existing['total'] = existing['quantity'] * (existing['price'] - (existing['price'] * existing['discount'] / 100.0))
                            else:
                                cart_items.append({
                                    'sno': len(cart_items) + 1,
                                    'product_id': prod_details[0],
                                    'name': pname,
                                    'quantity': qty,
                                    'unit': unit_str,
                                    'mrp': mrp_val,
                                    'price': price,
                                    'discount': disc,
                                    'total': item_total
                                })
                            
                            # Reset input
                            prod_select.value = None
                            price_input.value = 0.0
                            qty_input.value = 1
                            disc_input.value = 0.0
                            unit_label.text = 'Unit: -'
                            mrp_label.text = 'MRP: -'
                            stock_badge.text = 'Stock: -'
                            
                            refresh_cart_ui()
                            ui.notify(f'Added {pname} to cart', type='positive', icon='add_shopping_cart')

                        ui.button('Add to Bill (Enter)', icon='add', on_click=add_item_to_cart).props('unelevated color=emerald-600 rounded').classes('font-bold ml-auto')

                # 3. Cart Table Card
                with ui.card().classes('w-full p-5 rounded-2xl bg-white border border-slate-200 shadow-sm'):
                    ui.label('3. Current Bill Items').classes('text-sm font-bold text-slate-700 uppercase tracking-wider mb-2')
                    cart_container = ui.column().classes('w-full')

            # RIGHT SIDE (1/3 width): Bill Summary & Checkout
            with ui.card().classes('w-full lg:w-96 p-6 rounded-2xl bg-white border border-slate-200 shadow-sm flex flex-col gap-4'):
                ui.label('Bill Summary & Payment').classes('text-lg font-black text-slate-900 border-b border-slate-200 pb-3')
                
                with ui.column().classes('w-full gap-2 text-sm'):
                    with ui.row().classes('w-full justify-between items-center'):
                        ui.label('Subtotal:').classes('text-slate-600 font-medium')
                        subtotal_lbl = ui.label('₹0.00').classes('font-bold text-slate-800')
                    
                    with ui.row().classes('w-full justify-between items-center'):
                        ui.label('Extra Discount (₹):').classes('text-slate-600 font-medium')
                        bill_disc_input = ui.number(value=0.0, min=0, format='%.2f').classes('w-28').props('outlined dense')
                    
                    with ui.row().classes('w-full justify-between items-center pt-3 border-t border-slate-200'):
                        ui.label('Grand Total:').classes('text-base font-extrabold text-slate-900')
                        grand_total_lbl = ui.label('₹0.00').classes('text-2xl font-black text-blue-600')

                ui.separator().classes('my-2')
                
                # Payment Mode
                ui.label('Payment Method').classes('text-xs font-bold text-slate-500 uppercase tracking-wider')
                pay_mode_select = ui.select(
                    options=['Cash', 'UPI / QR', 'Credit / Udhar', 'Card', 'Cheque'],
                    value='Cash'
                ).classes('w-full').props('outlined dense')
                
                # Amount Paid & Due
                amount_paid_input = ui.number('Amount Received (₹)', value=0.0, min=0, format='%.2f').classes('w-full').props('outlined dense')
                
                with ui.row().classes('w-full justify-between items-center p-3 bg-slate-50 rounded-xl border border-slate-200'):
                    ui.label('Remaining Due:').classes('text-xs font-bold text-slate-600')
                    due_lbl = ui.label('₹0.00').classes('text-sm font-black text-rose-600')
                
                def update_checkout_calculations(*args):
                    subtot = sum(it['total'] for it in cart_items)
                    extra_disc = float(bill_disc_input.value or 0.0)
                    gtotal = max(0.0, subtot - extra_disc)
                    subtotal_lbl.text = f'₹{subtot:,.2f}'
                    grand_total_lbl.text = f'₹{gtotal:,.2f}'
                    
                    if pay_mode_select.value == 'Credit / Udhar':
                        if amount_paid_input.value == gtotal:
                            amount_paid_input.value = 0.0
                    else:
                        if amount_paid_input.value == 0.0 and gtotal > 0:
                            amount_paid_input.value = gtotal
                            
                    paid_val = float(amount_paid_input.value or 0.0)
                    rem_due = max(0.0, gtotal - paid_val)
                    due_lbl.text = f'₹{rem_due:,.2f}'

                bill_disc_input.on_value_change(update_checkout_calculations)
                pay_mode_select.on_value_change(update_checkout_calculations)
                amount_paid_input.on_value_change(update_checkout_calculations)

                # Final Button
                def generate_and_save_invoice():
                    if not cart_items:
                        ui.notify('Cart is empty. Add products first.', type='warning')
                        return
                    
                    # Resolve Customer
                    c_sel = cust_select.value or ""
                    c_name = c_sel.split(' (')[0].strip() if '(' in c_sel else c_sel.strip()
                    if not c_name:
                        c_name = "Cash Customer"
                        c_phone = ""
                    else:
                        c_phone = c_sel.split('(')[1].replace(')', '').strip() if '(' in c_sel else ""

                    subtot = sum(it['total'] for it in cart_items)
                    extra_disc = float(bill_disc_input.value or 0.0)
                    gtotal = max(0.0, subtot - extra_disc)
                    pmode = pay_mode_select.value
                    paid_val = float(amount_paid_input.value or 0.0)
                    
                    # Format items for save_complete_invoice:
                    # expects list of dicts with keys: product_id, name, quantity, mrp, price, unit, discount, discount_base, total
                    db_items = []
                    for it in cart_items:
                        db_items.append({
                            'product_id': it['product_id'],
                            'name': it['name'],
                            'quantity': it['quantity'],
                            'mrp': it['mrp'],
                            'price': it['price'],
                            'unit': it['unit'],
                            'discount': it['discount'],
                            'discount_base': 'Price',
                            'total': it['total']
                        })

                    try:
                        inv_num = database.save_complete_invoice(
                            customer_name=c_name,
                            cart_items=db_items,
                            grand_total=gtotal,
                            paid_amount=paid_val,
                            note=f"Payment Mode: {pmode}"
                        )
                        ui.notify(f'Invoice {inv_num} generated successfully!', type='positive', icon='check_circle')
                        clear_cart()
                        show_receipt_modal(inv_num)
                    except Exception as ex:
                        ui.notify(f'Failed to save invoice: {ex}', type='negative')

                ui.button('⚡ Generate & Print Bill', icon='print', on_click=generate_and_save_invoice).props('unelevated color=primary rounded size=lg').classes('w-full font-bold shadow-lg mt-2')

    def clear_cart():
        cart_items.clear()
        refresh_cart_ui()

    def refresh_cart_ui():
        cart_container.clear()
        with cart_container:
            if not cart_items:
                ui.label('Your cart is currently empty. Use the box above to add items.').classes('text-slate-400 italic text-sm py-8 text-center w-full')
            else:
                columns = [
                    {'name': 'sno', 'label': '#', 'field': 'sno', 'align': 'left'},
                    {'name': 'name', 'label': 'Item', 'field': 'name', 'align': 'left'},
                    {'name': 'qty', 'label': 'Qty', 'field': 'qty', 'align': 'center'},
                    {'name': 'rate', 'label': 'Rate (₹)', 'field': 'rate', 'align': 'right'},
                    {'name': 'disc', 'label': 'Disc %', 'field': 'disc', 'align': 'right'},
                    {'name': 'total', 'label': 'Total (₹)', 'field': 'total', 'align': 'right'},
                    {'name': 'action', 'label': '', 'field': 'action', 'align': 'center'},
                ]
                rows = []
                for idx, it in enumerate(cart_items, 1):
                    it['sno'] = idx
                    rows.append({
                        'sno': idx,
                        'name': it['name'],
                        'qty': f"{it['quantity']} {it['unit']}",
                        'rate': f"₹{it['price']:.2f}",
                        'disc': f"{it['discount']}%",
                        'total': f"₹{it['total']:,.2f}",
                        'idx': idx - 1
                    })
                
                tbl = ui.table(columns=columns, rows=rows, row_key='sno').classes('w-full').props('flat bordered dense')
                tbl.add_slot('body-cell-action', '''
                    <q-td :props="props">
                        <q-btn flat dense round icon="delete" color="negative" @click="$parent.$emit('remove_row', props.row.idx)" />
                    </q-td>
                ''')
                
                def remove_row_from_cart(row_idx):
                    if 0 <= row_idx < len(cart_items):
                        del cart_items[row_idx]
                        refresh_cart_ui()
                
                tbl.on('remove_row', lambda e: remove_row_from_cart(e.args))
        
        update_checkout_calculations()

    # Initial render
    refresh_cart_ui()
    render_footer()
