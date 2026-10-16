from nicegui import ui
import database
from web.layout import render_header, render_footer, is_admin, require_admin_dialog

def inventory_page():
    render_header(active_page="inventory")
    
    products_list = database.get_all_products() or []
    categories = ['All'] + (database.get_all_categories() or [])
    selected_category = {'val': 'All'}
    search_query = {'val': ''}
    
    with ui.column().classes('w-full max-w-7xl mx-auto p-6 gap-6'):
        # Header & Add Product Button
        with ui.row().classes('w-full justify-between items-center'):
            with ui.column().classes('gap-1'):
                ui.label('📦 Inventory & Stock Management').classes('text-2xl font-black text-slate-900')
                ui.label('Monitor stock levels, prices, and catalog items in real-time').classes('text-sm text-slate-500 font-medium')
            
            def open_add_product_dialog():
                with ui.dialog() as dlg, ui.card().classes('w-[480px] p-6 rounded-2xl'):
                    ui.label('➕ Add New Catalog Product').classes('text-lg font-bold text-slate-800 mb-2')
                    p_name = ui.input('Product Name').classes('w-full').props('outlined dense autofocus')
                    p_cat = ui.select(options=categories[1:] if len(categories) > 1 else ['Paints', 'Hardware', 'Thinners', 'Waterproofing'], label='Category', value='Paints').classes('w-full').props('outlined dense')
                    
                    with ui.row().classes('w-full gap-2'):
                        p_stock = ui.number('Initial Stock', value=10, min=0).classes('flex-1').props('outlined dense')
                        p_unit = ui.select(options=['Ltr', 'Kg', 'Pcs', 'Box', 'Roll', 'Bag', 'Coil'], label='Unit', value='Ltr').classes('w-32').props('outlined dense')
                    
                    with ui.row().classes('w-full gap-2'):
                        p_cost = ui.number('Cost Price (₹)', value=0.0, min=0).classes('flex-1').props('outlined dense')
                        p_price = ui.number('Selling Price (₹)', value=0.0, min=0).classes('flex-1').props('outlined dense')
                        p_mrp = ui.number('MRP (₹)', value=0.0, min=0).classes('flex-1').props('outlined dense')

                    def save_product():
                        name = p_name.value.strip()
                        if not name:
                            ui.notify('Product name is required', type='warning')
                            return
                        try:
                            database.add_product(
                                name=name,
                                category=p_cat.value,
                                cost_price=float(p_cost.value or 0),
                                selling_price=float(p_price.value or 0),
                                stock=int(p_stock.value or 0),
                                mrp=float(p_mrp.value or 0),
                                unit=p_unit.value
                            )
                            ui.notify(f'Product "{name}" added to inventory!', type='positive', icon='check_circle')
                            dlg.close()
                            refresh_table()
                        except Exception as e:
                            ui.notify(f'Failed to add product: {e}', type='negative')

                    with ui.row().classes('w-full justify-end gap-2 mt-4'):
                        ui.button('Cancel', on_click=dlg.close).props('flat text-slate-600')
                        ui.button('Save Product', on_click=save_product).props('unelevated color=primary')
                dlg.open()

            ui.button('+ Add Product', icon='add_box', on_click=open_add_product_dialog).props('unelevated color=primary rounded').classes('font-bold')

        # Filters: Search & Category Chips
        with ui.card().classes('w-full p-4 rounded-2xl bg-white border border-slate-200 shadow-sm gap-3'):
            with ui.row().classes('w-full items-center gap-3'):
                search_input = ui.input(placeholder='Search product name, code, brand...').classes('flex-1').props('outlined dense clearable')
                ui.icon('search', size='sm').classes('text-slate-400')
            
            with ui.row().classes('w-full gap-1 items-center flex-wrap'):
                ui.label('Category:').classes('text-xs font-bold text-slate-500 mr-2')
                for cat in categories:
                    def make_filter(c):
                        return lambda: set_filter(c)
                    ui.button(cat, on_click=make_filter(cat)).props('outline rounded dense').classes('text-xs font-semibold px-3 py-1')

        # Products Table Container
        table_container = ui.column().classes('w-full')

    def set_filter(cat):
        selected_category['val'] = cat
        refresh_table()

    def on_search(e):
        search_query['val'] = search_input.value or ''
        refresh_table()

    search_input.on_value_change(on_search)

    def refresh_table():
        table_container.clear()
        prods = database.get_all_products() or []
        
        # Filter by category
        if selected_category['val'] != 'All':
            prods = [p for p in prods if (len(p) > 2 and str(p[2]).lower() == selected_category['val'].lower())]
            
        # Filter by search
        sq = search_query['val'].strip().lower()
        if sq:
            prods = [p for p in prods if sq in str(p[1]).lower() or (len(p) > 2 and sq in str(p[2]).lower())]

        with table_container:
            with ui.card().classes('w-full p-4 rounded-2xl bg-white border border-slate-200 shadow-sm'):
                with ui.row().classes('w-full justify-between items-center mb-2'):
                    ui.label(f'Showing {len(prods)} products').classes('text-xs font-bold text-slate-500')
                    if selected_category['val'] != 'All':
                        ui.badge(f'Category: {selected_category["val"]}', color='blue-500').props('rounded')

                columns = [
                    {'name': 'id', 'label': '#', 'field': 'id', 'align': 'left'},
                    {'name': 'name', 'label': 'Product Description', 'field': 'name', 'align': 'left'},
                    {'name': 'cat', 'label': 'Category', 'field': 'cat', 'align': 'left'},
                    {'name': 'unit', 'label': 'Unit', 'field': 'unit', 'align': 'center'},
                    {'name': 'stock', 'label': 'Current Stock', 'field': 'stock', 'align': 'center'},
                    {'name': 'price', 'label': 'Selling Price', 'field': 'price', 'align': 'right'},
                    {'name': 'mrp', 'label': 'MRP', 'field': 'mrp', 'align': 'right'},
                    {'name': 'actions', 'label': 'Quick Actions', 'field': 'actions', 'align': 'center'},
                ]
                
                rows = []
                for p in prods:
                    # p: (id, name, category, cost_price, selling_price, stock, unit, mrp)
                    pid = p[0]
                    pname = p[1]
                    pcat = p[2] if len(p) > 2 else "General"
                    try:
                        pprice = float(p[4] if len(p) > 4 and p[4] is not None else 0.0)
                    except Exception:
                        pprice = 0.0
                    try:
                        pstock = int(p[5] if len(p) > 5 and p[5] is not None else 0)
                    except Exception:
                        pstock = 0
                    punit = p[6] if len(p) > 6 and p[6] else "Pcs"
                    try:
                        pmrp = float(p[7] if len(p) > 7 and p[7] is not None else pprice)
                    except Exception:
                        pmrp = pprice
                    
                    rows.append({
                        'id': pid,
                        'name': pname,
                        'cat': pcat,
                        'unit': punit,
                        'stock': pstock,
                        'price': f'₹{pprice:,.0f}',
                        'mrp': f'₹{pmrp:,.0f}',
                        'raw_stock': pstock,
                        'raw_id': pid,
                        'raw_name': pname
                    })
                
                tbl = ui.table(columns=columns, rows=rows, row_key='id').classes('w-full').props('flat bordered dense')
                
                tbl.add_slot('body-cell-stock', '''
                    <q-td :props="props">
                        <q-badge :color="props.row.raw_stock > 10 ? 'emerald' : props.row.raw_stock > 0 ? 'amber' : 'red'" text-color="white" rounded>
                            {{ props.row.stock }} {{ props.row.unit }}
                        </q-badge>
                    </q-td>
                ''')
                
                tbl.add_slot('body-cell-actions', '''
                    <q-td :props="props">
                        <q-btn flat dense icon="edit" color="primary" label="Stock" @click="$parent.$emit('adjust_stock', props.row)" />
                    </q-td>
                ''')
                
                def open_stock_adjust_dialog(row_data):
                    with ui.dialog() as dlg, ui.card().classes('w-96 p-6 rounded-2xl'):
                        ui.label('📦 Adjust Stock Level').classes('text-lg font-bold text-slate-800')
                        ui.label(row_data['raw_name']).classes('text-xs text-slate-500 font-semibold mb-3 truncate')
                        
                        new_stock_input = ui.number('New Total Stock', value=row_data['raw_stock'], min=0).classes('w-full').props('outlined dense autofocus')
                        reason_input = ui.input('Reason (e.g. Incoming shipment, count sync)').classes('w-full').props('outlined dense')

                        def apply_stock():
                            n_stock = int(new_stock_input.value or 0)
                            database.update_stock(row_data['raw_id'], n_stock)
                            database.record_audit_log(
                                action_type="STOCK_UPDATE",
                                description=f"Updated stock for {row_data['raw_name']} from {row_data['raw_stock']} to {n_stock}. Reason: {reason_input.value.strip() or 'Direct adjustment'}",
                                authorized_by="Admin" if is_admin() else "Operator"
                            )
                            ui.notify(f'Stock updated to {n_stock}!', type='positive')
                            dlg.close()
                            refresh_table()

                        with ui.row().classes('w-full justify-end gap-2 mt-4'):
                            ui.button('Cancel', on_click=dlg.close).props('flat text-slate-600')
                            ui.button('Save Changes', on_click=apply_stock).props('unelevated color=primary')
                    dlg.open()

                tbl.on('adjust_stock', lambda e: open_stock_adjust_dialog(e.args))

    refresh_table()
    render_footer()
