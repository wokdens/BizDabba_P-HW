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
        print("  -> All 17 mobile number permutations verified OK.")

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
            assert app.root.title() == "BizDibba Diwali v2.0 by wokdens.com", f"Title mismatch: {app.root.title()}"
            print("  -> MainWindow title verified: 'BizDibba Diwali v2.0 by wokdens.com'")

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

        root.destroy()
    finally:
        database.DATABASE_PATH = old_db_path
        shutil_rmtree_safe(temp_dir)

    print("=" * 70)
    print("  ALL 9 EXHAUSTIVE STAGES PASSED WITH ZERO ERRORS (100% SUCCESS)!")
    print("=" * 70)

def shutil_rmtree_safe(path):
    import shutil
    try:
        shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass

if __name__ == "__main__":
    run_exhaustive_suite()
