import tkinter as tk
from tkinter import ttk, messagebox
import os
import subprocess
from datetime import datetime
from database import (
    get_customers_with_pending,
    get_customer_invoices,
    get_invoice_details_by_id,
    get_invoice_items,
    update_invoice_payment,
    get_total_pending,
    update_invoice_note,
    get_customer_statement_data,
    record_audit_log
)

from config import INVOICES_DIR
from ui.admin_auth_dialog import request_admin_pin




class LedgerUI:

    def __init__(self, parent):

        self.parent = parent
        self.frame = tk.Frame(parent)
        self.frame.pack(fill="both", expand=True)
        
        self.current_view = "customers"  # Track current view
        self.selected_customer = None
        self.selected_invoice = None

        # Show customer list initially
        self.show_customer_list()

    # =========================
    # CUSTOMER LIST VIEW
    # =========================

    def show_customer_list(self):
        """Display customers with pending amounts"""
        
        # Clear frame
        for widget in self.frame.winfo_children():
            widget.destroy()

        # =========================
        # TITLE
        # =========================

        title = tk.Label(
            self.frame,
            text="Customer Ledger - Pending Amounts",
            font=("Arial", 18, "bold")
        )

        title.pack(pady=10)

        # =========================
        # SEARCH
        # =========================

        search_frame = tk.Frame(self.frame)
        search_frame.pack(fill="x", padx=20, pady=10)

        tk.Label(
            search_frame,
            text="Search Customer:",
            font=("Arial", 11, "bold")
        ).pack(side="left")

        self.search_entry = tk.Entry(
            search_frame,
            width=30,
            font=("Arial", 11)
        )

        self.search_entry.pack(side="left", padx=10)
        self.search_entry.bind("<KeyRelease>", self.search_customers)
        self.search_entry.bind("<Down>", self._focus_first_customer_row)
        self.search_entry.bind("<Return>", self._focus_first_customer_row)
        self.search_entry.bind("<FocusIn>", lambda e: self.search_entry.selection_range(0, tk.END))

        open_ledger_btn = tk.Button(
            search_frame,
            text="📂 View Invoices (Enter)",
            command=self.on_customer_select,
            bg="#0066cc",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=10,
            pady=3
        )
        open_ledger_btn.pack(side="right", padx=5)

        export_ledger_btn = tk.Button(
            search_frame,
            text="📊 Export Ledger CSV",
            command=self.export_ledger_csv,
            bg="#28a745",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=10,
            pady=3
        )
        export_ledger_btn.pack(side="right", padx=5)


        # =========================
        # TABLE
        # =========================

        columns = ("S.No", "Customer Name", "Total Pending", "Invoices Count")

        table_frame = tk.Frame(
            self.frame,
            relief="solid",
            bd=1,
            highlightthickness=1,
            highlightbackground="#ced4da"
        )
        table_frame.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=(0, 20)
        )

        self.customer_tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse"
        )

        scroll_y = ttk.Scrollbar(
            table_frame,
            orient="vertical",
            command=self.customer_tree.yview
        )
        self.customer_tree.configure(yscrollcommand=scroll_y.set)

        for col in columns:
            self.customer_tree.heading(
                col,
                text=col,
                anchor="center" if col in ("S.No", "Total Pending", "Invoices Count") else "w"
            )
            if col == "S.No":
                width = 45
            elif col == "Customer Name":
                width = 320
            else:
                width = 160
            self.customer_tree.column(
                col,
                width=width,
                minwidth=35 if col == "S.No" else 50,
                stretch=(col == "Customer Name"),
                anchor="center" if col in ("S.No", "Total Pending", "Invoices Count") else "w"
            )


        self.customer_tree.pack(side="left", fill="both", expand=True)
        scroll_y.pack(side="right", fill="y")

        self.customer_tree.tag_configure("evenrow", background="#ffffff")
        self.customer_tree.tag_configure("oddrow", background="#f8f9fa")

        self.customer_tree.bind("<Double-1>", self.on_customer_select)
        self.customer_tree.bind("<Return>", self.on_customer_select)
        self.customer_tree.bind("<ButtonRelease-1>", self.on_customer_select)

        # Load data
        self.all_customers = []
        self.load_customers()

    def _focus_first_customer_row(self, event=None):
        """Move focus from search bar to first customer in table."""
        children = self.customer_tree.get_children()
        if children:
            self.customer_tree.selection_set(children[0])
            self.customer_tree.focus(children[0])
            self.customer_tree.focus_set()
        return "break"

    def load_customers(self):
        """Load customers with pending amounts"""
        self.customer_tree.delete(*self.customer_tree.get_children())
        self.all_customers = get_customers_with_pending()

        for idx, row in enumerate(self.all_customers):
            values = (str(idx + 1), row[0], f"₹ {row[1]}", row[2])
            tag = "evenrow" if idx % 2 == 0 else "oddrow"
            self.customer_tree.insert("", "end", values=values, tags=(tag,))

    def search_customers(self, event):
        """Search customers by name"""
        keyword = self.search_entry.get().lower()
        self.customer_tree.delete(*self.customer_tree.get_children())

        match_count = 0
        for row in self.all_customers:
            if keyword in row[0].lower():
                values = (str(match_count + 1), row[0], f"₹ {row[1]}", row[2])
                tag = "evenrow" if match_count % 2 == 0 else "oddrow"
                self.customer_tree.insert("", "end", values=values, tags=(tag,))
                match_count += 1

    def on_customer_select(self, event=None):
        """Handle customer selection on click, double-click, or Enter key"""
        if event and hasattr(event, "y") and hasattr(event, "x") and event.x is not None and event.y is not None:
            try:
                region = self.customer_tree.identify("region", event.x, event.y)
                if region in ("cell", "tree"):
                    row_id = self.customer_tree.identify_row(event.y)
                    if row_id:
                        self.customer_tree.selection_set(row_id)
            except Exception:
                pass

        selected = self.customer_tree.selection()
        if not selected:
            children = self.customer_tree.get_children()
            if children:
                self.customer_tree.selection_set(children[0])
                selected = (children[0],)
            else:
                return

        item_data = self.customer_tree.item(selected[0])
        values = item_data.get("values", [])
        if not values or len(values) < 2:
            return

        customer_name = str(values[1])
        self.selected_customer = customer_name
        self.show_invoice_list(customer_name)




    def export_ledger_csv(self):
        """Exports the customer dues ledger to CSV (Admin PIN Protected)."""
        if not request_admin_pin(self.frame, "export customer ledger data to CSV"):
            return

        from tkinter import filedialog
        from ui.csv_security import export_encrypted_csv_archive

        file_path = filedialog.asksaveasfilename(
            title="Export Password-Protected Customer Ledger",
            defaultextension=".zip",
            filetypes=[("Password-Protected ZIP Archive (*.zip)", "*.zip"), ("CSV File (*.csv)", "*.csv")],
            initialfile="customer_ledger.zip"
        )

        if not file_path:
            return

        try:
            customers = get_customers_with_pending()
            headers = ["Customer Name", "Total Pending Dues (Rs)", "Invoices Count"]
            data_rows = [[row[0], row[1], row[2]] for row in customers]

            saved_zip = export_encrypted_csv_archive(
                target_path=file_path,
                base_name="customer_ledger.csv",
                header_row=headers,
                data_rows=data_rows
            )

            record_audit_log("CSV_EXPORT", f"Exported password-protected customer ledger dues ({len(customers)} customers) to {saved_zip}")

            messagebox.showinfo(
                "Export Successful (Password Protected)",
                f"Customer ledger exported successfully!\n\n"
                f"📁 Saved to:\n{saved_zip}\n\n"
                f"🔒 Password Protected: Enter your Master Export Password when extracting."
            )
        except Exception as e:
            messagebox.showerror("Export Error", str(e))


    # =========================
    # INVOICE LIST VIEW
    # =========================

    def show_invoice_list(self, customer_name):
        """Display invoices for selected customer"""
        
        # Clear frame
        for widget in self.frame.winfo_children():
            widget.destroy()

        # Header Frame
        header_frame = tk.Frame(self.frame)
        header_frame.pack(fill="x", padx=20, pady=10)

        # Back Button
        back_btn = tk.Button(
            header_frame,
            text="← Back to Customers",
            command=self.show_customer_list,
            bg="#f0f0f0",
            font=("Arial", 10, "bold"),
            padx=10,
            pady=5
        )
        back_btn.pack(side="left")

        # Customer Info
        info_frame = tk.Frame(header_frame)
        info_frame.pack(side="left", padx=20)

        name_label = tk.Label(
            info_frame,
            text=f"Customer: {customer_name}",
            font=("Arial", 13, "bold"),
            fg="#333333"
        )
        name_label.pack(anchor="w")

        # Calculate Total Pending for this customer
        invoices = get_customer_invoices(customer_name)
        total_dues = sum(inv[5] for inv in invoices)

        dues_label = tk.Label(
            info_frame,
            text=f"Total Dues: ₹ {total_dues}",
            font=("Arial", 12, "bold"),
            fg="#d9534f" if total_dues > 0 else "#5cb85c"
        )
        dues_label.pack(anchor="w")

        # Action Buttons on Right
        action_btn_frame = tk.Frame(header_frame)
        action_btn_frame.pack(side="right")

        # Export Thermal Statement Button (80mm Helix 1)
        thermal_stmt_btn = tk.Button(
            action_btn_frame,
            text="🖨️ Thermal Statement",
            command=self.export_thermal_statement,
            bg="#5634f0",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=12,
            pady=5
        )
        thermal_stmt_btn.pack(side="left", padx=5)

        # Export Statement PDF Button (A4 Sheet)
        statement_btn = tk.Button(
            action_btn_frame,
            text="📄 Statement PDF (A4)",
            command=self.export_statement_pdf,
            bg="#17a2b8",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=12,
            pady=5
        )
        statement_btn.pack(side="left", padx=5)

        # Pay All Bills Button
        pay_all_btn = tk.Button(
            action_btn_frame,
            text="💰 Pay All Bills",
            command=self.pay_all_pending_bills,
            bg="#28a745",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=12,
            pady=5
        )
        pay_all_btn.pack(side="left", padx=5)

        # Search / Filter by Date
        filter_frame = tk.Frame(self.frame)
        filter_frame.pack(fill="x", padx=20, pady=5)

        tk.Label(
            filter_frame,
            text="Filter Invoices:",
            font=("Arial", 10, "bold")
        ).pack(side="left")

        self.invoice_search_entry = tk.Entry(
            filter_frame,
            width=25,
            font=("Arial", 10)
        )
        self.invoice_search_entry.pack(side="left", padx=10)
        self.invoice_search_entry.bind("<KeyRelease>", self.filter_invoices)
        self.invoice_search_entry.bind("<Down>", self._focus_first_invoice_row)
        self.invoice_search_entry.bind("<Return>", self._focus_first_invoice_row)
        self.invoice_search_entry.bind("<Escape>", lambda e: self.show_customer_list())
        self.invoice_search_entry.bind("<FocusIn>", lambda e: self.invoice_search_entry.selection_range(0, tk.END))

        # Status filter buttons
        self.status_filter_var = tk.StringVar(value="All")

        all_radio = tk.Radiobutton(
            filter_frame,
            text="All",
            variable=self.status_filter_var,
            value="All",
            command=self.filter_invoices
        )
        all_radio.pack(side="left", padx=5)

        pending_radio = tk.Radiobutton(
            filter_frame,
            text="Pending Only",
            variable=self.status_filter_var,
            value="Pending",
            command=self.filter_invoices
        )
        pending_radio.pack(side="left", padx=5)

        paid_radio = tk.Radiobutton(
            filter_frame,
            text="Paid Only",
            variable=self.status_filter_var,
            value="Paid",
            command=self.filter_invoices
        )
        paid_radio.pack(side="left", padx=5)

        # Invoices Table
        columns = ("S.No", "Invoice Number", "Date", "Total", "Paid", "Pending", "Status", "Note")

        table_frame = tk.Frame(
            self.frame,
            relief="solid",
            bd=1,
            highlightthickness=1,
            highlightbackground="#ced4da"
        )
        table_frame.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=(0, 20)
        )

        self.invoice_tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse"
        )

        scroll_y = ttk.Scrollbar(
            table_frame,
            orient="vertical",
            command=self.invoice_tree.yview
        )
        self.invoice_tree.configure(yscrollcommand=scroll_y.set)

        for col in columns:
            self.invoice_tree.heading(
                col,
                text=col,
                anchor="center" if col in ("S.No", "Date", "Total", "Paid", "Pending", "Status") else "w"
            )
            if col == "S.No":
                width = 45
            elif col == "Invoice Number":
                width = 220
            elif col in ("Date", "Total", "Paid", "Pending"):
                width = 110
            elif col == "Status":
                width = 90
            elif col == "Note":
                width = 180
            else:
                width = 150

            self.invoice_tree.column(
                col,
                width=width,
                minwidth=35 if col == "S.No" else 50,
                stretch=(col in ("Invoice Number", "Note")),
                anchor="center" if col in ("S.No", "Date", "Total", "Paid", "Pending", "Status") else "w"
            )



        self.invoice_tree.pack(side="left", fill="both", expand=True)
        scroll_y.pack(side="right", fill="y")

        self.invoice_tree.tag_configure("evenrow", background="#ffffff")
        self.invoice_tree.tag_configure("oddrow", background="#f8f9fa")

        self.invoice_tree.bind("<Double-1>", self.on_invoice_double_click)
        self.invoice_tree.bind("<Return>", self.on_invoice_double_click)
        self.invoice_tree.bind("<Escape>", lambda e: self.show_customer_list())
        self.invoice_tree.bind("<BackSpace>", lambda e: self.show_customer_list())

        # Store all invoices for filtering
        self.all_invoices = get_customer_invoices(customer_name)
        self.current_customer_name = customer_name
        self.current_total_dues = total_dues
        
        # Display invoices
        self.refresh_invoice_display()

    def _focus_first_invoice_row(self, event=None):
        """Move focus from search bar to first invoice in table."""
        children = self.invoice_tree.get_children()
        if children:
            self.invoice_tree.selection_set(children[0])
            self.invoice_tree.focus(children[0])
            self.invoice_tree.focus_set()
        return "break"



    def pay_all_pending_bills(self):
        """Clear all pending invoices for the selected customer (Admin PIN Required)"""
        customer_name = getattr(self, "current_customer_name", None)
        total_dues = getattr(self, "current_total_dues", 0)

        if not customer_name:
            return

        if total_dues <= 0:
            messagebox.showinfo("No Pending Bills", f"{customer_name} has no pending bills")
            return

        # Security: Require Admin PIN
        if not request_admin_pin(self.frame, f"clear all pending bills (₹ {total_dues}) of {customer_name}"):
            return

        pending_invoices = [invoice for invoice in self.all_invoices if invoice[5] > 0]
        pending_invoice_count = len(pending_invoices)

        confirm_dialog = tk.Toplevel(self.frame)
        confirm_dialog.title("Confirm Clear All Bills")
        confirm_dialog.geometry("620x280")
        confirm_dialog.resizable(False, False)
        confirm_dialog.transient(self.frame.winfo_toplevel())
        confirm_dialog.grab_set()
        confirm_dialog.update_idletasks()

        screen_width = confirm_dialog.winfo_screenwidth()
        screen_height = confirm_dialog.winfo_screenheight()
        dialog_width = 620
        dialog_height = 280
        pos_x = (screen_width - dialog_width) // 2
        pos_y = (screen_height - dialog_height) // 2
        confirm_dialog.geometry(f"{dialog_width}x{dialog_height}+{pos_x}+{pos_y}")

        msg = tk.Label(
            confirm_dialog,
            text=(
                f"Are you sure you want to clear total "
                f"{pending_invoice_count} pending invoices of ₹ {total_dues}\n"
                f"of {customer_name}?"
            ),
            font=("Arial", 17, "bold"),
            fg="#333333",
            pady=36,
            padx=20,
            justify="center",
            wraplength=540,
            anchor="center"
        )
        msg.pack(fill="x", padx=20)

        btn_frame = tk.Frame(confirm_dialog)
        btn_frame.pack(pady=20)

        def confirm_yes():
            for invoice in pending_invoices:
                invoice_id, invoice_number, date_str, total, paid, pending, note = invoice
                update_invoice_payment(invoice_id, total)

            record_audit_log(
                "BILL_CLEAR_ALL",
                f"Cleared all {pending_invoice_count} pending bills (Total dues: Rs.{total_dues}) for customer '{customer_name}'"
            )

            confirm_dialog.destroy()
            messagebox.showinfo("Success", f"All pending bills of {customer_name} cleared successfully")
            self.show_invoice_list(customer_name)

        def confirm_no():
            confirm_dialog.destroy()

        yes_btn = tk.Button(
            btn_frame,
            text="Yes",
            command=confirm_yes,
            bg="#66cc66",
            fg="white",
            font=("Arial", 13, "bold"),
            width=12,
            height=2
        )
        yes_btn.pack(side="left", padx=20)

        no_btn = tk.Button(
            btn_frame,
            text="No",
            command=confirm_no,
            bg="#ff6666",
            fg="white",
            font=("Arial", 13, "bold"),
            width=12,
            height=2
        )
        no_btn.pack(side="left", padx=20)

    def export_statement_pdf(self):
        """Generates a formal Statement of Account PDF for the selected customer."""
        customer_name = getattr(self, "current_customer_name", None)
        if not customer_name:
            return

        cust_info, transactions = get_customer_statement_data(customer_name)
        if not cust_info or not transactions:
            messagebox.showinfo("No Transactions", f"No transactions found for {customer_name}")
            return

        import re
        safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', customer_name)
        today_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_path = os.path.join(INVOICES_DIR, f"Statement_{safe_name}_{today_str}.pdf")

        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
            from database import get_shop_details

            shop = get_shop_details()

            pdf = canvas.Canvas(pdf_path, pagesize=letter)
            width, height = letter

            # Header Title
            pdf.setFont("Helvetica-Bold", 18)
            pdf.setFillColorRGB(0.12, 0.14, 0.18)
            pdf.drawString(40, height - 50, "STATEMENT OF ACCOUNT")

            pdf.setFont("Helvetica", 9)
            pdf.setFillColorRGB(0.35, 0.35, 0.35)
            pdf.drawString(40, height - 68, f"Generated: {datetime.now().strftime('%d-%m-%Y %I:%M %p')}")

            # Business Details (Right aligned)
            pdf.setFont("Helvetica-Bold", 12)
            pdf.setFillColorRGB(0.1, 0.1, 0.1)
            pdf.drawRightString(width - 40, height - 50, str(shop["name"]))
            pdf.setFont("Helvetica", 9)
            pdf.setFillColorRGB(0.4, 0.4, 0.4)
            pdf.drawRightString(width - 40, height - 65, str(shop["address"]))
            pdf.drawRightString(width - 40, height - 78, f"Phone: {shop['phone']}")


            # Divider line
            pdf.setStrokeColorRGB(0.8, 0.8, 0.8)
            pdf.setLineWidth(1)
            pdf.line(40, height - 90, width - 40, height - 90)

            # Customer Details & Balance Box
            pdf.setFillColorRGB(0.96, 0.97, 0.98)
            pdf.roundRect(40, height - 165, width - 80, 65, 4, fill=1, stroke=0)

            pdf.setFont("Helvetica-Bold", 11)
            pdf.setFillColorRGB(0.2, 0.2, 0.2)
            pdf.drawString(55, height - 112, f"Customer: {cust_info['name']}")
            pdf.setFont("Helvetica", 9)
            pdf.drawString(55, height - 128, f"Phone: {cust_info['phone'] or 'N/A'}")
            pdf.drawString(55, height - 144, f"Address: {cust_info['address'] or 'N/A'}")

            # Balance Summary (Right Box)
            pdf.setFont("Helvetica-Bold", 10)
            pdf.drawString(width - 230, height - 112, f"Total Invoiced: Rs. {cust_info['total_invoiced']:.2f}")
            pdf.drawString(width - 230, height - 128, f"Total Paid: Rs. {cust_info['total_paid']:.2f}")
            pdf.setFillColorRGB(0.85, 0.1, 0.1)
            pdf.drawString(width - 230, height - 144, f"Net Balance: Rs. {cust_info['net_dues']:.2f}")

            # Table Header Bar
            table_top = height - 190
            pdf.setFillColorRGB(0.12, 0.14, 0.18)
            pdf.rect(40, table_top - 18, width - 80, 20, fill=1, stroke=0)

            pdf.setFont("Helvetica-Bold", 9)
            pdf.setFillColorRGB(1, 1, 1)
            pdf.drawString(50, table_top - 14, "Date")
            pdf.drawString(130, table_top - 14, "Invoice No")
            pdf.drawRightString(280, table_top - 14, "Billed (Debit)")
            pdf.drawRightString(370, table_top - 14, "Paid (Credit)")
            pdf.drawRightString(460, table_top - 14, "Pending")
            pdf.drawRightString(width - 50, table_top - 14, "Balance Due")

            # Table Rows
            y = table_top - 36
            for i, tx in enumerate(transactions):
                if y < 70:
                    # Draw page footer on current page
                    pdf.setStrokeColorRGB(0.85, 0.85, 0.85)
                    pdf.line(40, 45, width - 40, 45)
                    pdf.setFont("Helvetica-Bold", 8)
                    pdf.setFillColorRGB(0.5, 0.5, 0.5)
                    pdf.drawRightString(width - 40, 32, "⚡ BizDabba by Wokdens.com")

                    pdf.showPage()
                    y = height - 60

                    # Table Header on new page
                    pdf.setFillColorRGB(0.12, 0.14, 0.18)
                    pdf.rect(40, y - 18, width - 80, 20, fill=1, stroke=0)
                    pdf.setFont("Helvetica-Bold", 9)
                    pdf.setFillColorRGB(1, 1, 1)
                    pdf.drawString(50, y - 14, "Date")
                    pdf.drawString(130, y - 14, "Invoice No")
                    pdf.drawRightString(280, y - 14, "Billed (Debit)")
                    pdf.drawRightString(370, y - 14, "Paid (Credit)")
                    pdf.drawRightString(460, y - 14, "Pending")
                    pdf.drawRightString(width - 50, y - 14, "Balance Due")
                    y -= 36

                # Alternate row shading
                if i % 2 == 1:
                    pdf.setFillColorRGB(0.97, 0.97, 0.97)
                    pdf.rect(40, y - 4, width - 80, 16, fill=1, stroke=0)

                pdf.setFont("Helvetica", 9)
                pdf.setFillColorRGB(0.2, 0.2, 0.2)
                pdf.drawString(50, y, str(tx["date"]))
                pdf.drawString(130, y, f"INV-{tx['invoice_number']}")
                pdf.drawRightString(280, y, f"Rs. {tx['total']:.2f}")
                pdf.drawRightString(370, y, f"Rs. {tx['paid']:.2f}")
                pdf.drawRightString(460, y, f"Rs. {tx['pending']:.2f}")
                pdf.drawRightString(width - 50, y, f"Rs. {tx['running_balance']:.2f}")
                y -= 18

            # Footer
            pdf.setStrokeColorRGB(0.8, 0.8, 0.8)
            pdf.line(40, 45, width - 40, 45)
            pdf.setFont("Helvetica", 8)
            pdf.setFillColorRGB(0.4, 0.4, 0.4)
            pdf.drawString(40, 32, "Please verify all transactions and clear outstanding dues promptly.")
            pdf.setFont("Helvetica-Bold", 8)
            pdf.drawRightString(width - 40, 32, "⚡ BizDabba by Wokdens.com")


            pdf.save()

            from ui.invoice_ui import open_pdf_file
            open_pdf_file(pdf_path)

            messagebox.showinfo("Statement Generated", f"Statement of Account saved successfully:\n{pdf_path}", parent=self.frame)
        except Exception as e:
            messagebox.showerror("Error Generating Statement", str(e), parent=self.frame)

    def export_thermal_statement(self):
        """Generates an 80mm Thermal POS Statement for the customer dues, calibrated for Helix 1."""
        customer_name = getattr(self, "current_customer_name", None)
        if not customer_name:
            return

        cust_info, transactions = get_customer_statement_data(customer_name)
        if not cust_info or not transactions:
            messagebox.showinfo("No Transactions", f"No transactions found for {customer_name}", parent=self.frame)
            return

        import re
        from database import get_shop_details
        from config import INVOICES_DIR
        from ui.thermal_printer import find_thermal_printer, send_raw_to_printer, amount_to_indian_words
        from reportlab.pdfgen import canvas

        shop = get_shop_details()
        safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', customer_name)
        today_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_path = os.path.join(INVOICES_DIR, f"Statement_{safe_name}_{today_str}_80mm.pdf")

        # 1. Check if direct thermal printer exists
        t_printer = find_thermal_printer()
        if t_printer:
            try:
                ESC = b'\x1b'
                GS = b'\x1d'
                BOLD_ON = ESC + b'\x45\x01'
                BOLD_OFF = ESC + b'\x45\x00'
                ALIGN_CENTER = ESC + b'\x61\x01'
                ALIGN_LEFT = ESC + b'\x61\x00'
                ALIGN_RIGHT = ESC + b'\x61\x02'
                FEED_CUT = GS + b'\x56\x00'

                raw = bytearray()
                raw.extend(ALIGN_CENTER + BOLD_ON + f"{shop['name']}\n".encode('ascii', 'replace') + BOLD_OFF)
                raw.extend(f"{shop['address'][:48]}\n".encode('ascii', 'replace'))
                raw.extend(f"Phone: {shop['phone']}\n".encode('ascii', 'replace'))
                raw.extend(b'================================================\n')
                raw.extend(BOLD_ON + b'         STATEMENT OF ACCOUNT (PENDING)         \n' + BOLD_OFF)
                raw.extend(b'================================================\n')
                raw.extend(ALIGN_LEFT)
                raw.extend(f"Customer : {cust_info['name']}\n".encode('ascii', 'replace'))
                if cust_info.get('phone'):
                    raw.extend(f"Phone    : {cust_info['phone']}\n".encode('ascii', 'replace'))
                raw.extend(f"Date     : {datetime.now().strftime('%d-%m-%Y %I:%M %p')}\n".encode('ascii', 'replace'))
                raw.extend(b'------------------------------------------------\n')
                raw.extend(b'Date       Inv No      Billed    Paid    Pending\n')
                raw.extend(b'------------------------------------------------\n')

                for tx in transactions:
                    dt = str(tx['date'])[:10]
                    inv = f"INV-{tx['invoice_number']}"[:9]
                    bld = f"{tx['total']:,.0f}"[:8]
                    pd = f"{tx['paid']:,.0f}"[:7]
                    pnd = f"{tx['pending']:,.0f}"[:7]
                    raw.extend(f"{dt:<10} {inv:<9} {bld:>8} {pd:>7} {pnd:>8}\n".encode('ascii', 'replace'))

                raw.extend(b'================================================\n')
                raw.extend(ALIGN_RIGHT)
                raw.extend(f"Total Invoiced : Rs. {cust_info['total_invoiced']:,.2f}\n".encode('ascii', 'replace'))
                raw.extend(f"Total Paid     : Rs. {cust_info['total_paid']:,.2f}\n".encode('ascii', 'replace'))
                raw.extend(BOLD_ON + f"NET BALANCE DUE: Rs. {cust_info['net_dues']:,.2f}\n".encode('ascii', 'replace') + BOLD_OFF)
                words = amount_to_indian_words(cust_info['net_dues'])
                if words:
                    raw.extend(f"({words})\n".encode('ascii', 'replace'))

                raw.extend(ALIGN_CENTER + b'------------------------------------------------\n')
                raw.extend(b'Please clear overdue balance at earliest.\n')
                raw.extend(BOLD_ON + b'BizDabba by Wokdens.com\n' + BOLD_OFF)
                raw.extend(FEED_CUT)

                ok, msg = send_raw_to_printer(t_printer, bytes(raw), doc_name=f"Stmt-{safe_name}")
                if ok:
                    messagebox.showinfo(
                        "Thermal Statement Sent",
                        f"80mm Statement for {customer_name} printed directly to '{t_printer}'.",
                        parent=self.frame
                    )
                    return
            except Exception as e:
                print(f"Direct thermal statement notice: {e}")

        # Fallback / PDF Generation: Standard 80mm PDF
        try:
            mm_to_pt = 72.0 / 25.4
            width_pt = 80.0 * mm_to_pt
            est_height = 280 + (len(transactions) * 24)
            height_pt = max(380.0, float(est_height))

            pdf = canvas.Canvas(pdf_path, pagesize=(width_pt, height_pt))
            margin = 8.0
            curr_y = height_pt - 16

            pdf.setFont("Helvetica-Bold", 10)
            pdf.drawCentredString(width_pt / 2, curr_y, str(shop['name']))
            curr_y -= 11

            pdf.setFont("Helvetica", 6.8)
            pdf.drawCentredString(width_pt / 2, curr_y, str(shop['address'])[:50])
            curr_y -= 9
            pdf.drawCentredString(width_pt / 2, curr_y, f"Phone: {shop['phone']}")
            curr_y -= 8

            pdf.setLineWidth(0.8)
            pdf.line(margin, curr_y, width_pt - margin, curr_y)
            curr_y -= 10

            pdf.setFont("Helvetica-Bold", 8.5)
            pdf.drawCentredString(width_pt / 2, curr_y, "STATEMENT OF ACCOUNT (PENDING)")
            curr_y -= 10

            pdf.setFont("Helvetica", 7.0)
            pdf.drawString(margin, curr_y, f"Customer: {cust_info['name'][:30]}")
            curr_y -= 8.5
            pdf.drawString(margin, curr_y, f"Date: {datetime.now().strftime('%d-%m-%Y %I:%M %p')}")
            curr_y -= 6

            pdf.line(margin, curr_y, width_pt - margin, curr_y)
            curr_y -= 9

            pdf.setFont("Helvetica-Bold", 6.8)
            pdf.drawString(margin, curr_y, "Date / Inv No")
            pdf.drawRightString(width_pt - margin, curr_y, "Billed | Paid | Pending")
            curr_y -= 5

            pdf.setLineWidth(0.5)
            pdf.line(margin, curr_y, width_pt - margin, curr_y)
            curr_y -= 9

            for tx in transactions:
                pdf.setFont("Helvetica-Bold", 6.8)
                pdf.drawString(margin, curr_y, f"INV-{tx['invoice_number']} ({tx['date'][:10]})")
                pdf.setFont("Helvetica", 6.5)
                pdf.drawRightString(width_pt - margin, curr_y, f"Rs.{tx['total']:,.0f} | Rs.{tx['paid']:,.0f} | Rs.{tx['pending']:,.0f}")
                curr_y -= 10

            pdf.setLineWidth(0.8)
            pdf.line(margin, curr_y, width_pt - margin, curr_y)
            curr_y -= 11

            pdf.setFont("Helvetica", 7.0)
            pdf.drawString(margin, curr_y, f"Total Invoiced: Rs.{cust_info['total_invoiced']:,.2f}")
            curr_y -= 9
            pdf.drawString(margin, curr_y, f"Total Paid: Rs.{cust_info['total_paid']:,.2f}")
            curr_y -= 11

            pdf.setFont("Helvetica-Bold", 8.5)
            pdf.drawRightString(width_pt - margin, curr_y, f"NET DUES: Rs. {cust_info['net_dues']:,.2f}")
            curr_y -= 9

            words = amount_to_indian_words(cust_info['net_dues'])
            if words:
                pdf.setFont("Helvetica-Oblique", 6.0)
                pdf.drawRightString(width_pt - margin, curr_y, f"({words})")
                curr_y -= 8

            curr_y -= 4
            pdf.line(margin, curr_y, width_pt - margin, curr_y)
            curr_y -= 8

            pdf.setFont("Helvetica", 6.2)
            pdf.drawCentredString(width_pt / 2, curr_y, "Please clear overdue balance at earliest.")
            curr_y -= 7
            pdf.setFont("Helvetica-Bold", 6.8)
            pdf.drawCentredString(width_pt / 2, curr_y, "BizDabba by Wokdens.com")

            pdf.save()

            from ui.invoice_ui import open_pdf_file
            open_pdf_file(pdf_path)
            messagebox.showinfo("Thermal Statement Generated", f"80mm Thermal Statement saved to:\n{pdf_path}", parent=self.frame)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate 80mm statement: {str(e)}", parent=self.frame)


    def filter_invoices(self, event=None):
        """Filter invoices based on search text and status filter (All, Pending, Paid)."""
        search_kw = getattr(self, "invoice_search_entry", None)
        keyword = search_kw.get().strip().lower() if search_kw else ""
        status_filter = getattr(self, "status_filter_var", None)
        status_val = status_filter.get() if status_filter else "All"

        self.invoice_tree.delete(*self.invoice_tree.get_children())

        display_count = 0
        for row in getattr(self, "all_invoices", []):
            invoice_id, invoice_number, date_str, total, paid, pending, note = row[:7]
            inv_status = row[7] if len(row) > 7 else "ACTIVE"

            # Status filter
            if status_val == "Pending" and (pending <= 0 or inv_status == "CANCELLED"):
                continue
            elif status_val == "Paid" and (pending > 0 or inv_status == "CANCELLED"):
                continue

            # Keyword filter (invoice number, date, note, amounts)
            if keyword:
                searchable_text = f"inv-{invoice_number} {date_str} {note or ''} {total} {paid} {pending} {inv_status}".lower()
                if keyword not in searchable_text:
                    continue

            if inv_status == "CANCELLED":
                status = "CANCELLED"
            else:
                status = "Pending" if pending > 0 else "Paid"
            values = (
                str(display_count + 1),
                f"INV-{invoice_number}",
                date_str,
                f"₹ {total}",
                f"₹ {paid}",
                f"₹ {pending}",
                status,
                note or ""
            )
            tag = "evenrow" if display_count % 2 == 0 else "oddrow"
            self.invoice_tree.insert("", "end", values=values, iid=invoice_id, tags=(tag,))
            display_count += 1

    def refresh_invoice_display(self):
        """Refresh invoice tree with current filter"""
        self.filter_invoices()



    def on_invoice_double_click(self, event=None):
        """Open payment dialog or edit note depending on clicked column or keyboard selection"""
        if event and hasattr(event, "x") and hasattr(event, "y") and event.x is not None and event.y is not None:
            region = self.invoice_tree.identify("region", event.x, event.y)
            if region not in ("cell", "tree"):
                return
            invoice_id = self.invoice_tree.identify_row(event.y)
            column = self.invoice_tree.identify_column(event.x)
        else:
            sel = self.invoice_tree.selection()
            if not sel:
                children = self.invoice_tree.get_children()
                if children:
                    self.invoice_tree.selection_set(children[0])
                    sel = (children[0],)
                else:
                    return
            invoice_id = sel[0]
            column = "#5"

        if not invoice_id:
            return

        self.selected_invoice = invoice_id
        if column == "#8":
            self.edit_invoice_note(invoice_id)
        else:
            self.show_payment_dialog(invoice_id)


    def edit_invoice_note(self, invoice_id):
        # Security: Require Admin PIN to edit note
        if not request_admin_pin(self.frame, "modify invoice note"):
            return

        current_values = self.invoice_tree.item(invoice_id)["values"]
        current_note = current_values[7] if len(current_values) > 7 else ""


        dialog = tk.Toplevel(self.frame)
        dialog.title("Edit Note")
        dialog.geometry("520x260")
        dialog.transient(self.frame.winfo_toplevel())
        dialog.grab_set()

        tk.Label(
            dialog,
            text="Update invoice note",
            font=("Arial", 14, "bold")
        ).pack(pady=10)

        note_text = tk.Text(dialog, width=50, height=7, font=("Arial", 11))
        note_text.pack(padx=20, pady=10, fill="both", expand=True)
        note_text.insert("1.0", current_note)

        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=10)

        def save_note():
            new_note = note_text.get("1.0", tk.END).strip()
            update_invoice_note(invoice_id, new_note)
            dialog.destroy()
            self.show_invoice_list(self.current_customer_name)

        tk.Button(
            btn_frame,
            text="Save",
            command=save_note,
            bg="#66cc66",
            fg="white",
            font=("Arial", 11, "bold"),
            width=12
        ).pack(side="left", padx=10)

        tk.Button(
            btn_frame,
            text="Cancel",
            command=dialog.destroy,
            bg="#cccccc",
            font=("Arial", 11, "bold"),
            width=12
        ).pack(side="left", padx=10)


    # =========================
    # PAYMENT DIALOG
    # =========================

    def show_payment_dialog(self, invoice_id):
        """Show payment update dialog for invoice"""
        
        invoice_data = get_invoice_details_by_id(invoice_id)
        
        if not invoice_data:
            messagebox.showerror("Error", "Invoice not found")
            return

        inv_id, inv_number, customer_name, date_str, total, paid, pending, note = invoice_data

        # Create dialog with scrollbar - optimized height & responsive full-screen maximizing
        dialog = tk.Toplevel(self.parent)
        dialog.title(f"Update Payment - INV-{inv_number}")
        dialog.geometry("960x700")
        dialog.minsize(820, 520)

        # Main canvas for scrolling
        canvas = tk.Canvas(dialog, highlightthickness=0)
        scrollbar = ttk.Scrollbar(dialog, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        frame_window_id = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        def _on_canvas_configure(event):
            # Dynamically stretch the scrollable_frame to match the canvas width when resized/maximized
            canvas.itemconfig(frame_window_id, width=event.width)

        canvas.bind("<Configure>", _on_canvas_configure)

        def _on_mousewheel(event):
            try:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except Exception:
                pass

        dialog.bind("<MouseWheel>", _on_mousewheel)
        canvas.bind("<MouseWheel>", _on_mousewheel)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # =========================
        # INVOICE DETAILS - OPTIMIZED LAYOUT
        # =========================

        details_frame = tk.LabelFrame(scrollable_frame, text="Invoice Details", padx=15, pady=10)
        details_frame.pack(fill="x", padx=20, pady=10)

        # Left column (Date and Customer)
        left_column = tk.Frame(details_frame)
        left_column.pack(side="left", fill="x", expand=True)

        date_row = tk.Frame(left_column)
        date_row.pack(anchor="w", pady=2)
        tk.Label(date_row, text="Date:", font=("Arial", 10, "bold")).pack(side="left")
        tk.Label(date_row, text=date_str, font=("Arial", 10)).pack(side="left", padx=10)

        customer_row = tk.Frame(left_column)
        customer_row.pack(anchor="w", pady=2)
        tk.Label(customer_row, text="Customer:", font=("Arial", 10, "bold")).pack(side="left")
        tk.Label(customer_row, text=customer_name, font=("Arial", 10)).pack(side="left", padx=10)

        # Right column (Invoice Number and Total Pending)
        right_column = tk.Frame(details_frame)
        right_column.pack(side="right", fill="x", expand=True)

        inv_row = tk.Frame(right_column)
        inv_row.pack(anchor="w", pady=2)
        tk.Label(
            inv_row,
            text=f"Invoice Number: INV-{inv_number}",
            font=("Arial", 10, "bold"),
            fg="#0066ff"
        ).pack(side="left")

        pending_row = tk.Frame(right_column)
        pending_row.pack(anchor="w", pady=2)
        tk.Label(pending_row, text="Total Pending:", font=("Arial", 10, "bold")).pack(side="left")
        tk.Label(pending_row, text=f"₹ {pending}", font=("Arial", 11, "bold"), fg="red").pack(side="left", padx=10)

        # =========================
        # INVOICE ITEMS TABLE
        # =========================

        items_frame = tk.LabelFrame(scrollable_frame, text="Invoice Items", padx=15, pady=15)
        items_frame.pack(fill="both", expand=True, padx=20, pady=10)

        items_table_frame = tk.Frame(
            items_frame,
            relief="solid",
            bd=1,
            highlightthickness=1,
            highlightbackground="#ced4da"
        )
        items_table_frame.pack(fill="both", expand=True)

        columns = ("S.No", "Qty", "Product", "Price", "Unit", "Discount", "Discount On", "Total")
        items_tree = ttk.Treeview(items_table_frame, columns=columns, show="headings", height=8)
        items_scrollbar = ttk.Scrollbar(items_table_frame, orient="vertical", command=items_tree.yview)
        items_tree.configure(yscrollcommand=items_scrollbar.set)

        for col in columns:
            items_tree.heading(
                col,
                text=col,
                anchor="center" if col in ("S.No", "Qty", "Price", "Unit", "Discount", "Discount On", "Total") else "w"
            )
            is_product = (col == "Product")
            width = 50 if col == "S.No" else (300 if is_product else 95)
            items_tree.column(
                col,
                width=width,
                stretch=is_product,
                anchor="center" if col in ("S.No", "Qty", "Price", "Unit", "Discount", "Discount On", "Total") else "w"
            )

        items_tree.pack(side="left", fill="both", expand=True)
        items_scrollbar.pack(side="right", fill="y")

        items_tree.tag_configure("evenrow", background="#ffffff")
        items_tree.tag_configure("oddrow", background="#f8f9fa")

        # Load items
        invoice_items = get_invoice_items(invoice_id)
        for idx, item in enumerate(invoice_items):
            if len(item) >= 9:
                qty, product, mrp, price, unit, discount, discount_base, item_total, increase = item[:9]
            elif len(item) == 8:
                qty, product, mrp, price, unit, discount, discount_base, item_total = item
            elif len(item) == 7:
                qty, product, price, unit, discount, discount_base, item_total = item
            else:
                qty = item[0] if len(item) > 0 else 1
                product = item[1] if len(item) > 1 else ""
                price = item[2] if len(item) > 2 else 0
                unit = item[3] if len(item) > 3 else "Pcs"
                discount = item[4] if len(item) > 4 else 0
                discount_base = item[5] if len(item) > 5 else "Price"
                item_total = item[6] if len(item) > 6 else (qty * price)

            values = (str(idx + 1), qty, product, f"₹{price}", unit, f"{discount}%", discount_base, f"₹{item_total}")
            tag = "evenrow" if idx % 2 == 0 else "oddrow"
            items_tree.insert("", "end", values=values, tags=(tag,))



        # =========================
        # PAYMENT UPDATE
        # =========================

        payment_frame = tk.LabelFrame(scrollable_frame, text="Payment Update", padx=15, pady=15)
        payment_frame.pack(fill="x", padx=20, pady=10)

        tk.Label(payment_frame, text="Current Paid:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w", pady=5)
        tk.Label(payment_frame, text=f"₹ {paid}", font=("Arial", 10)).grid(row=0, column=1, sticky="w", padx=10, pady=5)

        tk.Label(payment_frame, text="Current Pending:", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky="w", pady=5)
        tk.Label(payment_frame, text=f"₹ {pending}", font=("Arial", 10)).grid(row=1, column=1, sticky="w", padx=10, pady=5)

        # Option: Pay Partially (incremental)
        tk.Label(payment_frame, text="Pay Partially:", font=("Arial", 10, "bold")).grid(row=2, column=0, sticky="w", pady=10)

        pay_partial_entry = tk.Entry(payment_frame, font=("Arial", 10), width=20)
        pay_partial_entry.insert(0, "0")
        pay_partial_entry.grid(row=2, column=1, sticky="w", padx=10, pady=10)

        # Real-time pending calculation
        pending_label = tk.Label(payment_frame, text=f"New Pending: ₹ {pending}", font=("Arial", 10, "bold"), fg="red")
        pending_label.grid(row=3, column=0, columnspan=2, sticky="w", pady=10)

        def update_pending_display(event=None):
            try:
                pay_partial = float(pay_partial_entry.get()) if pay_partial_entry.get() else 0
                new_pending = max(0, pending - pay_partial)
                pending_label.config(text=f"New Pending: ₹ {new_pending}")
            except:
                pending_label.config(text=f"New Pending: ₹ {pending}")

        pay_partial_entry.bind("<KeyRelease>", update_pending_display)

        # =========================
        # BUTTONS
        # =========================

        button_frame = tk.Frame(scrollable_frame)
        button_frame.pack(fill="x", padx=20, pady=20)

        def clear_bill():
            """Mark the entire bill as paid with confirmation (Admin PIN Required)"""
            if not request_admin_pin(dialog, f"clear bill INV-{inv_number} (₹ {pending})"):
                return

            # Confirmation popup - larger and bolder
            confirm_dialog = tk.Toplevel(dialog)
            confirm_dialog.title("Confirm Payment")
            confirm_dialog.geometry("560x260")
            confirm_dialog.resizable(False, False)
            
            # Center the dialog
            confirm_dialog.transient(dialog)
            confirm_dialog.grab_set()
            
            # Message label - bold and large
            msg = tk.Label(
                confirm_dialog,
                text=f"Are you sure {customer_name}\nhas paid ₹ {pending}?",
                font=("Arial", 17, "bold"),
                fg="#333333",
                pady=38,
                padx=20,
                justify="center"
            )
            msg.pack()
            
            # Button frame
            btn_frame = tk.Frame(confirm_dialog)
            btn_frame.pack(pady=20)
            
            response_var = [None]
            
            def confirm_yes():
                response_var[0] = True
                confirm_dialog.destroy()
            
            def confirm_no():
                response_var[0] = False
                confirm_dialog.destroy()
            
            yes_btn = tk.Button(
                btn_frame,
                text="Yes",
                command=confirm_yes,
                bg="#66cc66",
                fg="white",
                font=("Arial", 13, "bold"),
                width=12,
                height=2
            )
            yes_btn.pack(side="left", padx=20)
            
            no_btn = tk.Button(
                btn_frame,
                text="No",
                command=confirm_no,
                bg="#ff6666",
                fg="white",
                font=("Arial", 13, "bold"),
                width=12,
                height=2
            )
            no_btn.pack(side="left", padx=20)
            
            confirm_dialog.wait_window()
            response = response_var[0]
            
            if response:
                # Update database - set paid to total
                update_invoice_payment(invoice_id, total)
                record_audit_log(
                    "BILL_CLEAR",
                    f"Cleared full bill INV-{inv_number} (Paid: Rs.{pending}) for customer '{customer_name}'"
                )
                messagebox.showinfo("Success", "Bill marked as paid successfully")
                
                # Refresh invoice list
                dialog.destroy()
                self.show_invoice_list(self.current_customer_name)
            else:
                messagebox.showinfo("Cancelled", "Payment not confirmed")

        def pay_partially():
            try:
                pay_partial_amount = float(pay_partial_entry.get())
                if pay_partial_amount <= 0:
                    messagebox.showerror("Error", "Please enter a valid amount to pay")
                    return

                if pay_partial_amount > pending:
                    messagebox.showerror("Error", f"Payment amount (₹ {pay_partial_amount}) cannot exceed pending (₹ {pending})")
                    return

                if not request_admin_pin(dialog, f"record partial payment of ₹ {pay_partial_amount} for INV-{inv_number}"):
                    return

                new_paid = paid + pay_partial_amount
                
                # Update database
                update_invoice_payment(invoice_id, new_paid)
                record_audit_log(
                    "PARTIAL_PAYMENT",
                    f"Paid partial amount Rs.{pay_partial_amount} on bill INV-{inv_number} for customer '{customer_name}' (New Paid: Rs.{new_paid})"
                )

                messagebox.showinfo("Success", f"Payment of ₹ {pay_partial_amount} recorded successfully")

                # Refresh invoice list
                dialog.destroy()
                self.show_invoice_list(self.current_customer_name)

            except ValueError:
                messagebox.showerror("Error", "Please enter a valid amount")

        pay_partial_entry.bind("<Return>", lambda e: pay_partially())
        pay_partial_entry.bind("<FocusIn>", lambda e: pay_partial_entry.selection_range(0, tk.END))
        dialog.bind("<Escape>", lambda e: dialog.destroy())

        def open_thermal_receipt():
            from ui.invoice_ui import generate_thermal_receipt_pdf, open_pdf_file
            from ui.thermal_printer import print_receipt_direct, find_thermal_printer
            from config import INVOICES_DIR
            t_printer = find_thermal_printer()
            if t_printer:
                ok, msg = print_receipt_direct(
                    invoice_number=inv_number,
                    customer_name=customer_name,
                    items=invoice_items,
                    grand_total=total,
                    paid_amount=paid,
                    note=note,
                    date_str=date_str,
                    printer_name=t_printer
                )
                if ok:
                    messagebox.showinfo(
                        "Thermal Print Sent",
                        f"Receipt for INV-{inv_number} printed directly to '{t_printer}'.",
                        parent=dialog
                    )
                    return

            generate_thermal_receipt_pdf(
                invoice_number=inv_number,
                customer_name=customer_name,
                items=invoice_items,
                grand_total=total,
                paid_amount=paid,
                note=note,
                date_str=date_str,
                open_file=True
            )

        def open_a4_pdf():
            from ui.invoice_ui import generate_a4_invoice_pdf
            generate_a4_invoice_pdf(
                invoice_number=inv_number,
                customer_name=customer_name,
                items=invoice_items,
                grand_total=total,
                paid_amount=paid,
                note=note,
                date_str=date_str,
                open_file=True
            )

        clear_bill_btn = tk.Button(
            button_frame,
            text="Clear Bill",
            command=clear_bill,
            bg="#d9534f",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=10
        )
        clear_bill_btn.pack(side="left", padx=5)

        pay_partial_btn = tk.Button(
            button_frame,
            text="Pay Partially (Enter)",
            command=pay_partially,
            bg="#0275d8",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=10
        )
        pay_partial_btn.pack(side="left", padx=5)

        thermal_btn = tk.Button(
            button_frame,
            text="🖨️ 80mm Thermal",
            command=open_thermal_receipt,
            bg="#5634f0",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=10
        )
        thermal_btn.pack(side="left", padx=5)

        a4_btn = tk.Button(
            button_frame,
            text="📄 A4 PDF",
            command=open_a4_pdf,
            bg="#28a745",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=10
        )
        a4_btn.pack(side="left", padx=5)

        cancel_btn = tk.Button(
            button_frame,
            text="Cancel (Esc)",
            command=dialog.destroy,
            bg="#cccccc",
            font=("Arial", 10, "bold"),
            padx=10
        )
        cancel_btn.pack(side="left", padx=5)



