import os
import shutil

import tkinter as tk

from tkinter import filedialog, messagebox

from datetime import datetime
import subprocess

from database import (
    get_total_products,
    get_total_customers,
    get_total_pending_amount,
    get_today_sales,
    get_low_stock_items,
    backup_database_to_file,
    restore_database_from_file,
    get_daily_sales_and_profit,
    get_shop_details,
    set_shop_details,
    get_audit_logs,
    record_audit_log,
    reset_application_data,
    safe_flush_pen_drive,
    seed_paints_and_hardware_demo_data
)



from config import DATABASE_PATH, BACKUPS_DIR, INVOICES_DIR
from ui.admin_auth_dialog import request_admin_pin, change_admin_pin_dialog



class DashboardUI:

    def __init__(self, parent, app=None):

        self.parent = parent
        self.app = app
        self.frame = tk.Frame(
            parent,
            bg="#f5f5f5"
        )

        self.frame.pack(
            fill="both",
            expand=True
        )

        # =========================
        # TITLE
        # =========================

        title = tk.Label(
            self.frame,
            text="Business Dashboard",
            font=("Arial", 22, "bold"),
            bg="#f5f5f5"
        )

        title.pack(pady=20)

        # =========================
        # TOP BUTTONS
        # =========================

        top_btn_frame = tk.Frame(
            self.frame,
            bg="#f5f5f5"
        )

        top_btn_frame.pack(pady=10)

        save_usb_btn = tk.Button(
            top_btn_frame,
            text="💾 Save & Flush USB",
            width=16,
            height=2,
            bg="#059669",
            fg="white",
            font=("Arial", 10, "bold"),
            command=self.save_and_flush_usb
        )

        save_usb_btn.pack(
            side="left",
            padx=4
        )

        backup_btn = tk.Button(
            top_btn_frame,
            text="Backup DB",
            width=11,
            height=2,
            bg="#4a90e2",
            fg="white",
            font=("Arial", 10, "bold"),
            command=self.backup_database
        )

        backup_btn.pack(
            side="left",
            padx=4
        )

        restore_btn = tk.Button(
            top_btn_frame,
            text="Restore DB",
            width=11,
            height=2,
            bg="#ff6666",
            fg="white",
            font=("Arial", 10, "bold"),
            command=self.restore_database
        )

        restore_btn.pack(
            side="left",
            padx=4
        )

        z_report_btn = tk.Button(
            top_btn_frame,
            text="📊 Daily Summary",
            width=15,
            height=2,
            bg="#28a745",
            fg="white",
            font=("Arial", 10, "bold"),
            command=self.show_daily_z_report
        )

        z_report_btn.pack(
            side="left",
            padx=4
        )

        demo_data_btn = tk.Button(
            top_btn_frame,
            text="🎨 Load Demo Data",
            width=15,
            height=2,
            bg="#6366f1",
            fg="white",
            font=("Arial", 10, "bold"),
            command=self.load_paints_hardware_demo_data
        )

        demo_data_btn.pack(
            side="left",
            padx=4
        )

        change_pin_btn = tk.Button(
            top_btn_frame,
            text="🔒 PIN",
            width=8,
            height=2,
            bg="#343a40",
            fg="white",
            font=("Arial", 10, "bold"),
            command=lambda: change_admin_pin_dialog(self.frame)
        )

        change_pin_btn.pack(
            side="left",
            padx=4
        )

        shop_details_btn = tk.Button(
            top_btn_frame,
            text="🏬 Shop Details",
            width=13,
            height=2,
            bg="#6c757d",
            fg="white",
            font=("Arial", 10, "bold"),
            command=self.edit_shop_details_dialog
        )

        shop_details_btn.pack(
            side="left",
            padx=4
        )

        audit_logs_btn = tk.Button(
            top_btn_frame,
            text="🛡️ Audit",
            width=8,
            height=2,
            bg="#007bff",
            fg="white",
            font=("Arial", 10, "bold"),
            command=self.show_security_audit_logs
        )

        audit_logs_btn.pack(
            side="left",
            padx=4
        )

        reset_btn = tk.Button(
            top_btn_frame,
            text="💣 Reset All Data",
            width=14,
            height=2,
            bg="#dc3545",
            fg="white",
            font=("Arial", 10, "bold"),
            command=self.reset_all_system_data
        )

        reset_btn.pack(
            side="left",
            padx=4
        )







        # =========================
        # LOW STOCK
        # =========================

        low_stock_frame = tk.LabelFrame(
            self.frame,
            text="Low Stock Items",
            font=("Arial", 12, "bold"),
            padx=10,
            pady=10
        )

        low_stock_frame.pack(
            fill="both",
            expand=True,
            padx=30,
            pady=20
        )

        low_stock_items = get_low_stock_items()

        if len(low_stock_items) == 0:

            tk.Label(
                low_stock_frame,
                text="No low stock items",
                font=("Arial", 11)
            ).pack(pady=10)

        else:

            for item in low_stock_items:

                product_name = item[0]

                stock = item[1]

                text = (
                    f"{product_name} → Stock: {stock}"
                )

                tk.Label(
                    low_stock_frame,
                    text=text,
                    font=("Arial", 11),
                    anchor="w"
                ).pack(
                    fill="x",
                    pady=5
                )

    # =========================
    # CARD CREATOR
    # =========================

    def create_card(
        self,
        parent,
        title,
        value,
        row,
        column
    ):

        card = tk.Frame(
            parent,
            bg="white",
            width=250,
            height=120,
            relief="solid",
            borderwidth=1
        )

        card.grid(
            row=row,
            column=column,
            padx=20,
            pady=20
        )

        card.grid_propagate(False)

        title_label = tk.Label(
            card,
            text=title,
            font=("Arial", 13, "bold"),
            bg="white"
        )

        title_label.pack(pady=15)

        value_label = tk.Label(
            card,
            text=value,
            font=("Arial", 20, "bold"),
            bg="white"
        )

        value_label.pack()

    # =========================
    # BACKUP DATABASE
    # =========================

    def backup_database(self):

        # Security: Require Admin PIN to create database backup
        if not request_admin_pin(self.frame, "create manual database backup"):
            return

        try:

            from datetime import datetime

            timestamp = datetime.now().strftime(
                "%Y%m%d_%H%M%S"
            )

            backup_file = os.path.join(
                BACKUPS_DIR,
                f"business_backup_{timestamp}.db"
            )

            backup_database_to_file(backup_file)

            record_audit_log("DB_BACKUP", f"Created manual database backup at {backup_file}")

            messagebox.showinfo(
                "Success",
                f"Backup created successfully:\n{backup_file}"
            )

        except Exception as e:

            messagebox.showerror(
                "Error",
                f"Backup failed: {str(e)}"
            )

    # =========================
    # EDIT SHOP DETAILS
    # =========================

    def edit_shop_details_dialog(self):
        """Allows editing business name, phone, and address printed on invoices and statements."""
        if not request_admin_pin(self.frame, "change shop business details"):
            return

        shop = get_shop_details()

        dialog = tk.Toplevel(self.frame)
        dialog.title("Edit Shop Details")
        dialog.geometry("520x330")
        dialog.resizable(False, False)
        dialog.transient(self.frame.winfo_toplevel())
        dialog.grab_set()

        # Center on screen
        dialog.update_idletasks()
        sw = dialog.winfo_screenwidth()
        sh = dialog.winfo_screenheight()
        w, h = 520, 330
        x = (sw - w) // 2
        y = (sh - h) // 2
        dialog.geometry(f"{w}x{h}+{x}+{y}")

        header = tk.Frame(dialog, bg="#1e222d", pady=10)
        header.pack(fill="x")
        tk.Label(
            header,
            text="🏬 Shop Business Details",
            font=("Arial", 13, "bold"),
            bg="#1e222d",
            fg="white"
        ).pack()

        form = tk.Frame(dialog, padx=25, pady=15)
        form.pack(fill="both", expand=True)

        tk.Label(form, text="Shop Name:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w", pady=6)
        name_entry = tk.Entry(form, font=("Arial", 11), width=32)
        name_entry.grid(row=0, column=1, pady=6, padx=10)
        name_entry.insert(0, shop["name"])
        name_entry.focus_set()

        tk.Label(form, text="Phone Number:", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky="w", pady=6)
        phone_entry = tk.Entry(form, font=("Arial", 11), width=32)
        phone_entry.grid(row=1, column=1, pady=6, padx=10)
        phone_entry.insert(0, shop["phone"])

        tk.Label(form, text="Address / GSTIN:", font=("Arial", 10, "bold")).grid(row=2, column=0, sticky="nw", pady=6)
        address_entry = tk.Text(form, font=("Arial", 10), width=32, height=3)
        address_entry.grid(row=2, column=1, pady=6, padx=10)
        address_entry.insert("1.0", shop["address"])

        def on_save():
            new_name = name_entry.get().strip()
            new_phone = phone_entry.get().strip()
            new_address = address_entry.get("1.0", tk.END).strip()

            if not new_name:
                messagebox.showwarning("Missing Name", "Please enter Shop Name.", parent=dialog)
                name_entry.focus_set()
                return

            set_shop_details(new_name, new_phone, new_address)
            record_audit_log("SHOP_DETAILS_UPDATE", f"Updated shop details: Name='{new_name}', Phone='{new_phone}', Address='{new_address}'")
            messagebox.showinfo("Saved", "Shop details updated successfully!", parent=dialog)
            dialog.destroy()

        btn_bar = tk.Frame(dialog, pady=10)
        btn_bar.pack(fill="x", padx=25)

        tk.Button(
            btn_bar,
            text="Save Details",
            command=on_save,
            bg="#28a745",
            fg="white",
            font=("Arial", 10, "bold"),
            width=14
        ).pack(side="left", padx=10)

        tk.Button(
            btn_bar,
            text="Cancel",
            command=dialog.destroy,
            bg="#6c757d",
            fg="white",
            font=("Arial", 10, "bold"),
            width=10
        ).pack(side="right", padx=10)

        tk.Label(
            dialog,
            text="⚡ Powered by wokdens.com",
            font=("Arial", 8, "italic"),
            fg="#888888"
        ).pack(side="bottom", pady=4)



    # =========================
    # SECURITY AUDIT LOGS MODAL
    # =========================

    def show_security_audit_logs(self):
        """Displays timestamped security audit log of all PIN-authorized operations."""
        if not request_admin_pin(self.frame, "view security audit logs"):
            return

        logs = get_audit_logs(limit=200)

        dialog = tk.Toplevel(self.frame)
        dialog.title("Security Audit Logs")
        dialog.geometry("920x520")
        dialog.transient(self.frame.winfo_toplevel())
        dialog.grab_set()

        # Center on screen
        dialog.update_idletasks()
        sw = dialog.winfo_screenwidth()
        sh = dialog.winfo_screenheight()
        w, h = 920, 520
        x = (sw - w) // 2
        y = (sh - h) // 2
        dialog.geometry(f"{w}x{h}+{x}+{y}")

        header = tk.Frame(dialog, bg="#1e222d", pady=12)
        header.pack(fill="x")
        tk.Label(
            header,
            text="🛡️ Security Audit Logs & Price Override Trail",
            font=("Arial", 14, "bold"),
            bg="#1e222d",
            fg="white"
        ).pack(side="left", padx=20)

        def export_audit_csv():
            from ui.csv_security import export_encrypted_csv_archive

            file_path = filedialog.asksaveasfilename(
                title="Export Password-Protected Audit Logs",
                defaultextension=".zip",
                filetypes=[("Password-Protected ZIP Archive (*.zip)", "*.zip"), ("CSV Files (*.csv)", "*.csv")],
                initialfile="security_audit_logs.zip",
                parent=dialog
            )
            if not file_path:
                return
            try:
                headers = ["Log ID", "Timestamp", "Action Type", "Event Description", "Authorized By"]
                saved_zip = export_encrypted_csv_archive(
                    target_path=file_path,
                    base_name="security_audit_logs.csv",
                    header_row=headers,
                    data_rows=logs
                )
                record_audit_log("CSV_EXPORT", f"Exported password-protected security audit logs to {saved_zip}")
                messagebox.showinfo(
                    "Export Successful (Password Protected)",
                    f"Audit logs exported successfully!\n\n"
                    f"📁 Saved to:\n{saved_zip}\n\n"
                    f"🔒 Password Protected: Enter your Master Export Password when extracting.",
                    parent=dialog
                )
            except Exception as e:
                messagebox.showerror("Export Error", str(e), parent=dialog)

        tk.Button(
            header,
            text="📥 Export Logs (CSV)",
            command=export_audit_csv,
            bg="#28a745",
            fg="white",
            font=("Arial", 9, "bold"),
            padx=10,
            pady=3
        ).pack(side="right", padx=15)

        # Treeview
        tree_frame = tk.Frame(dialog, padx=15, pady=10)
        tree_frame.pack(fill="both", expand=True)

        columns = ("ID", "Timestamp", "Action Type", "Description", "Authorized By")
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings")

        tree.heading("ID", text="ID", anchor="center")
        tree.heading("Timestamp", text="Timestamp", anchor="w")
        tree.heading("Action Type", text="Action Type", anchor="w")
        tree.heading("Description", text="Description / Details", anchor="w")
        tree.heading("Authorized By", text="Authorized By", anchor="center")

        tree.column("ID", width=50, anchor="center")
        tree.column("Timestamp", width=170, anchor="w")
        tree.column("Action Type", width=150, anchor="w")
        tree.column("Description", width=420, anchor="w")
        tree.column("Authorized By", width=110, anchor="center")

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        for log in logs:
            tree.insert("", "end", values=log)

        footer = tk.Label(
            dialog,
            text="⚡ Powered by wokdens.com",
            font=("Arial", 8, "italic"),
            fg="#888888"
        )
        footer.pack(side="bottom", pady=4)




    # =========================
    # RESTORE DATABASE
    # =========================

    def restore_database(self):

        # Security: Require Admin PIN to restore database
        if not request_admin_pin(self.frame, "restore database from backup"):
            return

        try:

            backup_file = filedialog.askopenfilename(
                title="Select Backup File",
                initialdir=BACKUPS_DIR,
                filetypes=[
                    ("Database Files", "*.db")
                ]
            )

            if not backup_file:
                return

            confirm = messagebox.askyesno(
                "Confirm Restore",
                "Current database will be replaced with the selected backup.\nContinue?"
            )

            if not confirm:
                return

            restore_database_from_file(backup_file)

            record_audit_log("DB_RESTORE", f"Restored database from backup file {backup_file}")

            messagebox.showinfo(
                "Success",
                "Database restored successfully.\nPlease restart the application to reload all views."
            )


        except Exception as e:

            messagebox.showerror(
                "Error",
                f"Restore failed: {str(e)}"
            )

    # =========================
    # RESET ALL SYSTEM DATA (EMPTY)
    # =========================

    def reset_all_system_data(self):
        """Delete all invoices, customer details, and inventory without requiring a PIN.
        Asks for confirmation once.
        """
        confirm = messagebox.askyesno(
            "Confirm System Reset",
            "Are you sure you want to delete ALL invoices, customer details, and inventory?\n\n"
            "• All invoices and sales history will be permanently deleted.\n"
            "• All customers and balances will be removed.\n"
            "• All products and inventory will be cleared.\n"
            "• Product and invoice IDs will restart from 1.\n\n"
            "This will completely empty the system. Do you want to proceed?",
            parent=self.frame
        )

        if not confirm:
            return

        try:
            reset_application_data()
            try:
                record_audit_log("RESET_ALL_DATA", "All invoices, customers, and inventory data deleted by user.")
            except Exception:
                pass

            messagebox.showinfo(
                "System Reset Complete",
                "All invoices, customer details, and inventory have been deleted successfully.\n\n"
                "The system is now completely empty and ID counters have been reset to 1.",
                parent=self.frame
            )

            parent = self.parent
            app = self.app
            self.frame.destroy()
            self.__init__(parent, app)

        except Exception as e:
            messagebox.showerror(
                "Reset Failed",
                f"An error occurred while resetting application data:\n{str(e)}",
                parent=self.frame
            )

    # =========================
    # SAFE SAVE & FLUSH USB
    # =========================

    def save_and_flush_usb(self):
        """Flushes database WAL to pen drive storage and confirms with 3-second toast."""
        if self.app and hasattr(self.app, "trigger_pen_drive_save"):
            self.app.trigger_pen_drive_save()
        else:
            ok, msg = safe_flush_pen_drive()
            now_str = datetime.now().strftime("%I:%M:%S %p")
            if ok:
                try:
                    record_audit_log("USB_SAVE", f"Database flushed to USB flash storage at {now_str}")
                except Exception:
                    pass
                messagebox.showinfo(
                    "💾 Saved to Pen Drive",
                    f"All data has been safely flushed and committed to Pen Drive storage!\n\n"
                    f"Time: {now_str}\nStatus: Safe to unplug or power down.",
                    parent=self.frame
                )
            else:
                messagebox.showerror(
                    "Save Failed",
                    f"Could not safely flush data to USB:\n{msg}",
                    parent=self.frame
                )

    # =========================
    # LOAD PAINTS & HARDWARE DEMO DATA
    # =========================

    def load_paints_hardware_demo_data(self):
        """Seeds 50+ Paints & Hardware items, Delhi customer accounts, and sample invoices."""
        confirm = messagebox.askyesno(
            "Load Paints & Hardware Demo Data?",
            "Do you want to load the pre-seeded Delhi Paints & Hardware catalog and ledger data?\n\n"
            "This will add:\n"
            "• 50+ products across 8 categories (Asian Paints, Berger, Enamel, Thinners, Putty, Locks, CPVC fittings, etc.)\n"
            "• 10 Delhi contractor & painter customer profiles\n"
            "• 11 Realistic sales invoices (8 with pending balances in Ledger)\n\n"
            "Existing unique records will be preserved. Proceed?",
            parent=self.frame
        )
        if not confirm:
            return

        ok, msg = seed_paints_and_hardware_demo_data(force=True)
        if ok:
            safe_flush_pen_drive()
            try:
                record_audit_log("LOAD_DEMO_DATA", "Loaded Delhi Paints & Hardware try-before-you-buy demo catalog.")
            except Exception:
                pass

            messagebox.showinfo(
                "Demo Data Loaded",
                f"Paints & Hardware demo catalog loaded successfully!\n\n{msg}\n\n"
                "The dashboard will now refresh.",
                parent=self.frame
            )
            # Refresh dashboard
            parent = self.parent
            app = self.app
            self.frame.destroy()
            self.__init__(parent, app)
        else:
            messagebox.showerror(
                "Demo Data Error",
                f"Failed to seed demo data:\n{msg}",
                parent=self.frame
            )


    # ========================================
    # DAILY SALES & PROFIT SUMMARY (Z-REPORT)
    # ========================================

    def show_daily_z_report(self):
        """Displays the Day-End Z-Report summary modal and provides PDF export."""
        # Security: Require Admin PIN for viewing business profit report
        if not request_admin_pin(self.frame, "view Daily Sales & Profit Summary (Z-Report)"):
            return

        report_data = get_daily_sales_and_profit()

        dialog = tk.Toplevel(self.frame)
        dialog.title("Day-End Z-Report (Sales & Profit Summary)")
        dialog.geometry("850x620")
        dialog.transient(self.frame.winfo_toplevel())
        dialog.grab_set()

        # Center on screen
        dialog.update_idletasks()
        sw = dialog.winfo_screenwidth()
        sh = dialog.winfo_screenheight()
        w, h = 850, 620
        x = (sw - w) // 2
        y = (sh - h) // 2
        dialog.geometry(f"{w}x{h}+{x}+{y}")

        # Title / Header
        header_frame = tk.Frame(dialog, bg="#1e222d", pady=12)
        header_frame.pack(fill="x")

        tk.Label(
            header_frame,
            text=f"📊 Day-End Z-Report — {report_data['date']}",
            font=("Arial", 16, "bold"),
            bg="#1e222d",
            fg="white"
        ).pack()

        # Metric Badges Frame
        metrics_frame = tk.Frame(dialog, padx=15, pady=10, bg="#f8f9fa")
        metrics_frame.pack(fill="x", padx=15, pady=10)

        metrics = [
            ("Total Invoices", str(report_data["invoice_count"]), "#4a90e2"),
            ("Total Sales", f"₹ {report_data['total_sales']:.2f}", "#28a745"),
            ("Cash Collected", f"₹ {report_data['total_cash_collected']:.2f}", "#17a2b8"),
            ("Credit Given", f"₹ {report_data['total_credit_extended']:.2f}", "#fd7e14"),
            ("Est. Gross Profit", f"₹ {report_data['gross_profit']:.2f}", "#6f42c1")
        ]

        for i, (m_title, m_val, color) in enumerate(metrics):
            card = tk.Frame(metrics_frame, bg="white", relief="solid", borderwidth=1, padx=10, pady=8)
            card.grid(row=0, column=i, padx=5, sticky="nsew")
            metrics_frame.grid_columnconfigure(i, weight=1)

            tk.Label(card, text=m_title, font=("Arial", 9, "bold"), fg="#666666", bg="white").pack()
            tk.Label(card, text=m_val, font=("Arial", 12, "bold"), fg=color, bg="white").pack(pady=(4, 0))

        # Items Table Label
        tk.Label(
            dialog,
            text="Products Sold Today & Profit Breakdown",
            font=("Arial", 12, "bold"),
            anchor="w"
        ).pack(fill="x", padx=20, pady=(5, 5))

        # Items Table
        table_frame = tk.Frame(dialog, padx=15)
        table_frame.pack(fill="both", expand=True)

        cols = ("Product", "Qty Sold", "Sales Revenue", "Purchase Cost", "Gross Profit")
        tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=10)

        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, anchor="center")
        tree.column("Product", anchor="w", width=220)

        for row in report_data["items_sold"]:
            p_name, qty, rev, cost, profit = row
            tree.insert("", "end", values=(
                p_name,
                int(qty),
                f"₹ {float(rev):.2f}",
                f"₹ {float(cost):.2f}",
                f"₹ {float(profit):.2f}"
            ))

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Bottom Button Bar
        btn_bar = tk.Frame(dialog, pady=10)
        btn_bar.pack(fill="x", padx=20)

        def export_z_report_pdf():
            try:
                from reportlab.lib.pagesizes import letter
                from reportlab.pdfgen import canvas
                from config import SHOP_NAME, SHOP_ADDRESS, SHOP_PHONE

                today_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                pdf_path = os.path.join(INVOICES_DIR, f"Z_Report_{today_str}.pdf")

                pdf = canvas.Canvas(pdf_path, pagesize=letter)
                width, height = letter

                # Title
                pdf.setFont("Helvetica-Bold", 18)
                pdf.setFillColorRGB(0.12, 0.14, 0.18)
                pdf.drawString(40, height - 50, "DAY-END Z-REPORT (DAILY SUMMARY)")

                pdf.setFont("Helvetica", 9)
                pdf.setFillColorRGB(0.35, 0.35, 0.35)
                pdf.drawString(40, height - 68, f"Date: {report_data['date']} | Generated: {datetime.now().strftime('%I:%M %p')}")

                # Shop info
                pdf.setFont("Helvetica-Bold", 12)
                pdf.setFillColorRGB(0.1, 0.1, 0.1)
                pdf.drawRightString(width - 40, height - 50, str(SHOP_NAME))
                pdf.setFont("Helvetica", 9)
                pdf.setFillColorRGB(0.4, 0.4, 0.4)
                pdf.drawRightString(width - 40, height - 65, str(SHOP_ADDRESS))
                pdf.drawRightString(width - 40, height - 78, f"Phone: {SHOP_PHONE}")

                pdf.setStrokeColorRGB(0.8, 0.8, 0.8)
                pdf.line(40, height - 90, width - 40, height - 90)

                # Key Metrics Summary Box
                pdf.setFillColorRGB(0.95, 0.96, 0.98)
                pdf.roundRect(40, height - 170, width - 80, 70, 4, fill=1, stroke=0)

                pdf.setFont("Helvetica-Bold", 10)
                pdf.setFillColorRGB(0.2, 0.2, 0.2)
                pdf.drawString(55, height - 115, f"Total Invoices: {report_data['invoice_count']}")
                pdf.drawString(55, height - 135, f"Total Sales: Rs. {report_data['total_sales']:.2f}")

                pdf.drawString(240, height - 115, f"Cash Collected: Rs. {report_data['total_cash_collected']:.2f}")
                pdf.drawString(240, height - 135, f"Credit Given: Rs. {report_data['total_credit_extended']:.2f}")

                pdf.setFont("Helvetica-Bold", 11)
                pdf.setFillColorRGB(0.15, 0.55, 0.2)
                pdf.drawString(width - 240, height - 125, f"Gross Profit: Rs. {report_data['gross_profit']:.2f}")

                # Table Header
                table_top = height - 195
                pdf.setFillColorRGB(0.12, 0.14, 0.18)
                pdf.rect(40, table_top - 18, width - 80, 20, fill=1, stroke=0)

                pdf.setFont("Helvetica-Bold", 9)
                pdf.setFillColorRGB(1, 1, 1)
                pdf.drawString(50, table_top - 14, "Product Name")
                pdf.drawRightString(260, table_top - 14, "Qty Sold")
                pdf.drawRightString(350, table_top - 14, "Revenue")
                pdf.drawRightString(440, table_top - 14, "Cost")
                pdf.drawRightString(width - 50, table_top - 14, "Gross Profit")

                # Table Rows
                y = table_top - 36
                for i, r in enumerate(report_data["items_sold"]):
                    if y < 70:
                        pdf.showPage()
                        y = height - 60

                    if i % 2 == 1:
                        pdf.setFillColorRGB(0.97, 0.97, 0.97)
                        pdf.rect(40, y - 4, width - 80, 16, fill=1, stroke=0)

                    p_name, qty, rev, cost, profit = r
                    pdf.setFont("Helvetica", 9)
                    pdf.setFillColorRGB(0.2, 0.2, 0.2)
                    pdf.drawString(50, y, str(p_name)[:30])
                    pdf.drawRightString(260, y, str(int(qty)))
                    pdf.drawRightString(350, y, f"Rs. {float(rev):.2f}")
                    pdf.drawRightString(440, y, f"Rs. {float(cost):.2f}")
                    pdf.drawRightString(width - 50, y, f"Rs. {float(profit):.2f}")
                    y -= 18

                # Footer
                pdf.setStrokeColorRGB(0.8, 0.8, 0.8)
                pdf.line(40, 45, width - 40, 45)
                pdf.setFont("Helvetica-Bold", 8)
                pdf.setFillColorRGB(0.5, 0.5, 0.5)
                pdf.drawString(40, 32, "Confidential - Business Management Daily Audit")
                pdf.drawRightString(width - 40, 32, "⚡ Powered by wokdens.com")

                pdf.save()

                if os.name == "nt":
                    os.startfile(os.path.abspath(pdf_path))
                else:
                    subprocess.Popen(["xdg-open", os.path.abspath(pdf_path)])

                messagebox.showinfo("Report Exported", f"Daily Z-Report PDF saved to:\n{pdf_path}", parent=dialog)
            except Exception as ex:
                messagebox.showerror("Export Error", str(ex), parent=dialog)

        tk.Button(
            btn_bar,
            text="📄 Export Z-Report PDF",
            command=export_z_report_pdf,
            bg="#28a745",
            fg="white",
            font=("Arial", 11, "bold"),
            padx=12,
            pady=4
        ).pack(side="left")

        tk.Button(
            btn_bar,
            text="Close",
            command=dialog.destroy,
            bg="#6c757d",
            fg="white",
            font=("Arial", 11, "bold"),
            padx=12,
            pady=4
        ).pack(side="right")

        # Footer Branding
        tk.Label(
            dialog,
            text="⚡ Powered by wokdens.com",
            font=("Arial", 8, "italic"),
            fg="#888888"
        ).pack(side="bottom", pady=4)