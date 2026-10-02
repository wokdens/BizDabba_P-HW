import os

import tkinter as tk

from tkinter import ttk, messagebox

from database import get_connection, update_invoice_note
from config import INVOICES_DIR
from ui.admin_auth_dialog import request_admin_pin




class InvoiceHistoryUI:

    def __init__(self, parent, app=None):

        self.parent = parent
        self.app = app
        self.frame = tk.Frame(parent)

        self.frame.pack(
            fill="both",
            expand=True
        )

        # =========================
        # TITLE
        # =========================

        title = tk.Label(
            self.frame,
            text="Invoice History",
            font=("Arial", 18, "bold")
        )

        title.pack(pady=10)

        # =========================
        # SEARCH
        # =========================

        search_frame = tk.Frame(self.frame)

        search_frame.pack(
            fill="x",
            padx=20,
            pady=10
        )

        tk.Label(
            search_frame,
            text="Search:"
        ).pack(side="left")

        self.search_entry = tk.Entry(
            search_frame,
            width=40,
            font=("Arial", 11)
        )

        self.search_entry.pack(
            side="left",
            padx=10
        )

        self.search_entry.bind(
            "<KeyRelease>",
            self.search_invoices
        )

        # =========================
        # TABLE
        # =========================

        columns = (
            "S.No",
            "Invoice No",
            "Date",
            "Customer",
            "Total",
            "Paid",
            "Pending",
            "Status",
            "Note"
        )

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
            pady=(0, 8)
        )

        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse"
        )

        scroll_y = ttk.Scrollbar(
            table_frame,
            orient="vertical",
            command=self.tree.yview
        )
        self.tree.configure(yscrollcommand=scroll_y.set)

        for col in columns:
            self.tree.heading(
                col,
                text=col,
                anchor="center" if col in ("S.No", "Date", "Total", "Paid", "Pending", "Status") else "w"
            )

            width = 150
            if col == "S.No":
                width = 45
            elif col == "Invoice No":
                width = 200
            elif col == "Customer":
                width = 190
            elif col in ("Date", "Total", "Paid", "Pending"):
                width = 100
            elif col == "Status":
                width = 110
            elif col == "Note":
                width = 160

            self.tree.column(
                col,
                width=width,
                minwidth=35 if col == "S.No" else 50,
                anchor="center" if col in ("S.No", "Date", "Total", "Paid", "Pending", "Status") else "w"
            )

        self.tree.pack(
            side="left",
            fill="both",
            expand=True
        )
        scroll_y.pack(
            side="right",
            fill="y"
        )

        self.tree.tag_configure("evenrow", background="#ffffff")
        self.tree.tag_configure("oddrow", background="#f8f9fa")
        self.tree.tag_configure("cancelledrow", background="#fff0f0", foreground="#842029")

        # Double Click & Keyboard Bindings
        self.tree.bind("<Double-1>", self.handle_double_click)
        self.tree.bind("<Return>", lambda e: self.on_edit_clicked())
        self.tree.bind("<Delete>", lambda e: self.on_cancel_clicked())

        # =========================
        # ACTION TOOLBAR
        # =========================
        action_bar = tk.Frame(self.frame, bg="#f8f9fa", pady=8, padx=20)
        action_bar.pack(fill="x", side="bottom")

        self.edit_btn = tk.Button(
            action_bar,
            text="✏️ Edit in Billing (Enter)",
            font=("Arial", 10, "bold"),
            bg="#0066cc",
            fg="white",
            activebackground="#0052a3",
            activeforeground="white",
            padx=14,
            pady=5,
            relief="raised",
            bd=2,
            command=self.on_edit_clicked
        )
        self.edit_btn.pack(side="left", padx=(0, 10))

        self.cancel_btn = tk.Button(
            action_bar,
            text="❌ Cancel / Void Bill (Del)",
            font=("Arial", 10, "bold"),
            bg="#dc3545",
            fg="white",
            activebackground="#c82333",
            activeforeground="white",
            padx=14,
            pady=5,
            relief="raised",
            bd=2,
            command=self.on_cancel_clicked
        )
        self.cancel_btn.pack(side="left", padx=10)

        self.print_btn = tk.Button(
            action_bar,
            text="🖨️ Print / View PDF",
            font=("Arial", 10, "bold"),
            bg="#28a745",
            fg="white",
            activebackground="#218838",
            activeforeground="white",
            padx=14,
            pady=5,
            relief="raised",
            bd=2,
            command=self.open_invoice_pdf
        )
        self.print_btn.pack(side="left", padx=10)

        help_lbl = tk.Label(
            action_bar,
            text="💡 Tip: Double-click row for all options. Cancelling automatically restores stock.",
            font=("Arial", 9, "italic"),
            fg="#6c757d",
            bg="#f8f9fa"
        )
        help_lbl.pack(side="right", padx=10)

        self.all_invoices = []

        self.load_invoices()

    # =========================
    # LOAD INVOICES
    # =========================

    def load_invoices(self):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute("""
        SELECT
            invoices.id,
            invoices.invoice_number,
            COALESCE(strftime('%d-%m-%Y', invoices.invoice_date), 'N/A'),
            customers.name,
            invoices.total,
            invoices.paid,
            invoices.pending,
            COALESCE(invoices.note, ''),
            COALESCE(invoices.status, 'ACTIVE')

        FROM invoices

        JOIN customers
        ON invoices.customer_id = customers.id

        ORDER BY invoices.id DESC
        """)

        data = cursor.fetchall()

        conn.close()

        self.all_invoices = data

        self.render_table(data)

    # =========================
    # RENDER TABLE
    # =========================

    def render_table(self, data):

        self.tree.delete(
            *self.tree.get_children()
        )

        for idx, row in enumerate(data):

            invoice_no = row[1]  # invoice_number column
            customer_name = row[3]
            status = row[8] if len(row) > 8 else "ACTIVE"

            # Format: INV-DDMMYY_01_customername
            if invoice_no:
                safe_name = "".join(
                    c for c in customer_name if c.isalnum() or c in (" ", "-", "_")
                ).strip().replace(" ", "_")
                display_invoice = f"INV-{invoice_no}_{safe_name}"
            else:
                display_invoice = f"INV-{row[0]}"

            status_display = "❌ Cancelled" if status == "CANCELLED" else "✅ Active"

            new_row = (
                str(idx + 1),
                display_invoice,
                row[2],
                row[3],
                f"₹ {row[4]}",
                f"₹ {row[5]}",
                f"₹ {row[6]}",
                status_display,
                row[7]
            )

            if status == "CANCELLED":
                tag = "cancelledrow"
            else:
                tag = "evenrow" if idx % 2 == 0 else "oddrow"

            self.tree.insert(
                "",
                "end",
                values=new_row,
                iid=row[0],
                tags=(tag,)
            )


    # =========================
    # SEARCH (SMART MULTI-TERM TOKEN SEARCH)
    # =========================

    def search_invoices(self, event=None):

        keyword = (
            self.search_entry.get()
            .strip()
            .lower()
        )

        search_terms = keyword.split()
        if not search_terms:
            self.render_table(self.all_invoices)
            return

        filtered = []

        for row in self.all_invoices:
            # Format: row = (id, invoice_number, date, customer_name, total, paid, pending, note, status)
            invoice_no = str(row[1] or row[0]).lower()
            date_str = str(row[2] or "").lower()
            customer = str(row[3] or "").lower()
            total = str(row[4] or "")
            paid = str(row[5] or "")
            pending = str(row[6] or "")
            note = str(row[7] or "").lower()
            status = str(row[8] if len(row) > 8 else "").lower()

            searchable_text = f"inv-{invoice_no} {date_str} {customer} {total} {paid} {pending} {note} {status}".lower()

            if all(term in searchable_text for term in search_terms):
                filtered.append(row)

        self.render_table(filtered)


    # =========================
    # OPEN PDF
    # =========================

    def handle_double_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return

        item = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)

        if not item:
            return

        # Column #9 is Note
        if column == "#9":
            self.edit_note(item)
        else:
            self.open_invoice_pdf()

    def edit_note(self, invoice_id):
        # Security: Require Admin PIN to edit note
        if not request_admin_pin(self.frame, "modify invoice note"):
            return

        current_values = self.tree.item(invoice_id)["values"]
        current_note = current_values[8] if len(current_values) > 8 else ""

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
            self.load_invoices()

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

    def on_edit_clicked(self, target_iid=None):
        """Loads selected invoice into Sales Invoice screen for editing with automatic stock reconciliation."""
        selected = [target_iid] if target_iid else self.tree.selection()
        if not selected or not selected[0]:
            messagebox.showinfo("Select Invoice", "Please select an invoice from the table to edit.", parent=self.frame.winfo_toplevel())
            return

        inv_iid = selected[0]
        values = self.tree.item(inv_iid)["values"]
        inv_display = values[1]
        status = str(values[7]) if len(values) > 7 else ""

        if "Cancelled" in status:
            messagebox.showerror(
                "Cannot Edit",
                f"Invoice {inv_display} is CANCELLED and cannot be modified.\nCancelled invoices are voided.",
                parent=self.frame.winfo_toplevel()
            )
            return

        if not messagebox.askyesno(
            "Edit Invoice in Billing",
            f"Load {inv_display} into the Sales Invoice screen for editing?\n\n"
            f"• You can remove rejected items, adjust quantities, or add new items.\n"
            f"• Inventory stock will be automatically reconciled upon saving (removed items return to stock).\n"
            f"• Customer ledger and totals will be updated automatically.",
            parent=self.frame.winfo_toplevel()
        ):
            return

        if self.app and hasattr(self.app, "open_invoice"):
            self.app.open_invoice(invoice_id_to_edit=int(inv_iid))
        else:
            messagebox.showerror("Error", "Main application navigation reference is unavailable.", parent=self.frame.winfo_toplevel())

    def on_cancel_clicked(self, target_iid=None):
        """Cancels/voids an invoice, returning all sold items to inventory stock and clearing pending balance."""
        selected = [target_iid] if target_iid else self.tree.selection()
        if not selected or not selected[0]:
            messagebox.showinfo("Select Invoice", "Please select an invoice from the table to cancel.", parent=self.frame.winfo_toplevel())
            return

        inv_iid = selected[0]
        values = self.tree.item(inv_iid)["values"]
        inv_display = values[1]
        customer_name = values[3]
        total_str = values[4]
        status = str(values[7]) if len(values) > 7 else ""

        if "Cancelled" in status:
            messagebox.showinfo(
                "Already Cancelled",
                f"Invoice {inv_display} is already cancelled.",
                parent=self.frame.winfo_toplevel()
            )
            return

        # Security: Require Admin PIN
        if not request_admin_pin(self.frame, f"cancel / void {inv_display}"):
            return

        if not messagebox.askyesno(
            "Confirm Invoice Cancellation",
            f"Are you sure you want to CANCEL and VOID {inv_display}?\n"
            f"Customer: {customer_name}\n"
            f"Total: {total_str}\n\n"
            f"• All sold items on this bill will be returned to inventory stock automatically.\n"
            f"• Pending balance for this customer will be cleared.\n"
            f"• Invoice will remain in history marked as [CANCELLED] for audit trail.",
            parent=self.frame.winfo_toplevel()
        ):
            return

        from database import cancel_invoice
        try:
            ok, msg = cancel_invoice(int(inv_iid))
            if ok:
                messagebox.showinfo("Invoice Cancelled", msg, parent=self.frame.winfo_toplevel())
                self.load_invoices()
            else:
                messagebox.showerror("Cancellation Failed", msg, parent=self.frame.winfo_toplevel())
        except Exception as e:
            messagebox.showerror("Error", f"Failed to cancel invoice: {str(e)}", parent=self.frame.winfo_toplevel())

    def open_invoice_pdf(self):
        selected = self.tree.selection()
        if not selected:
            return

        inv_iid = selected[0]
        values = self.tree.item(inv_iid)["values"]
        invoice_display = str(values[1])  # Display format: INV-DDMMYY_01_customername
        clean_num = invoice_display.replace("INV-", "").strip()
        status = str(values[7]) if len(values) > 7 else ""
        is_cancelled = "Cancelled" in status

        # Modal to choose format or edit/cancel
        dialog = tk.Toplevel(self.frame)
        dialog.title("Invoice Options")
        dialog.geometry("480x340")
        dialog.resizable(False, False)
        dialog.transient(self.frame.winfo_toplevel())
        dialog.grab_set()

        # Center on parent window
        dialog.update_idletasks()
        try:
            px = self.frame.winfo_toplevel().winfo_rootx() + (self.frame.winfo_toplevel().winfo_width() // 2) - 240
            py = self.frame.winfo_toplevel().winfo_rooty() + (self.frame.winfo_toplevel().winfo_height() // 2) - 170
            dialog.geometry(f"480x340+{max(0, px)}+{max(0, py)}")
        except Exception:
            pass

        title_text = f"Estimate #{invoice_display}"
        if is_cancelled:
            title_text += " [CANCELLED]"

        tk.Label(
            dialog,
            text=title_text,
            font=("Arial", 12, "bold"),
            fg="#dc3545" if is_cancelled else "#1e293b"
        ).pack(pady=(14, 2))

        tk.Label(
            dialog,
            text="Choose an action for this invoice:",
            font=("Arial", 9),
            fg="#64748b"
        ).pack(pady=(0, 10))

        btn_frame = tk.Frame(dialog)
        btn_frame.pack(fill="x", padx=30, pady=2)

        def do_open(format_type):
            dialog.destroy()
            self._generate_and_open_invoice(inv_iid, clean_num, format_type)

        def do_edit():
            dialog.destroy()
            self.on_edit_clicked(inv_iid)

        def do_cancel():
            dialog.destroy()
            self.on_cancel_clicked(inv_iid)

        # 1. Thermal POS button (Indigo)
        thermal_btn = tk.Button(
            btn_frame,
            text="🖨️ 80mm Thermal POS Receipt (Direct Print)",
            command=lambda: do_open("thermal"),
            bg="#5634f0",
            fg="white",
            font=("Arial", 10, "bold"),
            relief="raised",
            bd=2,
            pady=6
        )
        thermal_btn.pack(fill="x", pady=4)

        # 2. A4 PDF button (Emerald)
        a4_btn = tk.Button(
            btn_frame,
            text="📄 Standard A4 PDF (WhatsApp / Print)",
            command=lambda: do_open("a4"),
            bg="#28a745",
            fg="white",
            font=("Arial", 10, "bold"),
            relief="raised",
            bd=2,
            pady=6
        )
        a4_btn.pack(fill="x", pady=4)

        # 3. Edit in Billing button (Blue)
        if not is_cancelled:
            edit_btn = tk.Button(
                btn_frame,
                text="✏️ Edit in Billing (Modify items & Reconcile Stock)",
                command=do_edit,
                bg="#0066cc",
                fg="white",
                font=("Arial", 10, "bold"),
                relief="raised",
                bd=2,
                pady=6
            )
            edit_btn.pack(fill="x", pady=4)

            # 4. Cancel / Void Bill button (Red)
            cancel_btn = tk.Button(
                btn_frame,
                text="❌ Cancel / Void Bill (Restores Stock to Inventory)",
                command=do_cancel,
                bg="#dc3545",
                fg="white",
                font=("Arial", 10, "bold"),
                relief="raised",
                bd=2,
                pady=6
            )
            cancel_btn.pack(fill="x", pady=4)

    def _generate_and_open_invoice(self, inv_iid, clean_num, format_type):
        from ui.invoice_ui import generate_thermal_receipt_pdf, generate_a4_invoice_pdf, open_pdf_file
        from database import get_invoice_details_by_id, get_invoice_by_number, get_invoice_items

        inv_data = None
        try:
            inv_data = get_invoice_details_by_id(int(inv_iid))
        except (ValueError, TypeError):
            pass

        if not inv_data:
            inv_data = get_invoice_by_number(clean_num)

        if not inv_data:
            messagebox.showerror("Error", f"Invoice record not found for {clean_num}", parent=self.frame.winfo_toplevel())
            return

        inv_id, inv_number, customer_name, date_str, total, paid, pending, note = inv_data[:8]
        items = get_invoice_items(inv_id)

        safe_name = "".join(
            c for c in customer_name if c.isalnum() or c in (" ", "-", "_")
        ).strip().replace(" ", "_")

        if format_type == "thermal":
            from ui.thermal_printer import print_receipt_direct, find_thermal_printer
            t_printer = find_thermal_printer()
            if t_printer:
                ok, msg = print_receipt_direct(
                    invoice_number=inv_number,
                    customer_name=customer_name,
                    items=items,
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
                        parent=self.frame.winfo_toplevel()
                    )
                    return

            thermal_filename = f"INV-{inv_number}_{safe_name}_80mm.pdf" if safe_name else f"INV-{inv_number}_80mm.pdf"
            thermal_path = os.path.join(INVOICES_DIR, thermal_filename)
            if os.path.exists(thermal_path):
                open_pdf_file(thermal_path)
                return

            generate_thermal_receipt_pdf(
                invoice_number=inv_number,
                customer_name=customer_name,
                items=items,
                grand_total=total,
                paid_amount=paid,
                note=note,
                date_str=date_str,
                open_file=True
            )
        else:
            a4_filename = f"INV-{inv_number}_{safe_name}.pdf" if safe_name else f"INV-{inv_number}.pdf"
            a4_path = os.path.join(INVOICES_DIR, a4_filename)
            if os.path.exists(a4_path):
                open_pdf_file(a4_path)
                return

            generate_a4_invoice_pdf(
                invoice_number=inv_number,
                customer_name=customer_name,
                items=items,
                grand_total=total,
                paid_amount=paid,
                note=note,
                date_str=date_str,
                open_file=True
            )

