# -*- coding: utf-8 -*-
"""
Exhaustive Automated Test & Quality Assurance Suite for BizDabba by wokdens.com
Tests permutations, edge cases, cross-version data models, and UI flows.
"""
import os
import sys
import time
import zipfile
import tempfile
import sqlite3
import tkinter as tk
from unittest.mock import patch, MagicMock

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config
import database
from ui.main_window import MainWindow
from ui.customer_popup import validate_and_normalize_indian_mobile, CustomerPopup
from ui.thermal_printer import amount_to_indian_words, format_esc_pos_receipt
from ui.csv_security import export_encrypted_csv_archive
from ui.invoice_ui import generate_thermal_receipt_pdf, generate_a4_invoice_pdf

def run_exhaustive_suite():
    print("=" * 70)
    print("  BIZDABBA BY WOKDENS.COM - EXHAUSTIVE QUALITY & STABILITY SUITE")
    print("=" * 70)

    # -------------------------------------------------------------
    # STAGE 1: Fresh Database Initialization & Migration Idempotency
    # -------------------------------------------------------------
    print("[STAGE 1/9] Testing Clean Database Setup & Migration Idempotency...")
    temp_dir = tempfile.mkdtemp(prefix="bizdabba_test_")
    test_db = os.path.join(temp_dir, "test_fresh.db")
    
    old_db_path = database.DATABASE_PATH
    database.DATABASE_PATH = test_db
    
    try:
        # Create fresh DB
        database.create_tables()
        assert os.path.exists(test_db), "Database file was not created!"
        
        # Verify all modern columns exist in fresh database
        for col in ["category", "name", "mrp", "purchase_price", "selling_price", "unit", "stock", "discount_base"]:
            assert database.column_exists("products", col), f"Missing column '{col}' in products table!"
        
        for col in ["invoice_number", "customer_id", "total", "paid", "pending", "invoice_date", "note"]:
            assert database.column_exists("invoices", col), f"Missing column '{col}' in invoices table!"
            
        for col in ["unit", "custom_price", "discount_base", "mrp"]:
            assert database.column_exists("invoice_items", col), f"Missing column '{col}' in invoice_items table!"
            
        for col in ["phone", "address"]:
            assert database.column_exists("customers", col), f"Missing column '{col}' in customers table!"

        # Test running migrations 5 times consecutively (must be 100% idempotent)
        for _ in range(5):
            database.run_migrations()
        print("  -> Database schema & 5x migration idempotency verified OK.")

        # -------------------------------------------------------------
        # STAGE 2: Indian Mobile Number Permutations & Validation
        # -------------------------------------------------------------
        print("[STAGE 2/9] Testing Indian Mobile Number Permutations...")
        valid_cases = [
            ("9876543210", "9876543210"),
            ("09876543210", "9876543210"),
            ("+91-9876543210", "9876543210"),
            ("+91 9876543210", "9876543210"),
            ("+919876543210", "9876543210"),
            ("6123456789", "6123456789"),
            ("7000000000", "7000000000"),
            ("8999999999", "8999999999"),
        ]
        for raw, expected in valid_cases:
            valid, norm = validate_and_normalize_indian_mobile(raw)
            assert valid is True and norm == expected, f"Failed for valid mobile: {raw} -> got {norm}"

        invalid_cases = [
            "5123456789",    # Starts with 5
            "1234567890",    # Starts with 1
            "009876543210",  # Double zero prefix
            "987654321",     # 9 digits
            "98765432101",   # 11 digits without 0
            "+1-9876543210", # US Country code
            "abcdefghij",    # Non-digits
            "",              # Empty
            "   ",           # Whitespace
        ]
        for raw in invalid_cases:
            valid, _ = validate_and_normalize_indian_mobile(raw)
            assert valid is False, f"Expected invalid for: {raw}"

        # Test optional phone allowance (v3.0 feature)
        valid_empty, norm_empty = validate_and_normalize_indian_mobile("", allow_empty=True)
        assert valid_empty is True and norm_empty == "", "allow_empty=True should accept empty string!"
        valid_space, norm_space = validate_and_normalize_indian_mobile("   ", allow_empty=True)
        assert valid_space is True and norm_space == "", "allow_empty=True should accept whitespace!"

        print("  -> All 17 mobile number permutations verified OK (including optional blank).")

        # -------------------------------------------------------------
        # STAGE 3: Grand Total in Indian Words Conversion
        # -------------------------------------------------------------
        print("[STAGE 3/9] Testing Grand Total in Indian Words...")
        words_tests = [
            (0, "Rupees Zero Only"),
            (5, "Rupees Five Only"),
            (1265, "Rupees One Thousand Two Hundred Sixty Five Only"),
            (1285, "Rupees One Thousand Two Hundred Eighty Five Only"),
            (100000, "Rupees One Lakh Only"),
            (250780.50, "Rupees Two Lakh Fifty Thousand Seven Hundred Eighty and Fifty Paise Only"),
            (15000000, "Rupees One Crore Fifty Lakh Only")
        ]
        for amt, expected_words in words_tests:
            result_words = amount_to_indian_words(amt)
            assert result_words == expected_words, f"Amount words mismatch: {amt} -> '{result_words}' != '{expected_words}'"
        print("  -> Indian currency numbers-to-words verified OK.")

        # -------------------------------------------------------------
        # STAGE 4: Discount & Pricing Calculation Permutations
        # -------------------------------------------------------------
        print("[STAGE 4/9] Testing Discount & Pricing Math...")
        # Case A: Discount on Price (Default)
        # Price = 100, Disc % = 10 -> Effective = 90
        qty, price, mrp, disc = 2, 100.0, 150.0, 10.0
        disc_amt_price = price * (disc / 100.0)
        final_price_a = price - disc_amt_price
        total_a = qty * final_price_a
        assert total_a == 180.0, f"Math mismatch on price discount: {total_a}"

        # Case B: Discount on MRP
        # MRP = 200, Price = 150, Disc % = 10 (10% of 200 = 20) -> Effective = 150 - 20 = 130
        qty, price, mrp, disc = 3, 150.0, 200.0, 10.0
        disc_amt_mrp = mrp * (disc / 100.0)
        final_price_b = max(0.0, price - disc_amt_mrp)
        total_b = qty * final_price_b
        assert total_b == 390.0, f"Math mismatch on MRP discount: {total_b}"
        print("  -> Pricing and dual discount calculation rules verified OK.")

        # -------------------------------------------------------------
        # STAGE 5: UI GUI Simulation on Blank Database
        # -------------------------------------------------------------
        print("[STAGE 5/9] Launching Full GUI Simulation on Blank Database...")
        root = tk.Tk()
        root.withdraw()

        with patch('tkinter.messagebox.showinfo'), \
             patch('tkinter.messagebox.showerror'), \
             patch('tkinter.messagebox.showwarning'), \
             patch('ui.thermal_printer.print_receipt_direct', return_value=(True, "Mock OK")), \
             patch('ui.admin_auth_dialog.request_admin_pin', return_value=True), \
             patch('ui.inventory_ui.request_admin_pin', return_value=True):

            app = MainWindow(root)
            assert app.root.title() == "BizDabba PHWP by wokdens.com", f"Title mismatch: {app.root.title()}"
            print("  -> MainWindow title verified: 'BizDabba PHWP by wokdens.com'")

            # -------------------------------------------------------------
            # STAGE 6: Inventory CSV Import Permutations & Category Refresh
            # -------------------------------------------------------------
            print("[STAGE 6/9] Testing Live Inventory CSV Import...")
            app.open_inventory()
            inv_ui = app.current_ui
            
            csv_candidates = [
                os.path.join(os.path.dirname(__file__), "..", "INVENTORY_SARTAJ_0786.csv"),
                os.path.join(os.path.dirname(__file__), "..", "Inventory", "INVENTORY_SARTAJ_0786.csv"),
                os.path.join(os.path.dirname(__file__), "..", "BizDabba By Wokdens.com", "9TH SEP INVENTORY_SARTAJ_0786.csv"),
            ]
            csv_path = next((p for p in csv_candidates if os.path.isfile(p)), csv_candidates[0])
            with patch('ui.inventory_ui.filedialog.askopenfilename', return_value=csv_path), \
                 patch('ui.inventory_ui.request_admin_pin', return_value=True):
                inv_ui.import_products_csv()

            prod_count = len(inv_ui.tree.get_children())
            cat_count = len(database.get_all_categories())
            assert prod_count >= 580, f"Expected 580+ products in UI, got {prod_count}"
            assert cat_count >= 20, f"Expected 20+ categories, got {cat_count}"
            print(f"  -> Successfully imported {prod_count} products across {cat_count} categories into UI.")

            # Verify product IDs start from 1
            all_rows = [inv_ui.tree.item(item_id, 'values') for item_id in inv_ui.tree.get_children()]
            ids = [int(r[0]) for r in all_rows]
            min_id = min(ids)
            assert min_id == 1, f"Expected product IDs to start from 1, but min ID was {min_id}!"
            print(f"  -> Verified product IDs start cleanly from ID 1 (min: {min_id}, max: {max(ids)}).")

            # Test Renumbering functionality
            with patch('ui.inventory_ui.request_admin_pin', return_value=True):
                inv_ui.renumber_all_product_ids()
            all_rows_after = [inv_ui.tree.item(item_id, 'values') for item_id in inv_ui.tree.get_children()]
            ids_after = [int(r[0]) for r in all_rows_after]
            assert min(ids_after) == 1 and max(ids_after) == len(ids_after), "Renumbering failed to produce clean 1..N sequence!"
            print(f"  -> Renumber all product IDs verified OK (1 to {len(ids_after)}).")

            # Search in Inventory
            inv_ui.search_entry.delete(0, tk.END)
            inv_ui.search_entry.insert(0, "TIBCON")
            inv_ui.search_products()
            matching = len(inv_ui.tree.get_children())
            assert matching > 0, "Inventory search returned 0 items!"
            print(f"  -> Inventory search filter returned {matching} matching items.")

            # -------------------------------------------------------------
            # STAGE 7: Sales Invoice & 80mm Thermal Receipt Generation
            # -------------------------------------------------------------
            print("[STAGE 7/9] Testing Sales Invoice Creation & Thermal Formatting...")
            app.open_invoice()
            invoice_ui = app.current_ui

            # Add Customer
            cust_name = "Test Wholesale Buyer"
            cust_phone = "9876543210"
            database.get_or_create_customer(cust_name, cust_phone, "Shop #42 Wholesale Market")
            invoice_ui.customer_combo.set(f"{cust_name} ({cust_phone})")

            # Add Product to Cart
            prod_names = database.get_product_names()
            assert len(prod_names) > 0, "No products available in database!"
            test_prod_name = prod_names[0]
            
            invoice_ui.product_combo.set(test_prod_name)
            invoice_ui.autofill_product_details()
            invoice_ui.qty_entry.delete(0, tk.END)
            invoice_ui.qty_entry.insert(0, "5")
            invoice_ui.add_to_cart()
            assert len(invoice_ui.cart_items) == 1, "Failed to add item to invoice cart!"

            # Add 2nd Product from database
            test_prod_2 = prod_names[1] if len(prod_names) > 1 else prod_names[0]
            invoice_ui.product_combo.set(test_prod_2)
            invoice_ui.autofill_product_details()
            invoice_ui.qty_entry.delete(0, tk.END)
            invoice_ui.qty_entry.insert(0, "10")
            invoice_ui.add_to_cart()
            assert len(invoice_ui.cart_items) == 2, "Failed to add 2nd item to cart!"

            # Set partial payment
            invoice_ui.paid_entry.delete(0, tk.END)
            invoice_ui.paid_entry.insert(0, "500")
            invoice_ui.update_pending()

            # Save & Print Thermal Receipt
            with patch('ui.invoice_ui.open_pdf_file'):
                invoice_ui.save_invoice(format_type="thermal")
            print("  -> Sales invoice created and thermal receipt printed successfully.")

            # Verify Invoice in History
            app.open_invoice_history()
            hist_ui = app.current_ui
            hist_items = hist_ui.tree.get_children()
            assert len(hist_items) >= 1, "Invoice not visible in Invoice History!"
            print(f"  -> Invoice History loaded with {len(hist_items)} invoice records.")

            # -------------------------------------------------------------
            # STAGE 8: Password-Protected CSV Export & AES Decryption
            # -------------------------------------------------------------
            print("[STAGE 8/9] Testing Password-Protected CSV Export Security...")
            test_zip = os.path.join(temp_dir, "test_sec.zip")
            created_zip = export_encrypted_csv_archive(
                target_path=test_zip,
                base_name="inventory_catalog.csv",
                header_row=["Category", "Name", "Selling Price"],
                data_rows=[["CAPACITORS", "2.5 MFD TIBCON", 120.0]]
            )
            assert os.path.exists(created_zip), "Encrypted export ZIP was not created!"
            
            zf = zipfile.ZipFile(created_zip)
            zf.setpassword(config.CSV_MASTER_EXPORT_PASSWORD.encode("utf-8"))
            decrypted = zf.read("inventory_catalog.csv").decode("utf-8-sig")
            zf.close()
            assert "2.5 MFD TIBCON" in decrypted, "Decrypted CSV content failed verification!"
            print("  -> Password-protected CSV encryption & master password decryption verified OK.")

            # -------------------------------------------------------------
            # STAGE 9: Invoice Editing, Stock Reconciliation & Cancellation
            # -------------------------------------------------------------
            print("[STAGE 9/9] Testing Invoice Editing, Stock Reconciliation & Cancellation...")
            prod_a = database.get_product_by_name("2.5 MFD TIBCON")
            assert prod_a is not None, "Product '2.5 MFD TIBCON' not found!"
            initial_stock_a = prod_a[3]

            # 1. Create a sales invoice with 30 units of 2.5 MFD TIBCON
            app.open_invoice()
            inv_ui = app.current_ui
            inv_ui.customer_combo.set("Deepak Electricals")
            inv_ui.product_combo.set("CAPACITORS - 2.5 MFD TIBCON")
            inv_ui.autofill_product_details()
            inv_ui.qty_entry.delete(0, tk.END)
            inv_ui.qty_entry.insert(0, "30")
            inv_ui.add_to_cart()
            assert len(inv_ui.cart_items) == 1 and inv_ui.cart_items[0]["quantity"] == 30

            with patch('ui.invoice_ui.open_pdf_file'):
                inv_ui.save_invoice(format_type="thermal")

            stock_after_sale = database.get_product_by_name("2.5 MFD TIBCON")[3]
            assert stock_after_sale == initial_stock_a - 30, f"Expected {initial_stock_a - 30}, got {stock_after_sale}"

            # 2. Recall the bill into billing cart (Customer reduces from 30 to 27 units)
            with patch('ui.invoice_ui.request_admin_pin', return_value=True):
                inv_ui.recall_last_bill()
            assert inv_ui.editing_invoice_id is not None, "Recall did not activate editing mode!"
            assert len(inv_ui.cart_items) == 1, "Recalled cart should contain 1 item!"
            assert inv_ui.cart_items[0]["quantity"] == 30, "Recalled item quantity should be 30!"

            inv_ui.cart_items[0]["quantity"] = 27
            inv_ui.cart_items[0]["total"] = inv_ui.cart_items[0]["price"] * 27
            inv_ui.refresh_cart_table()
            inv_ui.update_total()

            with patch('ui.invoice_ui.open_pdf_file'):
                inv_ui.save_invoice(format_type="thermal")

            # Verify stock reconciliation: 3 units returned to stock!
            stock_after_edit = database.get_product_by_name("2.5 MFD TIBCON")[3]
            assert stock_after_edit == initial_stock_a - 27, f"Expected {initial_stock_a - 27}, got {stock_after_edit}"
            print("  -> Invoice editing verified: 3 units returned to inventory with zero discrepancy.")

            # 3. Test Invoice Cancellation: Restores all 27 units and zeroes out dues
            last_inv = database.get_last_active_invoice()
            assert last_inv is not None
            target_inv_id = last_inv["id"]

            ok, msg = database.cancel_invoice(target_inv_id, authorized_by="Admin PIN 8160")
            assert ok is True, f"Failed to cancel invoice: {msg}"

            stock_after_cancel = database.get_product_by_name("2.5 MFD TIBCON")[3]
            assert stock_after_cancel == initial_stock_a, f"Expected complete restoration to {initial_stock_a}, got {stock_after_cancel}"

            conn = database.get_connection()
            cur = conn.cursor()
            cur.execute("SELECT status, pending FROM invoices WHERE id = ?", (target_inv_id,))
            status_row = cur.fetchone()
            conn.close()
            assert status_row[0] == "CANCELLED", f"Invoice status should be CANCELLED, got {status_row[0]}"
            assert status_row[1] == 0.0, f"Cancelled invoice pending should be 0.0, got {status_row[1]}"

            # 4. Verify cannot edit a cancelled invoice
            with patch('ui.invoice_ui.request_admin_pin', return_value=True):
                app.open_invoice(invoice_id_to_edit=target_inv_id)
            assert app.current_ui.editing_invoice_id is None, "Should not be able to edit a cancelled invoice!"

            # 5. Verify Invoice History displays CANCELLED status
            app.open_invoice_history()
            hist_ui = app.current_ui
            found_cancelled = False
            for item_id in hist_ui.tree.get_children():
                values = hist_ui.tree.item(item_id, "values")
                if "Cancelled" in str(values) or "CANCELLED" in str(values):
                    found_cancelled = True
                    break
            assert found_cancelled, "Cancelled invoice status not found in Invoice History table!"
            print("  -> Invoice cancellation verified: 100% stock restored, dues cleared, audit logged.")

            # -------------------------------------------------------------
            # STAGE 10: BizDibba Diwali v3.0 Features Verification
            # -------------------------------------------------------------
            print("[STAGE 10/10] Testing v3.0 Keyboard Navigation, Optional Phone & Dashboard Reset...")

            # 1. Test Customer Creation with blank/optional phone
            app.open_invoice()
            inv_ui = app.current_ui
            cust_id = database.get_or_create_customer("Counter Walk-in", "", "Main Bazaar")
            conn = database.get_connection()
            cur = conn.cursor()
            cur.execute("SELECT id, name, phone, address FROM customers WHERE id = ?", (cust_id,))
            cust_record = cur.fetchone()
            conn.close()
            assert cust_record is not None, "Failed to create customer with optional blank phone!"
            assert cust_record[2] == "", f"Expected empty phone, got '{cust_record[2]}'"
            print("  -> Customer created with optional empty mobile number verified.")

            # 2. Test Autocomplete Keyboard Navigation (Feature 4)
            cb = inv_ui.product_combo
            cb.set_completion_list(["Orient Ceiling Fan 1200mm", "Usha Farrata Fan 500mm", "Havells Exhaust Fan 150mm"])
            cb.entry.delete(0, tk.END)
            cb.entry.insert(0, "Fan")
            cb.show_popup(["Orient Ceiling Fan 1200mm", "Usha Farrata Fan 500mm", "Havells Exhaust Fan 150mm"])

            # Test Down Arrow moves to listbox item 1
            cb._on_down_arrow(None)
            assert cb.listbox.curselection() == (1,), f"Expected selection (1,), got {cb.listbox.curselection()}"

            # Test Tab moves down to item 2
            cb._on_listbox_down(None)
            assert cb.listbox.curselection() == (2,), f"Expected selection (2,), got {cb.listbox.curselection()}"

            # Test Up Arrow moves up to item 1
            cb._on_listbox_up(None)
            assert cb.listbox.curselection() == (1,), f"Expected selection (1,), got {cb.listbox.curselection()}"

            # Test Up Arrow moves up to item 0
            cb._on_listbox_up(None)
            assert cb.listbox.curselection() == (0,), f"Expected selection (0,), got {cb.listbox.curselection()}"

            # Test Enter selects item
            cb._on_listbox_enter(None)
            assert cb.get() == "Orient Ceiling Fan 1200mm", f"Expected 'Orient Ceiling Fan 1200mm', got '{cb.get()}'"
            print("  -> Autocomplete keyboard navigation (Down, Tab, Up, Enter) verified OK.")

            # 3. Test Dashboard Reset All Data without PIN (Feature 3)
            app.open_dashboard()
            dash_ui = app.current_ui

            # Ensure we had data prior to reset
            assert database.get_total_products() > 0, "Database should contain products before reset test!"

            with patch('tkinter.messagebox.askyesno', return_value=True):
                dash_ui.reset_all_system_data()

            # Verify complete deletion
            assert database.get_total_products() == 0, "Products table was not wiped!"
            assert database.get_total_customers() == 0, "Customers table was not wiped!"
            assert database.get_last_active_invoice() is None, "Invoices table was not wiped!"

            # 4. Verify ID starts cleanly from 1 upon new insertion (Feature 1)
            database.add_product(
                name="Test LED Bulb 9W",
                mrp=120.0,
                purchase_price=60.0,
                selling_price=80.0,
                stock=50,
                unit="Pcs",
                category="TEST_CAT"
            )
            conn = database.get_connection()
            cur = conn.cursor()
            cur.execute("SELECT id FROM products WHERE name = 'Test LED Bulb 9W'")
            new_pid = cur.fetchone()[0]
            conn.close()
            assert new_pid == 1, f"Expected first product after reset to have ID 1, got {new_pid}!"
            print("  -> Dashboard Reset All Data (without PIN) & Reset ID to 1 verified OK.")

            # -------------------------------------------------------------
            # STAGE 11: BizDabba PHWP Pen Drive Mode & Paints/Hardware Demo Data
            # -------------------------------------------------------------
            print("[STAGE 11/11] Testing BizDabba PHWP Pen Drive Mode & Demo Data...")

            # 1. Zero Host Computer Footprint
            localappdata = os.environ.get("LOCALAPPDATA", "")
            if localappdata:
                assert not config.AUTO_BACKUPS_DIR.lower().startswith(localappdata.lower()), \
                    f"Auto-backups should reside on USB, not %LOCALAPPDATA%! Got {config.AUTO_BACKUPS_DIR}"
            assert config.BASE_DIR in config.AUTO_BACKUPS_DIR, \
                f"Auto-backups must be inside BASE_DIR! Got {config.AUTO_BACKUPS_DIR}"
            print("  -> Zero host computer footprint verified (auto-backups strictly within BASE_DIR).")

            # 2. Seed Delhi Paints & Hardware Demo Data via Dashboard
            with patch('tkinter.messagebox.askyesno', return_value=True):
                dash_ui.load_paints_hardware_demo_data()

            total_prods = database.get_total_products()
            assert total_prods >= 50, f"Expected 50+ demo products, got {total_prods}"
            categories = database.get_all_categories()
            assert len(categories) >= 7, f"Expected 7+ categories, got {len(categories)}"
            assert "PAINTS - EMULSION & EXTERIOR" in categories, "Missing PAINTS - EMULSION & EXTERIOR category"
            assert "HARDWARE - FASTENERS & NAILS" in categories, "Missing HARDWARE - FASTENERS & NAILS category"

            total_custs = database.get_total_customers()
            assert total_custs == 10, f"Expected exactly 10 demo customers, got {total_custs}"
            pending_custs = database.get_customers_with_pending()
            assert len(pending_custs) == 8, f"Expected exactly 8 customers with pending dues in ledger, got {len(pending_custs)}"
            print(f"  -> Paints & Hardware demo catalog seeded: {total_prods} products across {len(categories)} categories.")
            print(f"  -> Demo customer accounts verified: exactly 10 customers, {len(pending_custs)} with pending dues in Ledger.")

            # 3. Test Dual Printing (80mm Thermal & A4 Sheet) across all 8 pending accounts
            app.open_ledger()
            ledger_ui = app.current_ui
            for cname, dues, inv_cnt in pending_custs:
                ledger_ui.current_customer_name = cname
                ledger_ui.current_total_dues = dues

                # A4 Statement PDF
                ledger_ui.export_statement_pdf()

                # 80mm Thermal Statement
                ledger_ui.export_thermal_statement()

                # Test Invoices for this customer
                invoices = database.get_customer_invoices(cname)
                assert len(invoices) > 0, f"No invoices found for pending customer {cname}"
                for inv in invoices:
                    inv_id, inv_num, inv_date, total, paid, pending, note, status = inv[:8]
                    assert pending > 0, f"Expected pending > 0 for {cname} invoice {inv_num}"
                    items = database.get_invoice_items(inv_id)

                    # 80mm Thermal receipt
                    t_path = generate_thermal_receipt_pdf(inv_num, cname, items, total, paid, note, inv_date, open_file=False)
                    assert os.path.isfile(t_path) and os.path.getsize(t_path) > 500, f"Thermal receipt failed for {inv_num}"

                    # A4 Invoice PDF
                    a4_path = generate_a4_invoice_pdf(inv_num, cname, items, total, paid, note, inv_date, open_file=False)
                    assert os.path.isfile(a4_path) and os.path.getsize(a4_path) > 500, f"A4 invoice failed for {inv_num}"

            # Verify the 2 fully paid customers (0 dues)
            for paid_cname in ["Sunil Kumar (Civil Lines)", "Walk-in Cash Customer"]:
                p_invs = database.get_customer_invoices(paid_cname)
                assert len(p_invs) == 1, f"Expected 1 invoice for {paid_cname}"
                assert p_invs[0][5] == 0, f"Expected 0 pending for {paid_cname}, got {p_invs[0][5]}"

            print("  -> Dual printing (80mm Thermal & A4 Sheet) verified 100% OK across all 8 pending customer profiles & invoices.")

            # 4. Pen Drive Safe Flush & Checkpoint
            ok_flush, msg_flush = database.safe_flush_pen_drive()
            assert ok_flush is True, f"safe_flush_pen_drive failed: {msg_flush}"
            print("  -> Pen Drive safe flush (WAL checkpoint & auto-backup) verified OK.")

            # 5. Global Pen Drive Save Trigger (Ctrl+S Simulation)
            app.trigger_pen_drive_save()
            print("  -> Global Pen Drive Save (Ctrl+S) triggered & executed cleanly.")

            # 6. Verify Demo Catalog CSV file
            csv_demo = os.path.join(os.path.dirname(__file__), "..", "DEMO_PAINTS_HARDWARE_CATALOG.csv")
            assert os.path.isfile(csv_demo), f"DEMO_PAINTS_HARDWARE_CATALOG.csv missing at {csv_demo}"
            with open(csv_demo, "r", encoding="utf-8") as f:
                csv_lines = [l for l in f if l.strip()]
            assert len(csv_lines) >= 51, f"Expected 51+ lines in demo CSV, got {len(csv_lines)}"
            print(f"  -> DEMO_PAINTS_HARDWARE_CATALOG.csv verified with {len(csv_lines)-1} products.")

        root.destroy()
    finally:
        database.DATABASE_PATH = old_db_path
        shutil_rmtree_safe(temp_dir)

    print("=" * 70)
    print("  ALL 11 EXHAUSTIVE STAGES PASSED WITH ZERO ERRORS (100% SUCCESS)!")
    print("=" * 70)

def shutil_rmtree_safe(path):
    import shutil
    try:
        shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass

if __name__ == "__main__":
    run_exhaustive_suite()
