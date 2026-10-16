from nicegui import ui
import database
from web.layout import render_header, render_footer, is_admin, require_admin_dialog

def audit_page():
    render_header(active_page="audit")
    
    # Check authentication
    if not is_admin():
        with ui.column().classes('w-full max-w-7xl mx-auto p-6 gap-6'):
            with ui.card().classes('w-full max-w-md mx-auto p-8 rounded-2xl bg-white border border-slate-200 shadow-md text-center items-center my-12'):
                ui.icon('lock', size='xl').classes('text-blue-600 mb-2')
                ui.label('Admin Authentication Required').classes('text-xl font-black text-slate-800')
                ui.label('Audit trails and security records require the Owner/Admin PIN to unlock.').classes('text-xs text-slate-500 mb-4')
                
                pin_input = ui.input(placeholder='Enter PIN (e.g. 8160)', password=True).classes('w-full').props('outlined dense autofocus')
                
                def try_unlock():
                    if database.verify_admin_pin(pin_input.value.strip()):
                        from web.layout import set_admin_authenticated
                        set_admin_authenticated(True)
                        ui.notify('Security Area Unlocked', type='positive', icon='check_circle')
                        ui.navigate.to('/audit')
                    else:
                        ui.notify('Invalid PIN. Access denied.', type='negative')
                        pin_input.value = ''
                        
                ui.button('Unlock Audit Area', icon='key', on_click=try_unlock).props('unelevated color=primary rounded').classes('w-full font-bold mt-2')
        render_footer()
        return

    with ui.column().classes('w-full max-w-7xl mx-auto p-6 gap-6'):

        # Authenticated Admin View
        with ui.row().classes('w-full justify-between items-center'):
            with ui.column().classes('gap-1'):
                ui.label('🛡️ Security Audit Trails & Event Logs').classes('text-2xl font-black text-slate-900')
                ui.label('Tamper-evident logs of billing, price overrides, payments, and system events').classes('text-sm text-slate-500 font-medium')
            
            def open_change_pin_dialog():
                with ui.dialog() as dlg, ui.card().classes('w-96 p-6 rounded-2xl'):
                    ui.label('🔑 Change Admin PIN').classes('text-lg font-bold text-slate-800 mb-2')
                    curr_pin = ui.input('Current PIN', password=True).classes('w-full').props('outlined dense autofocus')
                    new_pin = ui.input('New 4-digit PIN', password=True).classes('w-full').props('outlined dense')
                    conf_pin = ui.input('Confirm New PIN', password=True).classes('w-full').props('outlined dense')

                    def save_pin():
                        if not database.verify_admin_pin(curr_pin.value.strip()):
                            ui.notify('Current PIN is incorrect', type='negative')
                            return
                        np = new_pin.value.strip()
                        if len(np) < 4:
                            ui.notify('New PIN must be at least 4 digits', type='warning')
                            return
                        if np != conf_pin.value.strip():
                            ui.notify('New PIN confirmation does not match', type='warning')
                            return
                        database.set_admin_pin(np)
                        database.record_audit_log('ADMIN_PIN_CHANGED', 'Owner Admin PIN updated', authorized_by='Owner PIN')
                        ui.notify('Admin PIN successfully updated!', type='positive', icon='check_circle')
                        dlg.close()

                    with ui.row().classes('w-full justify-end gap-2 mt-4'):
                        ui.button('Cancel', on_click=dlg.close).props('flat text-slate-600')
                        ui.button('Update PIN', on_click=save_pin).props('unelevated color=primary')
                dlg.open()

            ui.button('Change Admin PIN', icon='lock_reset', on_click=open_change_pin_dialog).props('outline color=slate-700 rounded').classes('font-semibold')

        # Fetch Logs
        logs = database.get_audit_logs(limit=200) or []
        
        with ui.card().classes('w-full p-5 rounded-2xl bg-white border border-slate-200 shadow-sm'):
            with ui.row().classes('w-full justify-between items-center mb-3'):
                ui.label(f'Audit History ({len(logs)} most recent security records)').classes('text-xs font-bold text-slate-500')
                ui.badge('Protected Area', color='emerald-500').props('rounded')

            columns = [
                {'name': 'id', 'label': '#', 'field': 'id', 'align': 'left'},
                {'name': 'time', 'label': 'Date & Time', 'field': 'time', 'align': 'left'},
                {'name': 'type', 'label': 'Event Type', 'field': 'type', 'align': 'center'},
                {'name': 'desc', 'label': 'Event Description', 'field': 'desc', 'align': 'left'},
                {'name': 'auth', 'label': 'Authorized By', 'field': 'auth', 'align': 'center'},
            ]
            
            rows = []
            for l in logs:
                # l: (id, timestamp, action_type, description, authorized_by)
                lid, ltime, ltype, ldesc, lauth = l
                rows.append({
                    'id': lid,
                    'time': ltime,
                    'type': ltype,
                    'desc': ldesc,
                    'auth': lauth
                })

            tbl = ui.table(columns=columns, rows=rows, row_key='id').classes('w-full').props('flat bordered dense')
            tbl.add_slot('body-cell-type', '''
                <q-td :props="props">
                    <q-badge :color="props.row.type.includes('PIN') || props.row.type.includes('MASTER') ? 'amber-500' : props.row.type.includes('PAYMENT') ? 'emerald-500' : 'blue-500'" text-color="white" rounded>
                        {{ props.row.type }}
                    </q-badge>
                </q-td>
            ''')

    render_footer()
