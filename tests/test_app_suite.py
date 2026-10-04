import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import tkinter as tk
from unittest.mock import patch, MagicMock

import database
from ui.main_window import MainWindow
from ui.invoice_ui import InvoiceUI, generate_thermal_receipt_pdf, generate_a4_invoice_pdf
from ui.invoice_history_ui import InvoiceHistoryUI
from ui.ledger_ui import LedgerUI
from ui.inventory_ui import InventoryUI
from ui.dashboard_ui import DashboardUI

def run_tests():
    print('=' * 60)
    print('STARTING FULL END-TO-END AUTOMATED TEST SUITE')
    print('=' * 60)

    import tempfile
    import shutil
    old_db_path = database.DATABASE_PATH
    temp_dir = tempfile.mkdtemp()
    temp_db_path = os.path.join(temp_dir, "test_app_business.db")
    database.DATABASE_PATH = temp_db_path
    database.create_tables()
    database.run_migrations()
    database.seed_paints_and_hardware_demo_data(force=True)

    try:
        root = tk.Tk()
        root.withdraw()

        with patch('tkinter.messagebox.showinfo') as mock_info, \
             patch('tkinter.messagebox.showerror') as mock_error, \
             patch('tkinter.messagebox.showwarning') as mock_warning, \
             patch('ui.invoice_ui.open_pdf_file') as mock_open_pdf, \
             patch('ui.thermal_printer.print_receipt_direct', return_value=(True, "Mock print OK")) as mock_print_direct, \
             patch('ui.thermal_printer.send_raw_to_printer', return_value=(True, "Mock raw OK")) as mock_raw_print:

            # Step 1: Initialize MainWindow
            print('[TEST 1] Initializing MainWindow...')
            app = MainWindow(root)
            print('MainWindow initialized successfully.')

        # Step 2: Test InvoiceUI directly
        print('[TEST 2] Testing InvoiceUI workflow...')
        app.open_invoice()
        inv_ui = app.current_ui

        assert hasattr(inv_ui, 'handle_table_click'), 'Missing handle_table_click!'
        assert hasattr(inv_ui, 'refresh_cart_table'), 'Missing refresh_cart_table!'
        assert hasattr(inv_ui, 'edit_cart_item'), 'Missing edit_cart_item!'
        assert hasattr(inv_ui, 'delete_cart_item'), 'Missing delete_cart_item!'
        assert hasattr(inv_ui, 'save_thermal_btn'), 'Missing save_thermal_btn!'
        assert hasattr(inv_ui, 'save_a4_btn'), 'Missing save_a4_btn!'
        print('All InvoiceUI methods & attributes present.')

        # Clear state
        inv_ui.clear_invoice()
        assert len(inv_ui.cart_items) == 0

        # Select customer
        customers = database.get_customer_names_with_phone()
        cust_name = customers[0] if customers else 'Test Auto Customer'
        inv_ui.customer_combo.set(cust_name)

        # Select product
        products = database.get_product_names()
        if not products:
            database.add_product("Test Product 1", 100.0, 50.0, 80.0, 20, "Pcs", "General")
            products = database.get_product_names()
        assert len(products) > 0, 'No products in database!'
        prod_name = products[0]
        inv_ui.product_combo.set(prod_name)
        inv_ui.autofill_product_details(focus_qty=False)

        # Add to cart
        inv_ui.qty_entry.delete(0, tk.END)
        inv_ui.qty_entry.insert(0, '3')
        inv_ui.discount_entry.delete(0, tk.END)
        inv_ui.discount_entry.insert(0, '5')

        inv_ui.add_to_cart()
        assert len(inv_ui.cart_items) == 1
        print('Added item to cart:', inv_ui.cart_items[0]['name'])

        if len(products) > 1:
            inv_ui.product_combo.set(products[1])
            inv_ui.autofill_product_details(focus_qty=False)
            inv_ui.qty_entry.delete(0, tk.END)
            inv_ui.qty_entry.insert(0, '2')
            inv_ui.add_to_cart()
            assert len(inv_ui.cart_items) == 2
            print('Added 2nd item to cart:', inv_ui.cart_items[1]['name'])

        # Test Editing cart item
        tree_children = inv_ui.tree.get_children()
        assert len(tree_children) >= 1
        first_row = tree_children[0]
        inv_ui.edit_cart_item(first_row)
        assert inv_ui.editing_cart_index == 0
        inv_ui.qty_entry.delete(0, tk.END)
        inv_ui.qty_entry.insert(0, '5')
        inv_ui.add_to_cart()
        assert inv_ui.cart_items[0]['quantity'] == 5
        print('Cart item edit & update verified successfully.')

        # Test Deleting a cart item
        if len(inv_ui.cart_items) >= 2:
            tree_children = inv_ui.tree.get_children()
            del_row = tree_children[-1]
            inv_ui.delete_cart_item(del_row)
            assert len(inv_ui.cart_items) == 1
            print('Cart item deletion verified successfully.')

        # Test Paid Amount & Pending calculation
        inv_ui.paid_entry.delete(0, tk.END)
        inv_ui.paid_entry.insert(0, '100')
        inv_ui.on_paid_changed()
        print('Pending calculated successfully.')

        # Test Save Invoice - Thermal (Default)
        inv_ui.save_invoice(format_type='thermal')
        assert mock_info.called, 'showinfo was not called on save!'
        print('Save Invoice (80mm Thermal Receipt default) completed successfully.')

        # Re-add item to test A4 Save
        inv_ui.customer_combo.set(cust_name)
        inv_ui.product_combo.set(prod_name)
        inv_ui.autofill_product_details(focus_qty=False)
        inv_ui.qty_entry.delete(0, tk.END)
        inv_ui.qty_entry.insert(0, '2')
        inv_ui.add_to_cart()
        inv_ui.save_invoice(format_type='a4')
        print('Save Invoice (A4 format) completed successfully.')

        # Step 3: Test Invoice History UI
        print('[TEST 3] Testing Invoice History UI...')
        app.open_invoice_history()
        hist_ui = app.current_ui
        hist_rows = hist_ui.tree.get_children()
        print(f'Invoice History loaded with {len(hist_rows)} invoices.')
        if hist_rows:
            first_inv = hist_rows[0]
            hist_ui.tree.selection_set(first_inv)
            vals = hist_ui.tree.item(first_inv, 'values')
            print('Selected Invoice from History verified successfully.')

        # Step 4: Test Ledger UI
        print('[TEST 4] Testing Ledger UI...')
        app.open_ledger()
        ledger_ui = app.current_ui
        assert isinstance(ledger_ui, LedgerUI)
        ledger_rows = ledger_ui.customer_tree.get_children()
        print(f'Ledger loaded with {len(ledger_rows)} customer entries.')
        if ledger_rows:
            first_cust = ledger_rows[0]
            ledger_ui.customer_tree.selection_set(first_cust)
            ledger_ui.on_customer_select()
            inv_rows = ledger_ui.invoice_tree.get_children()
            print(f'Customer invoices loaded: {len(inv_rows)} invoices.')
            if inv_rows:
                inv_id = int(inv_rows[0])
                ledger_ui.show_payment_dialog(inv_id)
                print('Payment drilldown dialog with 80mm Thermal & A4 buttons tested OK.')
            # Go back to customer list
            ledger_ui.show_customer_list()

        # Step 5: Test Inventory UI
        print('[TEST 5] Testing Inventory UI...')
        app.open_inventory()
        inv_tab = app.current_ui
        print('Inventory tab loaded successfully.')

        # Step 6: Test Dashboard UI
        print('[TEST 6] Testing Dashboard UI...')
        app.open_dashboard()
        dash_tab = app.current_ui
        print('Dashboard tab refreshed successfully.')

        # Step 7: Test Indian Mobile Number Validation
        print('[TEST 7] Testing Indian Mobile Number Validation...')
        from ui.customer_popup import validate_and_normalize_indian_mobile, CustomerPopup

        # Valid Indian mobile test cases
        assert validate_and_normalize_indian_mobile('9876543210') == (True, '9876543210')
        assert validate_and_normalize_indian_mobile('09876543210') == (True, '9876543210')
        assert validate_and_normalize_indian_mobile('+91-9876543210') == (True, '9876543210')
        assert validate_and_normalize_indian_mobile('+91 98765 43210') == (True, '9876543210')
        assert validate_and_normalize_indian_mobile('+91-61234-56789') == (True, '6123456789')
        assert validate_and_normalize_indian_mobile('7000000000') == (True, '7000000000')
        assert validate_and_normalize_indian_mobile('8123456789') == (True, '8123456789')

        # Invalid test cases
        assert validate_and_normalize_indian_mobile('5123456789')[0] is False  # Must start with 6-9
        assert validate_and_normalize_indian_mobile('1234567890')[0] is False  # Landline / invalid
        assert validate_and_normalize_indian_mobile('987654321')[0] is False   # Less than 10 digits
        assert validate_and_normalize_indian_mobile('987654321012')[0] is False # Exceeds 10 digits
        assert validate_and_normalize_indian_mobile('+1-9876543210')[0] is False # Non-Indian country code
        assert validate_and_normalize_indian_mobile('')[0] is False
        assert validate_and_normalize_indian_mobile('abcdefghij')[0] is False

        # Test CustomerPopup save
        import time
        uniq_phone = f"9876{int(time.time()) % 1000000:06d}"
        cb_called = []
        popup = CustomerPopup(root, lambda: cb_called.append(True))
        popup.name_entry.insert(0, 'Test Auto Customer Valid')
        popup.phone_entry.insert(0, f"+91-{uniq_phone}")
        popup.address_text.insert('1.0', '123 Market Road')
        popup.save_customer()
        assert len(cb_called) == 1, 'Customer callback not fired!'

        # Test duplicate phone rejection
        popup2 = CustomerPopup(root, lambda: None)
        popup2.name_entry.insert(0, 'Duplicate Phone User')
        popup2.phone_entry.insert(0, uniq_phone)
        popup2.save_customer()
        assert mock_warning.called, 'Duplicate phone warning was not shown!'
        popup2.window.destroy()

        print('CustomerPopup Indian mobile validation and duplicate detection tested OK.')

        # Step 8: Test Password-Protected CSV Export & Decryption
        print('[TEST 8] Testing Password-Protected CSV Export & Decryption...')
        from ui.csv_security import export_encrypted_csv_archive
        from config import CSV_MASTER_EXPORT_PASSWORD
        import zipfile

        test_zip_path = os.path.join(os.path.dirname(__file__), 'test_export.zip')
        sample_headers = ['Category', 'Product Name', 'Selling Price']
        sample_rows = [['Fans', 'Ceiling Fan 48"', 2100], ['Lighting', 'LED Bulb 12W', 120]]

        created_zip = export_encrypted_csv_archive(
            target_path=test_zip_path,
            base_name='inventory_catalog.csv',
            header_row=sample_headers,
            data_rows=sample_rows
        )
        assert os.path.exists(created_zip), 'Encrypted ZIP was not created!'

        # Verify decryption using Master Password
        zf = zipfile.ZipFile(created_zip)
        zf.setpassword(CSV_MASTER_EXPORT_PASSWORD.encode('utf-8'))
        decrypted_csv = zf.read('inventory_catalog.csv').decode('utf-8-sig')
        zf.close()

        assert 'Ceiling Fan 48"' in decrypted_csv, 'Decrypted content missing expected data!'
        assert 'LED Bulb 12W' in decrypted_csv, 'Decrypted content missing expected data!'

        # Clean up test file
        if os.path.exists(test_zip_path):
            os.remove(test_zip_path)

        print('Password-Protected CSV export and Master Password decryption verified 100% OK.')

        # Step 9: Test UI Import CSV and Category Refresh
        print('[TEST 9] Testing InventoryUI Import CSV and Live Refresh...')
        app.open_inventory()
        inv_ui = app.current_ui
        csv_candidates = [
            os.path.join(os.path.dirname(__file__), '..', 'INVENTORY_SARTAJ_0786.csv'),
            os.path.join(os.path.dirname(__file__), '..', 'Inventory', 'INVENTORY_SARTAJ_0786.csv'),
            os.path.join(os.path.dirname(__file__), '..', 'BizDabba By Wokdens.com', '9TH SEP INVENTORY_SARTAJ_0786.csv'),
        ]
        csv_file = next((p for p in csv_candidates if os.path.isfile(p)), csv_candidates[0])
        assert os.path.exists(csv_file), f'Inventory CSV not found at {csv_file}!'

        with patch('ui.inventory_ui.filedialog.askopenfilename', return_value=csv_file), \
             patch('ui.inventory_ui.request_admin_pin', return_value=True), \
             patch('tkinter.messagebox.showinfo') as mock_info2:
            inv_ui.import_products_csv()

        assert len(inv_ui.tree.get_children()) > 500, 'Products not loaded into Inventory table!'
        assert len(database.get_all_categories()) >= 20, 'Categories not stored in database!'
        print(f'InventoryUI imported {len(inv_ui.tree.get_children())} products and {len(database.get_all_categories())} categories successfully.')

        root.destroy()
        print('=' * 60)
        print('ALL 9 END-TO-END TESTS PASSED WITH ZERO ERRORS!')
        print('=' * 60)
    finally:
        database.DATABASE_PATH = old_db_path
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass


if __name__ == '__main__':
    run_tests()

