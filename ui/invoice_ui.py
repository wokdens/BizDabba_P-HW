import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import Canvas
from database import (
    get_product_names,
    get_product_complete_details,
    save_complete_invoice,
    get_customer_names_with_phone,
    update_saved_invoice,
    get_invoice_with_items,
    get_last_active_invoice,
    record_audit_log
)

from ui.autocomplete_combobox import (
    AutocompleteCombobox
)

from ui.customer_popup import (
    CustomerPopup
)

from ui.admin_auth_dialog import (
    request_admin_pin,
    is_admin_mode
)

from reportlab.pdfgen import canvas
from datetime import datetime

import os
import shutil
import textwrap 

from config import INVOICES_DIR, PENDRIVE_DIR, get_pen_drive_dir


def _normalize_items(raw_items):
    """Normalizes both dict-based cart items and tuple-based database items into a uniform structure"""
    normalized = []
    for it in raw_items:
        if isinstance(it, dict):
            normalized.append({
                "name": str(it.get("name", "")),
                "quantity": it.get("quantity", 0),
                "price": float(it.get("price", 0) or 0),
                "mrp": float(it.get("mrp", 0) or 0),
                "unit": str(it.get("unit", "Pcs") or "Pcs"),
                "increase": float(it.get("increase", 0) or 0),
                "discount": float(it.get("discount", 0) or 0),
                "discount_base": str(it.get("discount_base", "Price") or "Price"),
                "total": float(it.get("total", 0) or 0)
            })
        elif isinstance(it, (list, tuple)):
            if len(it) == 7:
                qty, name, price, unit, disc, disc_base, tot = it
                normalized.append({
                    "name": str(name),
                    "quantity": qty,
                    "price": float(price or 0),
                    "mrp": 0.0,
                    "unit": str(unit or "Pcs"),
                    "increase": 0.0,
                    "discount": float(disc or 0),
                    "discount_base": str(disc_base or "Price"),
                    "total": float(tot or 0)
                })
            elif len(it) == 8:
                qty, name, mrp, price, unit, disc, disc_base, tot = it[:8]
                normalized.append({
                    "name": str(name),
                    "quantity": qty,
                    "price": float(price or 0),
                    "mrp": float(mrp or 0),
                    "unit": str(unit or "Pcs"),
                    "increase": 0.0,
                    "discount": float(disc or 0),
                    "discount_base": str(disc_base or "Price"),
                    "total": float(tot or 0)
                })
            elif len(it) >= 9:
                qty, name, mrp, price, unit, disc, disc_base, tot, inc = it[:9]
                normalized.append({
                    "name": str(name),
                    "quantity": qty,
                    "price": float(price or 0),
                    "mrp": float(mrp or 0),
                    "unit": str(unit or "Pcs"),
                    "increase": float(inc or 0),
                    "discount": float(disc or 0),
                    "discount_base": str(disc_base or "Price"),
                    "total": float(tot or 0)
                })
    return normalized


def open_pdf_file(path):
    """Opens a PDF file in the system default viewer/printer application"""
    try:
        abs_path = os.path.abspath(path)
        if os.path.exists(abs_path):
            if os.name == "nt":
                os.startfile(abs_path)
            else:
                import subprocess
                opener = "open" if os.name == "darwin" else "xdg-open"
                subprocess.Popen([opener, abs_path])
    except Exception:
        pass


def generate_thermal_receipt_pdf(
    invoice_number,
    customer_name,
    items,
    grand_total,
    paid_amount=0,
    note="",
    date_str=None,
    open_file=False
):
    """Generates a dedicated 80mm (3-Inch) Thermal POS Receipt with full 8-column table matching A4 layout"""
    safe_name = "".join(
        c for c in customer_name if c.isalnum() or c in (" ", "-", "_")
    ).strip().replace(" ", "_")

    clean_num = str(invoice_number).replace("INV-", "").strip()
    if safe_name:
        filename = f"INV-{clean_num}_{safe_name}_80mm.pdf"
    else:
        filename = f"INV-{clean_num}_80mm.pdf"

    path = os.path.join(INVOICES_DIR, filename)
    normalized_items = _normalize_items(items)

    width = 226.77  # 80mm in points (standard 3-inch roll)
    margin = 5.5
    table_w = 215.77
    table_left = margin
    table_right = margin + table_w

    # Calculate dynamic height based on 2-line item rows and note
    header_h = 65
    table_header_h = 16
    item_row_h = 36  # 2 lines per item with clear breathing separation
    items_h = len(normalized_items) * item_row_h

    summary_h = 60
    note_lines = textwrap.wrap(note.strip(), width=36) if note and note.strip() else []
    if note_lines:
        summary_h += len(note_lines) * 9 + 8

    footer_h = 35
    feed_padding = 18
    total_height = max(200, header_h + table_header_h + items_h + summary_h + footer_h + feed_padding)

    pdf = canvas.Canvas(path, pagesize=(width, total_height))

    # Header
    curr_y = total_height - 16
    pdf.setFillColorRGB(0, 0, 0)
    pdf.setStrokeColorRGB(0, 0, 0)

    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawCentredString(width / 2, curr_y, "ESTIMATE ONLY")

    curr_y -= 12
    pdf.setFont("Helvetica", 7.5)
    d_str = date_str or datetime.now().strftime("%d-%m-%Y  %I:%M %p")
    pdf.drawCentredString(width / 2, curr_y, f"Date: {d_str}")

    curr_y -= 12
    pdf.setFont("Helvetica", 8)
    pdf.drawString(table_left, curr_y, f"Est No   : INV-{clean_num}")

    curr_y -= 11
    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(table_left, curr_y, f"Customer : {customer_name.upper()}")

    curr_y -= 5
    pdf.setLineWidth(0.8)
    pdf.line(table_left, curr_y, table_right, curr_y)

    # =====================================
    # TABLE HEADER (OPTION 2: 2-LINE FORMAT)
    # =====================================
    curr_y -= 11
    pdf.setFont("Helvetica-Bold", 7.5)
    pdf.drawString(table_left, curr_y, "Item Description & Pricing Details")
    pdf.drawRightString(table_right, curr_y, "Amount")

    curr_y -= 4
    pdf.setLineWidth(0.5)
    pdf.line(table_left, curr_y, table_right, curr_y)

    # =====================================
    # TABLE ROWS (2 LINES PER ITEM WITH BREATHING GAP)
    # =====================================
    serial = 1
    for it in normalized_items:
        curr_y -= 11
        # Line 1: Bold Item Name
        pdf.setFont("Helvetica-Bold", 7.5)
        item_name = str(it.get("name", ""))[:38]
        pdf.drawString(table_left, curr_y, f"{serial}. {item_name}")

        curr_y -= 10
        # Line 2: Pricing Details & Total
        qty = it.get("quantity", 0)
        price = float(it.get("price", 0) or 0)
        unit = str(it.get("unit", "Pcs") or "Pcs").strip()
        unit_str = f" {unit}" if unit else " pcs"
        mrp = float(it.get("mrp", 0) or 0)
        inc = float(it.get("increase", 0) or 0)
        disc = float(it.get("discount", 0) or 0)
        total_val = float(it.get("total", 0) or 0)

        left_detail = f"   {qty}{unit_str} x Rs.{price:,.2f}"
        tags = []
        if mrp > 0:
            tags.append(f"MRP: {mrp:,.0f}")
        if inc > 0:
            inc_str = f"{int(inc) if inc.is_integer() else inc}%"
            tags.append(f"Inc: +{inc_str}")
        if disc > 0:
            disc_str = f"{int(disc) if disc.is_integer() else disc}%"
            tags.append(f"Disc: -{disc_str}")
        if tags:
            left_detail += f" ({' | '.join(tags)})"

        pdf.setFont("Helvetica", 7.0)
        pdf.drawString(table_left, curr_y, left_detail[:35])

        pdf.setFont("Helvetica-Bold", 7.5)
        pdf.drawRightString(table_right, curr_y, f"{total_val:,.2f}")

        # Distinct vertical separation between items for high readability
        curr_y -= 14
        serial += 1

    curr_y -= 2
    pdf.setLineWidth(0.8)
    pdf.line(table_left, curr_y, table_right, curr_y)

    # =====================================
    # SUMMARY SECTION
    # =====================================
    curr_y -= 11
    total_qty = sum(float(it.get("quantity", 0)) for it in normalized_items)
    pdf.setFont("Helvetica", 7.5)
    pdf.setFillColorRGB(0, 0, 0)
    pdf.drawString(table_left, curr_y, f"Total Items: {len(normalized_items)}   |   Total Qty: {int(total_qty) if total_qty.is_integer() else total_qty}")

    curr_y -= 16  # Clean breathing gap before Grand Total
    pdf.setFont("Helvetica-Bold", 9.5)
    pdf.drawRightString(table_right, curr_y, f"GRAND TOTAL: Rs. {grand_total:,.2f}")

    from ui.thermal_printer import amount_to_indian_words
    words = amount_to_indian_words(grand_total)
    if words:
        curr_y -= 10
        pdf.setFont("Helvetica-Oblique", 6.0)
        w_lines = textwrap.wrap(f"({words})", width=40)
        for wl in w_lines:
            pdf.drawRightString(table_right, curr_y, wl)
            curr_y -= 7.5

    if note_lines:
        curr_y -= 11
        pdf.setFont("Helvetica-Bold", 6.8)
        pdf.setFillColorRGB(0, 0, 0)
        pdf.drawString(table_left, curr_y, "Note: " + note_lines[0])
        for nl in note_lines[1:]:
            curr_y -= 8.5
            pdf.drawString(table_left + 18, curr_y, nl)

    curr_y -= 7
    pdf.setDash(1.5, 1.5)
    pdf.setLineWidth(0.5)
    pdf.line(table_left, curr_y, table_right, curr_y)
    pdf.setDash()

    # =====================================
    # FOOTER & BRANDING
    # =====================================
    curr_y -= 10
    pdf.setFont("Helvetica", 6.5)
    pdf.setFillColorRGB(0, 0, 0)
    pdf.drawCentredString(width / 2, curr_y, "Goods exchangeable in 7 days in sealed pack. No return on tinted paints.")

    curr_y -= 8
    pdf.setFont("Helvetica", 6.0)
    pdf.drawCentredString(width / 2, curr_y, "GST extra as applicable. E.&O.E.")

    curr_y -= 9
    pdf.setFont("Helvetica-Bold", 7.0)
    pdf.drawCentredString(width / 2, curr_y, "Powered by wokdens.com")

    pdf.save()

    # Guarantee invoice is saved strictly to Pen Drive storage
    pd_dir = PENDRIVE_DIR or get_pen_drive_dir()
    if pd_dir and os.path.isdir(pd_dir):
        pd_inv_dir = os.path.join(pd_dir, "invoices")
        os.makedirs(pd_inv_dir, exist_ok=True)
        pd_file_path = os.path.join(pd_inv_dir, os.path.basename(path))
        if os.path.abspath(path).lower() != os.path.abspath(pd_file_path).lower():
            try:
                shutil.copy2(path, pd_file_path)
            except Exception:
                pass

    if open_file:
        open_pdf_file(path)

    return path


def generate_a4_invoice_pdf(
    invoice_number,
    customer_name,
    items,
    grand_total,
    paid_amount=0,
    note="",
    date_str=None,
    open_file=False
):
    """Generates standard / compact A4 Invoice PDF (for WhatsApp sharing and A4 printers)"""
    safe_name = "".join(
        c for c in customer_name if c.isalnum() or c in (" ", "-", "_")
    ).strip().replace(" ", "_")

    clean_num = str(invoice_number).replace("INV-", "").strip()
    if safe_name:
        path = os.path.join(INVOICES_DIR, f"INV-{clean_num}_{safe_name}.pdf")
    else:
        path = os.path.join(INVOICES_DIR, f"INV-{clean_num}.pdf")

    normalized_items = _normalize_items(items)

    pdf = canvas.Canvas(path)
    page_width, page_height = 595.27, 841.89  # Standard A4

    # =====================================
    # HEADER (ESTIMATE ONLY - NO SHOP DETAILS)
    # =====================================
    pdf.setFont("Helvetica-Bold", 16)
    pdf.setFillColorRGB(0.12, 0.14, 0.18)
    pdf.drawString(40, 805, "ESTIMATE ONLY")

    pdf.setFont("Helvetica", 9)
    pdf.setFillColorRGB(0.35, 0.38, 0.42)
    d_str = date_str or datetime.now().strftime("%d-%m-%Y  %I:%M %p")
    pdf.drawRightString(555, 805, f"Date: {d_str}")

    pdf.setStrokeColorRGB(0.8, 0.83, 0.88)
    pdf.setLineWidth(1)
    pdf.line(40, 792, 555, 792)

    # =====================================
    # ESTIMATE & CUSTOMER INFO
    # =====================================
    pdf.setFont("Helvetica-Bold", 9.5)
    pdf.setFillColorRGB(0.2, 0.2, 0.2)
    pdf.drawString(40, 775, f"Estimate No : INV-{clean_num}")
    pdf.drawString(280, 775, f"Customer : {customer_name.upper()}")

    # =====================================
    # TABLE HEADER
    # =====================================
    table_top = 758
    header_height = 20

    pdf.setFillColorRGB(0.93, 0.94, 0.97)
    pdf.rect(40, table_top - header_height, 515, header_height, fill=True, stroke=False)

    pdf.setStrokeColorRGB(0.75, 0.78, 0.84)
    pdf.setLineWidth(0.8)
    pdf.rect(40, table_top - header_height, 515, header_height, fill=False, stroke=True)

    headers = [
        ("S.No", 53, "center"),
        ("Qty", 79, "center"),
        ("Product Description", 98, "left"),
        ("MRP", 314, "right"),
        ("Price", 358, "right"),
        ("Unit", 378, "center"),
        ("Inc %", 415, "center"),
        ("Disc %", 465, "center"),
        ("Total (Rs.)", 548, "right")
    ]

    pdf.setFont("Helvetica-Bold", 9)
    pdf.setFillColorRGB(0.15, 0.18, 0.25)

    for title, x_pos, align in headers:
        if align == "center":
            pdf.drawCentredString(x_pos, table_top - 14, title)
        elif align == "right":
            pdf.drawRightString(x_pos, table_top - 14, title)
        else:
            pdf.drawString(x_pos, table_top - 14, title)

    # =====================================
    # TABLE ROWS
    # =====================================
    current_y = table_top - header_height - 13
    serial = 1

    for item in normalized_items:
        wrapped_product = textwrap.wrap(item["name"], width=28) or ["Item"]
        lines_count = len(wrapped_product)
        row_height = 16 if lines_count <= 1 else (lines_count * 11 + 5)

        if current_y - row_height < 90:
            pdf.showPage()
            current_y = 800
            pdf.setFont("Helvetica", 8.5)

        if serial % 2 == 0:
            pdf.setFillColorRGB(0.98, 0.98, 0.99)
            pdf.rect(40, current_y - row_height + 11, 515, row_height, fill=True, stroke=False)

        pdf.setFont("Helvetica", 8.5)
        pdf.setFillColorRGB(0.15, 0.15, 0.15)

        # 1. S.No
        pdf.drawCentredString(53, current_y, str(serial))

        # 2. Qty
        pdf.setFont("Helvetica-Bold", 8.5)
        pdf.drawCentredString(79, current_y, str(item["quantity"]))
        pdf.setFont("Helvetica", 8.5)

        # 3. Product Description
        yy = current_y
        for line in wrapped_product:
            pdf.drawString(98, yy, line)
            yy -= 11

        # 4. MRP
        mrp_val = float(item.get("mrp", 0))
        pdf.drawRightString(314, current_y, f"{mrp_val:,.1f}" if mrp_val > 0 else "-")

        # 5. Price
        price_val = float(item.get("price", 0))
        pdf.drawRightString(358, current_y, f"{price_val:,.2f}")

        # 6. Unit
        pdf.drawCentredString(378, current_y, str(item.get("unit", "Pcs") or "Pcs"))

        # 7. Increase %
        inc_val = float(item.get("increase", 0) or 0)
        inc_str = f"+{int(inc_val) if inc_val.is_integer() else inc_val}%" if inc_val > 0 else "-"
        pdf.drawCentredString(415, current_y, inc_str)

        # 8. Discount %
        discount_value = float(item.get("discount", 0) or 0)
        if discount_value > 0:
            disc_base = item.get("discount_base", "Price")
            disc_str = f"-{int(discount_value) if discount_value.is_integer() else discount_value}% ({disc_base})"
        else:
            disc_str = "-"
        pdf.drawCentredString(465, current_y, disc_str)

        # 9. Total
        total_val = float(item.get("total", 0))
        pdf.setFont("Helvetica-Bold", 8.5)
        pdf.drawRightString(548, current_y, f"{total_val:,.2f}")
        pdf.setFont("Helvetica", 8.5)

        # Bottom row divider line
        pdf.setStrokeColorRGB(0.9, 0.91, 0.94)
        pdf.setLineWidth(0.5)
        pdf.line(40, current_y - row_height + 11, 555, current_y - row_height + 11)

        current_y -= row_height
        serial += 1

    # Table outer border
    table_bottom = current_y + 11
    pdf.setStrokeColorRGB(0.75, 0.78, 0.84)
    pdf.setLineWidth(0.8)
    pdf.rect(40, table_bottom, 515, (table_top - table_bottom), fill=False, stroke=True)

    # Vertical Column Divider Lines
    v_dividers = [65, 92, 270, 318, 362, 395, 435, 495]
    pdf.setStrokeColorRGB(0.88, 0.89, 0.92)
    pdf.setLineWidth(0.5)
    for vx in v_dividers:
        pdf.line(vx, table_top, vx, table_bottom)

    # Summary Section
    summary_y = table_bottom - 16
    if note and note.strip():
        pdf.setFont("Helvetica-Bold", 8.5)
        pdf.setFillColorRGB(0.2, 0.2, 0.2)
        pdf.drawString(45, summary_y - 2, f"Note / Remarks: {note.strip()}")

    total_box_width = 190
    total_box_height = 30
    total_box_x = 365
    total_box_y = summary_y - total_box_height + 10

    pdf.setFillColorRGB(0.94, 0.96, 1.0)
    pdf.rect(total_box_x, total_box_y, total_box_width, total_box_height, fill=True, stroke=False)
    pdf.setStrokeColorRGB(0.2, 0.35, 0.65)
    pdf.setLineWidth(1)
    pdf.rect(total_box_x, total_box_y, total_box_width, total_box_height, fill=False, stroke=True)

    pdf.setFont("Helvetica-Bold", 12)
    pdf.setFillColorRGB(0.1, 0.2, 0.5)
    pdf.drawRightString(total_box_x + total_box_width - 10, total_box_y + 9, f"Grand Total:  Rs. {grand_total:,.2f}")

    # Mandatory Footer
    footer_line_y = total_box_y - 12
    footer_text_y = footer_line_y - 12

    pdf.setStrokeColorRGB(0.85, 0.88, 0.92)
    pdf.setLineWidth(0.5)
    pdf.line(40, footer_line_y, 555, footer_line_y)

    pdf.setFont("Helvetica", 8)
    pdf.setFillColorRGB(0.35, 0.35, 0.35)
    pdf.drawString(40, footer_text_y, "GST as per applicable. Order against PO.")

    pdf.setFont("Helvetica-Bold", 8)
    pdf.setFillColorRGB(0.35, 0.35, 0.35)
    pdf.drawRightString(555, footer_text_y, "Powered by wokdens.com")

    pdf.save()

    # Guarantee invoice is saved strictly to Pen Drive storage
    pd_dir = PENDRIVE_DIR or get_pen_drive_dir()
    if pd_dir and os.path.isdir(pd_dir):
        pd_inv_dir = os.path.join(pd_dir, "invoices")
        os.makedirs(pd_inv_dir, exist_ok=True)
        pd_file_path = os.path.join(pd_inv_dir, os.path.basename(path))
        if os.path.abspath(path).lower() != os.path.abspath(pd_file_path).lower():
            try:
                shutil.copy2(path, pd_file_path)
            except Exception:
                pass

    if open_file:
        open_pdf_file(path)

    return path



class InvoiceUI:
    _saved_state = None
    

    def __init__(self, parent, app=None):

        self.parent = parent
        self.app = app
        self.editing_invoice_id = None
        self.editing_invoice_number = None
        self.original_invoice_total = 0.0
        self.cart_items = []
        self.editing_cart_index = None

        self.frame = tk.Frame(parent)

        self.frame.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=5
        )

        style = ttk.Style()
        style.configure("TCombobox", font=("Arial", 11, "bold"))
        style.configure("Treeview.Heading", font=("Arial", 11, "bold"))
        style.configure("Treeview", font=("Arial", 11), rowheight=28)

        style.configure(
            "Vertical.TScrollbar",
            gripcount=0,
            background="gray",
            darkcolor="gray",
            lightcolor="gray",
            troughcolor="#d9d9d9",
            bordercolor="#d9d9d9",
            arrowcolor="black"
        )

        self.selected_cell_value = ""

        # =========================
        # EDIT MODE BANNER (Hidden by default)
        # =========================
        self.edit_banner = tk.Frame(
            self.frame,
            bg="#fff3cd",
            relief="solid",
            bd=1,
            padx=10,
            pady=5
        )
        self.edit_banner_label = tk.Label(
            self.edit_banner,
            text="⚠️ EDITING INVOICE",
            font=("Arial", 10, "bold"),
            fg="#856404",
            bg="#fff3cd"
        )
        self.edit_banner_label.pack(side="left", padx=5)

        cancel_edit_btn = tk.Button(
            self.edit_banner,
            text="✕ Cancel Edit (Return to New Bill)",
            command=self.cancel_invoice_edit,
            bg="#dc3545",
            fg="white",
            activebackground="#c82333",
            relief="raised",
            bd=2,
            padx=10,
            pady=2,
            font=("Arial", 9, "bold")
        )
        cancel_edit_btn.pack(side="right", padx=5)

        # =========================
        # 1. CUSTOMER SECTION
        # =========================

        self.customer_frame = customer_frame = tk.Frame(self.frame)
        customer_frame.pack(
            fill="x",
            padx=4,
            pady=(2, 4)
        )

        tk.Label(
            customer_frame,
            text="Customer Name:",
            font=("Arial", 12, "bold")
        ).pack(
            side="left",
            padx=(4, 6)
        )

        self.customer_combo = AutocompleteCombobox(
            customer_frame,
            width=28
        )
        self.customer_combo.entry.config(font=("Arial", 11, "bold"))
        self.customer_combo.listbox.config(font=("Arial", 11))
        self.customer_combo.pack(
            side="left",
            fill="x",
            expand=True,
            padx=4,
            ipady=3
        )

        self.refresh_customers()

        def apply_entry_focus_style(widget):
            """Adds crisp high-visibility blue border & soft light blue tint on focus."""
            widget.config(
                relief="solid",
                bd=1,
                highlightthickness=1,
                highlightbackground="#ced4da",
                highlightcolor="#2563eb",
                bg="#ffffff"
            )
            def _on_f_in(e):
                try:
                    widget.config(
                        highlightthickness=2,
                        highlightbackground="#2563eb",
                        highlightcolor="#2563eb",
                        bg="#f0f7ff"
                    )
                    widget.selection_range(0, tk.END)
                except Exception:
                    pass
            def _on_f_out(e):
                try:
                    widget.config(
                        highlightthickness=1,
                        highlightbackground="#ced4da",
                        highlightcolor="#ced4da",
                        bg="#ffffff"
                    )
                except Exception:
                    pass
            widget.bind("<FocusIn>", _on_f_in, add="+")
            widget.bind("<FocusOut>", _on_f_out, add="+")

        def apply_button_focus_style(button, ring_color="#ff9800", trigger_func=None):
            """
            Adds a bright high-visibility glowing ring border on focus to Buttons,
            and binds Enter / Space to execute trigger_func or invoke the button.
            """
            button.config(
                relief="raised",
                bd=2,
                highlightthickness=2,
                highlightbackground="#ced4da",
                highlightcolor=ring_color
            )
            def _on_btn_f_in(e):
                try:
                    button.config(
                        relief="solid",
                        highlightthickness=3,
                        highlightbackground=ring_color,
                        highlightcolor=ring_color
                    )
                except Exception:
                    pass
            def _on_btn_f_out(e):
                try:
                    button.config(
                        relief="raised",
                        highlightthickness=2,
                        highlightbackground="#ced4da",
                        highlightcolor=ring_color
                    )
                except Exception:
                    pass
            def _on_key_activate(e):
                if trigger_func:
                    trigger_func()
                else:
                    button.invoke()
                return "break"

            button.bind("<FocusIn>", _on_btn_f_in, add="+")
            button.bind("<FocusOut>", _on_btn_f_out, add="+")
            button.bind("<Return>", _on_key_activate)
            button.bind("<KP_Enter>", _on_key_activate)
            button.bind("<space>", _on_key_activate)

        self._apply_entry_focus = apply_entry_focus_style
        self._apply_btn_focus = apply_button_focus_style

        add_customer_btn = tk.Button(
            customer_frame,
            text="+ Add Customer",
            command=self.open_customer_popup,
            bg="#f4a300",
            fg="black",
            activebackground="#d68e00",
            relief="raised",
            bd=2,
            padx=10,
            pady=3,
            font=("Arial", 10, "bold")
        )
        add_customer_btn.pack(side="left", padx=4)
        apply_button_focus_style(add_customer_btn, ring_color="#0066cc", trigger_func=self.open_customer_popup)

        clear_invoice_btn = tk.Button(
            customer_frame,
            text="🧹 Clear / New Bill (Ctrl+N)",
            bg="#e9ecef",
            fg="#495057",
            activebackground="#dde2e6",
            relief="raised",
            bd=2,
            padx=10,
            pady=3,
            font=("Arial", 10, "bold"),
            command=self.clear_invoice
        )
        clear_invoice_btn.pack(side="left", padx=4)
        apply_button_focus_style(clear_invoice_btn, ring_color="#dc3545", trigger_func=self.clear_invoice)

        # =========================
        # 2. PRODUCT SECTION (Compact & Fast)
        # =========================

        product_frame = tk.LabelFrame(
            self.frame,
            text="Add Product to Bill",
            font=("Arial", 10, "bold"),
            padx=10,
            pady=6
        )
        product_frame.pack(
            fill="x",
            padx=4,
            pady=(2, 4)
        )

        for col in (1, 3, 5, 7):
            product_frame.grid_columnconfigure(col, weight=1)

        # Row 0: Product Search Dropdown & Live Stock Badge
        tk.Label(
            product_frame,
            text="Product:",
            font=("Arial", 11, "bold")
        ).grid(row=0, column=0, padx=6, pady=3, sticky="w")

        self.product_combo = AutocompleteCombobox(
            product_frame,
            width=32
        )
        self.product_combo.entry.config(font=("Arial", 11, "bold"))
        self.product_combo.listbox.config(font=("Arial", 11))
        self.product_combo.grid(
            row=0,
            column=1,
            columnspan=5,
            padx=4,
            pady=3,
            sticky="ew"
        )

        # Live Stock Indicator Badge
        self.stock_badge = tk.Label(
            product_frame,
            text="Stock: --",
            font=("Arial", 10, "bold"),
            fg="#6c757d",
            bg="#e9ecef",
            padx=8,
            pady=2,
            relief="groove"
        )
        self.stock_badge.grid(
            row=0,
            column=6,
            columnspan=2,
            padx=6,
            pady=3,
            sticky="e"
        )

        products = get_product_names()
        self.product_combo.set_completion_list(products)

        self.product_combo.bind("<KeyRelease>", lambda e: self.autofill_product_details(focus_qty=False))
        self.product_combo.bind("<<ComboboxSelected>>", lambda e: self.autofill_product_details(focus_qty=True))
        self.product_combo.bind("<FocusOut>", lambda e: self.autofill_product_details(focus_qty=False))
        self.product_combo.entry.bind("<Return>", self.on_product_enter_pressed)

        # Row 1: Qty, MRP, Price, Unit
        tk.Label(product_frame, text="Qty:", font=("Arial", 10, "bold")).grid(row=1, column=0, padx=4, pady=3, sticky="w")
        self.qty_entry = tk.Entry(product_frame, width=6, font=("Arial", 11, "bold"), justify="center")
        self.qty_entry.grid(row=1, column=1, padx=4, pady=3, ipady=2, sticky="ew")
        self._apply_entry_focus(self.qty_entry)

        tk.Label(product_frame, text="MRP:", font=("Arial", 10, "bold")).grid(row=1, column=2, padx=4, pady=3, sticky="w")
        self.mrp_entry = tk.Entry(product_frame, width=8, state="readonly", font=("Arial", 11, "bold"), justify="center")
        self.mrp_entry.grid(row=1, column=3, padx=4, pady=3, ipady=2, sticky="ew")

        tk.Label(product_frame, text="Price:", font=("Arial", 10, "bold")).grid(row=1, column=4, padx=4, pady=3, sticky="w")
        self.price_entry = tk.Entry(product_frame, width=8, font=("Arial", 11, "bold"), justify="center")
        self.price_entry.grid(row=1, column=5, padx=4, pady=3, ipady=2, sticky="ew")
        self._apply_entry_focus(self.price_entry)

        tk.Label(product_frame, text="Unit:", font=("Arial", 10, "bold")).grid(row=1, column=6, padx=4, pady=3, sticky="w")
        self.unit_entry = tk.Entry(product_frame, width=6, state="readonly", font=("Arial", 11, "bold"), justify="center")
        self.unit_entry.grid(row=1, column=7, padx=4, pady=3, ipady=2, sticky="ew")

        # Row 2: Increase %, Discount %, Base, Add To Cart Button
        self.discount_base_var = tk.StringVar(value="Price")

        tk.Label(product_frame, text="Inc %:", font=("Arial", 10, "bold")).grid(row=2, column=0, padx=4, pady=3, sticky="w")
        self.increase_entry = tk.Entry(product_frame, width=6, font=("Arial", 11, "bold"), justify="center")
        self.increase_entry.insert(0, "0")
        self.increase_entry.grid(row=2, column=1, padx=4, pady=3, ipady=2, sticky="ew")
        self._apply_entry_focus(self.increase_entry)

        tk.Label(product_frame, text="Disc %:", font=("Arial", 10, "bold")).grid(row=2, column=2, padx=4, pady=3, sticky="w")
        self.discount_entry = tk.Entry(product_frame, width=6, font=("Arial", 11, "bold"), justify="center")
        self.discount_entry.insert(0, "0")
        self.discount_entry.grid(row=2, column=3, padx=4, pady=3, ipady=2, sticky="ew")
        self._apply_entry_focus(self.discount_entry)

        tk.Label(product_frame, text="Base:", font=("Arial", 10, "bold")).grid(row=2, column=4, padx=4, pady=3, sticky="w")
        self.discount_base_label = tk.Label(
            product_frame,
            textvariable=self.discount_base_var,
            font=("Arial", 10, "bold"),
            fg="#0066cc",
            anchor="w"
        )
        self.discount_base_label.grid(row=2, column=5, padx=4, pady=3, sticky="w")

        self.add_btn = tk.Button(
            product_frame,
            text="➕ Add to Bill (Enter)",
            command=self.add_to_cart,
            bg="#28a745",
            fg="white",
            activebackground="#218838",
            relief="raised",
            bd=2,
            padx=14,
            pady=3,
            font=("Arial", 10, "bold")
        )
        self.add_btn.grid(row=2, column=6, columnspan=2, padx=6, pady=3, sticky="e")
        self._apply_btn_focus(self.add_btn, ring_color="#ffcc00", trigger_func=self.add_to_cart)

        # =========================
        # TALLY SEAMLESS KEYBOARD NAVIGATION LOOP
        # =========================
        self.customer_combo.entry.bind("<Return>", self.on_customer_enter_pressed)
        self.customer_combo.bind("<<ComboboxSelected>>", self.on_customer_enter_pressed)

        # Enter advances to next field seamlessly
        self.qty_entry.bind(
            "<Return>",
            lambda e: (self.price_entry.focus_set(), self.price_entry.selection_range(0, tk.END))
        )
        self.price_entry.bind(
            "<Return>",
            lambda e: (self.increase_entry.focus_set(), self.increase_entry.selection_range(0, tk.END))
        )
        self.increase_entry.bind(
            "<Return>",
            lambda e: (self.discount_entry.focus_set(), self.discount_entry.selection_range(0, tk.END))
        )
        self.discount_entry.bind(
            "<Return>",
            lambda e: self.add_to_cart()
        )



        # =========================
        # 3. CART TABLE WITH INTERNAL SCROLLBAR
        # =========================

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
            padx=4,
            pady=4
        )

        columns = (
            "S.No",
            "Qty",
            "Product",
            "MRP",
            "Price",
            "Unit",
            "Inc %",
            "Disc %",
            "Base",
            "Total",
            "Edit",
            "Delete"
        )

        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse"
        )

        for col in columns:
            self.tree.heading(col, text=col)
            width = 100
            minwidth = 50
            if col == "S.No":
                width = 38
                minwidth = 28
            elif col == "Qty":
                width = 45
                minwidth = 35
            elif col == "Product":
                width = 270
                minwidth = 140
            elif col in ("MRP", "Price"):
                width = 75
                minwidth = 50
            elif col == "Unit":
                width = 48
                minwidth = 35
            elif col in ("Inc %", "Disc %"):
                width = 58
                minwidth = 40
            elif col == "Base":
                width = 65
                minwidth = 45
            elif col == "Total":
                width = 85
                minwidth = 60
            elif col in ("Edit", "Delete"):
                width = 52
                minwidth = 38

            self.tree.column(
                col,
                width=width,
                minwidth=minwidth,
                anchor="center" if col != "Product" else "w"
            )


        tree_scroll = ttk.Scrollbar(
            table_frame,
            orient="vertical",
            command=self.tree.yview
        )
        self.tree.configure(yscrollcommand=tree_scroll.set)

        self.tree.pack(side="left", fill="both", expand=True)
        tree_scroll.pack(side="right", fill="y")

        self.tree.tag_configure("evenrow", background="#ffffff")
        self.tree.tag_configure("oddrow", background="#f8f9fa")

        self.tree.bind(
            "<Button-1>",
            self.handle_table_click
        )
        # Table Keyboard & Mouse Shortcuts (Tally Style)
        self.tree.bind("<Double-1>", lambda e: self._edit_selected_cart_row())
        self.tree.bind("<Delete>", lambda e: self._delete_selected_cart_row())
        self.tree.bind("<BackSpace>", lambda e: self._delete_selected_cart_row())
        self.tree.bind("<Return>", lambda e: self._edit_selected_cart_row())



        # =========================
        # 4. BOTTOM SUMMARY & ACTIONS
        # =========================

        bottom_frame = tk.Frame(
            self.frame,
            bg="#f8f9fa",
            relief="groove",
            borderwidth=1,
            padx=10,
            pady=6
        )
        bottom_frame.pack(
            fill="x",
            padx=4,
            pady=(2, 4),
            side="bottom"
        )

        # Line 1: Items Count, Grand Total, Paid Amount, Pending, Note (ALL in ONE Line)
        line1 = tk.Frame(bottom_frame, bg="#f8f9fa")
        line1.pack(fill="x", pady=2)

        # Wholesale Quantity Counter Badge
        self.items_count_label = tk.Label(
            line1,
            text="Items: 0 | Qty: 0",
            font=("Arial", 10, "bold"),
            fg="#495057",
            bg="#e9ecef",
            padx=6,
            pady=2,
            relief="groove"
        )

        self.items_count_label.pack(side="left", padx=(4, 10))

        self.total_label = tk.Label(
            line1,
            text="Grand Total: ₹ 0",
            font=("Arial", 14, "bold"),
            fg="#5634f0",
            bg="#f8f9fa"
        )
        self.total_label.pack(side="left", padx=(4, 12))

        tk.Label(
            line1,
            text="Paid Amount:",
            font=("Arial", 11, "bold"),
            bg="#f8f9fa"
        ).pack(side="left", padx=(8, 4))

        self.paid_entry = tk.Entry(
            line1,
            width=11,
            font=("Arial", 11, "bold"),
            justify="center"
        )
        self.paid_entry.insert(0, "0")
        self.paid_entry.pack(side="left", padx=4)
        self._apply_entry_focus(self.paid_entry)

        self.paid_entry.bind(
            "<KeyRelease>",
            self.on_paid_changed
        )
        self.paid_entry.bind(
            "<FocusOut>",
            lambda e: self.update_pending()
        )
        self.paid_entry.bind(
            "<Return>",
            lambda e: (self.note_text.focus_set(), self.note_text.selection_range(0, tk.END))
        )

        self.pending_label = tk.Label(
            line1,
            text="Pending: ₹ 0",
            font=("Arial", 12, "bold"),
            fg="#28a745",
            bg="#f8f9fa"
        )
        self.pending_label.pack(side="left", padx=(12, 12))

        tk.Label(
            line1,
            text="Note:",
            font=("Arial", 11, "bold"),
            bg="#f8f9fa"
        ).pack(side="left", padx=(8, 4))

        self.note_text = tk.Entry(
            line1,
            font=("Arial", 10),
            width=26
        )
        self.note_text.pack(side="left", fill="x", expand=True, padx=4)
        self._apply_entry_focus(self.note_text)
        self.note_text.bind(
            "<Return>",
            lambda e: self.save_thermal_btn.focus_set()
        )

        # Line 2: Save Invoice Buttons (Thermal & A4), Clear Button & Branding
        line2 = tk.Frame(bottom_frame, bg="#f8f9fa")
        line2.pack(fill="x", pady=(5, 2))

        # Default 80mm Thermal Receipt Button (Primary - Indigo Accent)
        self.save_thermal_btn = tk.Button(
            line2,
            text="🖨️ Save & Print 80mm Receipt (Ctrl+P)",
            command=lambda: self.save_invoice(format_type="thermal"),
            fg="white",
            bg="#5634f0",
            activebackground="#3f22c2",
            relief="raised",
            bd=3,
            padx=14,
            pady=4,
            font=("Arial", 10, "bold")
        )
        self.save_thermal_btn.pack(side="left", padx=(4, 6))
        self._apply_btn_focus(self.save_thermal_btn, ring_color="#ffcc00", trigger_func=lambda: self.save_invoice(format_type="thermal"))

        # Secondary A4 PDF Button (Emerald Accent)
        self.save_a4_btn = tk.Button(
            line2,
            text="📄 Save & Print A4 PDF (Ctrl+J)",
            command=lambda: self.save_invoice(format_type="a4"),
            fg="white",
            bg="#28a745",
            activebackground="#218838",
            relief="raised",
            bd=3,
            padx=12,
            pady=4,
            font=("Arial", 10, "bold")
        )
        self.save_a4_btn.pack(side="left", padx=4)
        self._apply_btn_focus(self.save_a4_btn, ring_color="#ffcc00", trigger_func=lambda: self.save_invoice(format_type="a4"))

        # Recall Last Bill Button (Amber Accent)
        self.recall_btn = tk.Button(
            line2,
            text="↺ Recall Last Bill (Ctrl+Z)",
            command=self.recall_last_bill,
            fg="#7c2d12",
            bg="#fef3c7",
            activebackground="#fde68a",
            relief="raised",
            bd=2,
            padx=10,
            pady=4,
            font=("Arial", 10, "bold")
        )
        self.recall_btn.pack(side="left", padx=5)
        self._apply_btn_focus(self.recall_btn, ring_color="#d97706", trigger_func=self.recall_last_bill)

        self.clear_btn = tk.Button(
            line2,
            text="🧹 Clear / New Bill (Ctrl+N)",
            command=self.clear_invoice,
            fg="#495057",
            bg="#e9ecef",
            activebackground="#dde2e6",
            relief="raised",
            bd=2,
            padx=10,
            pady=4,
            font=("Arial", 10, "bold")
        )
        self.clear_btn.pack(side="left", padx=5)
        self._apply_btn_focus(self.clear_btn, ring_color="#dc3545", trigger_func=self.clear_invoice)

        branding_label = tk.Label(
            line2,
            text="⚡ Powered by wokdens.com",
            font=("Arial", 9, "italic"),
            fg="#888888",
            bg="#f8f9fa"
        )
        branding_label.pack(side="right", padx=10)

        self.auto_fill_paid = True
        self.restore_state()
        self._bind_tally_shortcuts()




    def _bind_tally_shortcuts(self):
        """Binds global keyboard shortcuts for fast POS billing."""
        try:
            top = self.frame.winfo_toplevel()
            # Ctrl+P: Print / Save 80mm Thermal Receipt (Default)
            for seq in ("<Control-p>", "<Control-P>", "<Control-Key-p>", "<Control-Key-P>"):
                top.bind_all(seq, lambda e: self._handle_shortcut_save("thermal"))
            # Ctrl+J: Save & Generate A4 PDF
            for seq in ("<Control-j>", "<Control-J>", "<Control-Key-j>", "<Control-Key-J>"):
                top.bind_all(seq, lambda e: self._handle_shortcut_save("a4"))
            # Ctrl+N: Clear / New Bill
            for seq in ("<Control-n>", "<Control-N>", "<Control-Key-n>", "<Control-Key-N>"):
                top.bind_all(seq, lambda e: self._handle_shortcut_clear())
            # Ctrl+Z: Recall Last Bill
            for seq in ("<Control-z>", "<Control-Z>", "<Control-Key-z>", "<Control-Key-Z>"):
                top.bind_all(seq, lambda e: self._handle_shortcut_recall())
        except Exception:
            pass

    def _handle_shortcut_save(self, format_type):
        self.save_invoice(format_type=format_type)
        return "break"

    def _handle_shortcut_clear(self):
        self.clear_invoice()
        return "break"

    def _handle_shortcut_recall(self):
        self.recall_last_bill()
        return "break"




    # =========================
    # CUSTOMERS
    # =========================

    
    def refresh_customers(self):

        self.customer_list = (
            get_customer_names_with_phone()
        )

        self.customer_combo.set_completion_list(
            self.customer_list
        )

    def open_customer_popup(self):

        CustomerPopup(
            self.frame,
            self.refresh_customers
        )
        
    def _on_mousewheel(self, event):

        self.canvas.yview_scroll(
            int(-1 * (event.delta / 120)),
            "units"
        )

    # =========================
    # AUTOFILL
    # =========================

    def on_customer_enter_pressed(self, event=None):
        """Move focus seamlessly from customer search to product search."""
        self.product_combo.entry.focus_set()
        self.product_combo.entry.selection_range(0, tk.END)

    def on_product_enter_pressed(self, event=None):
        """Product Enter key: autofill details and advance focus into Qty."""
        self.autofill_product_details(focus_qty=True)

    def autofill_product_details(
        self,
        event=None,
        focus_qty=False
    ):

        selected = (
            self.product_combo.get()
        )

        if not selected or not selected.strip():
            return

        product = get_product_complete_details(selected)
        if not product:
            return

        self.mrp_entry.config(
            state="normal"
        )

        self.mrp_entry.delete(
            0,
            tk.END
        )

        self.mrp_entry.insert(
            0,
            str(product[2] or 0)
        )

        self.mrp_entry.config(
            state="readonly"
        )

        self.price_entry.delete(
            0,
            tk.END
        )

        self.price_entry.insert(
            0,
            str(product[3])
        )

        unit = product[5] if (len(product) > 5 and product[5] and str(product[5]).strip()) else "Pcs"
        self.unit_entry.config(
            state="normal"
        )

        self.unit_entry.delete(
            0,
            tk.END
        )

        self.unit_entry.insert(
            0,
            unit
        )

        self.unit_entry.config(
            state="readonly"
        )


        if len(product) > 6 and product[6]:
            self.discount_base_var.set(product[6])
        else:
            self.discount_base_var.set("Price")

        # Update Live Stock Indicator Badge
        if len(product) > 4:
            stock = product[4]
            unit = product[5] if len(product) > 5 else "Pcs"
            if hasattr(self, "stock_badge"):
                if stock > 10:
                    self.stock_badge.config(
                        text=f"Stock: {stock} {unit}",
                        fg="#155724",
                        bg="#d4edda"
                    )
                elif 1 <= stock <= 10:
                    self.stock_badge.config(
                        text=f"Low Stock: {stock} {unit}",
                        fg="#856404",
                        bg="#fff3cd"
                    )
                else:
                    self.stock_badge.config(
                        text=f"Out of Stock (0 {unit})",
                        fg="#721c24",
                        bg="#f8d7da"
                    )


        # Pre-fill default Qty = 1 if empty
        if not self.qty_entry.get().strip():
            self.qty_entry.delete(0, tk.END)
            self.qty_entry.insert(0, "1")

        # Only focus into Qty if triggered by Enter or dropdown selection
        if focus_qty:
            self.qty_entry.focus_set()
            self.qty_entry.selection_range(0, tk.END)


    # =========================
    # ADD TO CART
    # =========================

    def add_to_cart(self):

        selected_product = (
            self.product_combo.get()
        )

        if not selected_product or not selected_product.strip():

            messagebox.showerror(
                "Error",
                "Please select a product first.",
                parent=self.frame.winfo_toplevel()
            )

            self.product_combo.entry.focus_set()
            return


        product = get_product_complete_details(selected_product)
        if not product:
            messagebox.showerror(
                "Product Not Found",
                "The selected product is not available in inventory."
            )
            return

        product_name = product[1]

        try:
            quantity = int(self.qty_entry.get())
            if quantity <= 0:
                messagebox.showerror(
                    "Invalid Quantity",
                    "Quantity must be a positive whole number greater than 0."
                )
                return
        except ValueError:
            messagebox.showerror(
                "Invalid Quantity",
                "Please enter a valid whole number in Qty."
            )
            return

        try:
            custom_price = float(self.price_entry.get())
            if custom_price < 0:
                messagebox.showerror(
                    "Invalid Price",
                    "Price cannot be negative."
                )
                return
        except ValueError:
            messagebox.showerror(
                "Invalid Price",
                "Please enter a valid numeric value in Price."
            )
            return

        unit = self.unit_entry.get().strip()
        if not unit:
            unit = (product[5] if len(product) > 5 and product[5] else "Pcs")
            self.unit_entry.config(state="normal")
            self.unit_entry.delete(0, tk.END)
            self.unit_entry.insert(0, unit)
            self.unit_entry.config(state="readonly")

        try:
            increase = float(self.increase_entry.get().strip() or 0)
            if increase < 0:
                messagebox.showerror(
                    "Invalid Increase",
                    "Increase percentage cannot be negative.",
                    parent=self.frame.winfo_toplevel()
                )
                return
        except ValueError:
            messagebox.showerror(
                "Invalid Increase",
                "Please enter a valid numeric value in Inc %.",
                parent=self.frame.winfo_toplevel()
            )
            return

        try:
            discount = float(self.discount_entry.get().strip() or 0)
            if discount < 0 or discount > 100:
                messagebox.showerror(
                    "Invalid Discount",
                    "Discount must be between 0% and 100%.",
                    parent=self.frame.winfo_toplevel()
                )
                return
        except ValueError:
            messagebox.showerror(
                "Invalid Discount",
                "Please enter a valid numeric value in Disc %.",
                parent=self.frame.winfo_toplevel()
            )
            return

        discount_base = self.discount_base_var.get() or "Price"

        if quantity > product[4]:
            messagebox.showerror(
                "Out of Stock",
                f"Only {product[4]} units of this product are available in inventory.",
                parent=self.frame.winfo_toplevel()
            )
            return

        mrp = float(self.mrp_entry.get() or 0)
        base_price = mrp if discount_base == "MRP" else custom_price

        # Increase adds % to base price, Discount subtracts % from base price
        effective_price = base_price + (base_price * increase / 100.0) - (base_price * discount / 100.0)
        if effective_price < 0:
            effective_price = 0.0

        total = effective_price * quantity

        # IF CURRENTLY IN EDIT MODE -> UPDATE ROW IN PLACE (SAME ORDER / SERIAL NO)
        if self.editing_cart_index is not None and self.editing_cart_index < len(self.cart_items):
            item = {
                "product_id": product[0],
                "name": product_name,
                "quantity": quantity,
                "mrp": mrp,
                "price": custom_price,
                "unit": unit,
                "increase": increase,
                "discount": discount,
                "discount_base": discount_base,
                "total": total
            }
            self.cart_items[self.editing_cart_index] = item
            self.editing_cart_index = None
            self.add_btn.config(
                text="➕ Add to Bill (Enter)",
                bg="#28a745",
                activebackground="#218838"
            )
            self.refresh_cart_table()
            self.update_total()
            self.clear_inputs()
            self.product_combo.entry.focus_set()
            self.product_combo.entry.icursor(tk.END)
            return

        # Check if identical product is already in cart -> increase count
        existing_item = None
        for itm in self.cart_items:
            if (
                itm["product_id"] == product[0]
                and abs(itm["price"] - custom_price) < 0.001
                and abs(itm.get("increase", 0) - increase) < 0.001
                and abs(itm.get("discount", 0) - discount) < 0.001
                and itm.get("discount_base", "Price") == discount_base
            ):
                existing_item = itm
                break

        if existing_item:
            combined_qty = existing_item["quantity"] + quantity
            if combined_qty > product[4]:
                messagebox.showerror(
                    "Out of Stock",
                    f"Only {product[4]} {unit} available in stock.\nCart already has {existing_item['quantity']} {unit}.",
                    parent=self.frame.winfo_toplevel()
                )
                return

            existing_item["quantity"] = combined_qty
            existing_item["total"] = effective_price * combined_qty
            self.refresh_cart_table()
            self.update_total()
            self.clear_inputs()
            self.product_combo.entry.focus_set()
            self.product_combo.entry.icursor(tk.END)
            return

        item = {
            "product_id": product[0],
            "name": product_name,
            "quantity": quantity,
            "mrp": mrp,
            "price": custom_price,
            "unit": unit,
            "increase": increase,
            "discount": discount,
            "discount_base": discount_base,
            "total": total
        }

        self.cart_items.append(item)
        self.refresh_cart_table()
        self.update_total()
        self.clear_inputs()
        self.product_combo.entry.focus_set()
        self.product_combo.entry.icursor(tk.END)

    # =========================
    # UPDATE TOTAL
    # =========================

    def update_total(self):

        total = sum(
            item["total"]
            for item in self.cart_items
        )

        # Round off paisa values to nearest rupee
        rounded_total = round(total)

        # store for pending calculation
        self.rounded_total = rounded_total

        self.total_label.config(
            text=f"Grand Total: ₹ {rounded_total}"
        )

        # Live Wholesale Counter (Items & Physical Quantity)
        if hasattr(self, "items_count_label"):
            total_items = len(self.cart_items)
            total_qty = sum(int(item.get("quantity", 0)) for item in self.cart_items)
            self.items_count_label.config(
                text=f"Items: {total_items} | Qty: {total_qty}"
            )


        if self.auto_fill_paid:

            self.paid_entry.delete(
                0,
                tk.END
            )

            self.paid_entry.insert(
                0,
                str(rounded_total)
            )

        self.update_pending()

    # =========================
    # CLEAR
    # =========================

    def clear_inputs(self):

        self.editing_cart_index = None
        self.add_btn.config(
            text="➕ Add to Bill (Enter)",
            bg="#28a745",
            activebackground="#218838"
        )

        self.product_combo.set("")

        if hasattr(self, "stock_badge"):
            self.stock_badge.config(
                text="Stock: --",
                fg="#6c757d",
                bg="#e9ecef"
            )

        self.qty_entry.delete(
            0,
            tk.END
        )
        self.qty_entry.insert(0, "1")


        self.price_entry.delete(
            0,
            tk.END
        )

        self.mrp_entry.config(state="normal")
        self.mrp_entry.delete(0, tk.END)
        self.mrp_entry.config(state="readonly")

        self.unit_entry.config(state="normal")
        self.unit_entry.delete(
            0,
            tk.END
        )
        self.unit_entry.config(state="readonly")

        self.increase_entry.delete(
            0,
            tk.END
        )
        self.increase_entry.insert(
            0,
            "0"
        )

        self.discount_entry.delete(
            0,
            tk.END
        )

        self.discount_entry.insert(
            0,
            "0"
        )



    # =========================
    # EDIT & RECALL BILLING CONTROLS
    # =========================

    def _show_edit_banner(self):
        if not self.editing_invoice_id:
            return
        self.edit_banner_label.config(
            text=f"⚠️ EDITING INVOICE #{self.editing_invoice_number} (Original: ₹ {self.original_invoice_total:,.2f}) — Modify/Remove items, then Save to reconcile stock."
        )
        self.edit_banner.pack(fill="x", padx=4, pady=(2, 4), before=self.customer_frame)
        self.save_thermal_btn.config(
            text=f"💾 Update & Print 80mm (INV-{self.editing_invoice_number})",
            bg="#d97706"
        )
        self.save_a4_btn.config(
            text=f"📄 Update & Print A4 (INV-{self.editing_invoice_number})",
            bg="#059669"
        )

    def _hide_edit_banner(self):
        try:
            self.edit_banner.pack_forget()
        except Exception:
            pass
        self.editing_invoice_id = None
        self.editing_invoice_number = None
        self.original_invoice_total = 0.0
        try:
            self.save_thermal_btn.config(
                text="🖨️ Save & Print 80mm Receipt (Ctrl+P)",
                bg="#5634f0"
            )
            self.save_a4_btn.config(
                text="📄 Save & Print A4 PDF (Ctrl+J)",
                bg="#28a745"
            )
        except Exception:
            pass

    def load_invoice_for_editing(self, invoice_id, authorized=False):
        """Loads an existing invoice and its items into the cart for editing (Admin PIN required)."""
        if not authorized and not is_admin_mode():
            if not request_admin_pin(self.frame.winfo_toplevel(), f"edit Invoice #{invoice_id}"):
                return False

        inv_data = get_invoice_with_items(invoice_id)
        if not inv_data:
            messagebox.showerror(
                "Error",
                f"Invoice #{invoice_id} could not be found.",
                parent=self.frame.winfo_toplevel()
            )
            return False

        if inv_data.get("status") == "CANCELLED":
            messagebox.showwarning(
                "Cancelled Invoice",
                f"Invoice #{inv_data['invoice_number']} is CANCELLED and cannot be edited.",
                parent=self.frame.winfo_toplevel()
            )
            return False

        self.editing_invoice_id = inv_data["id"]
        self.editing_invoice_number = inv_data["invoice_number"]
        self.original_invoice_total = inv_data["total"]

        # Audit trail: document who opened this invoice for modification
        record_audit_log(
            "INVOICE_EDIT_LOADED",
            f"Invoice #{inv_data['invoice_number']} ({inv_data['customer_name']}) loaded into billing editor by Admin.",
            authorized_by="Admin PIN"
        )

        # Populate customer
        cust_name = inv_data["customer_name"]
        found_match = False
        if hasattr(self, "customer_list") and self.customer_list:
            for c_entry in self.customer_list:
                if c_entry.startswith(cust_name) or cust_name in c_entry:
                    self.customer_combo.set(c_entry)
                    found_match = True
                    break
        if not found_match:
            self.customer_combo.set(cust_name)

        # Populate note
        if hasattr(self.note_text, "delete"):
            self.note_text.delete(0, tk.END)
            self.note_text.insert(0, inv_data.get("note", ""))

        # Populate cart items
        self.cart_items = list(inv_data.get("items", []))
        self.refresh_cart_table()
        self.update_total()

        # Populate paid amount
        self.auto_fill_paid = False
        self.paid_entry.delete(0, tk.END)
        paid_val = inv_data.get("paid", 0.0)
        self.paid_entry.insert(0, str(int(paid_val) if float(paid_val).is_integer() else paid_val))
        self.update_pending()

        # Show edit banner and update button labels
        self._show_edit_banner()
        return True

    def cancel_invoice_edit(self, silent=False):
        """Cancels the current invoice edit and clears the cart back to a new bill."""
        if not self.editing_invoice_id:
            return
        if not silent:
            if not messagebox.askyesno(
                "Cancel Edit",
                f"Discard changes to Invoice #{self.editing_invoice_number} and return to a new bill?",
                parent=self.frame.winfo_toplevel()
            ):
                return
        self.clear_invoice()

    def recall_last_bill(self):
        """Recalls the most recent active invoice into the billing cart for quick editing (Admin PIN required)."""
        last_inv = get_last_active_invoice()
        if not last_inv:
            messagebox.showinfo(
                "No Invoices",
                "No recent active invoices found to recall.",
                parent=self.frame.winfo_toplevel()
            )
            return

        # Security: Only Admin can recall an invoice for editing
        if not is_admin_mode():
            if not request_admin_pin(self.frame.winfo_toplevel(), f"recall and edit Invoice #{last_inv['invoice_number']}"):
                return

        if self.cart_items:
            if not messagebox.askyesno(
                "Confirm Recall",
                f"Current cart has items.\n\nDiscard current cart and recall Invoice #{last_inv['invoice_number']} ({last_inv['customer_name']}, ₹ {last_inv['total']:,.2f}) for editing?",
                parent=self.frame.winfo_toplevel()
            ):
                return

        record_audit_log(
            "INVOICE_RECALLED",
            f"Recalled Invoice #{last_inv['invoice_number']} ({last_inv['customer_name']}) for editing.",
            authorized_by="Admin PIN"
        )
        self.load_invoice_for_editing(last_inv["id"], authorized=True)

    def clear_invoice(self):

        InvoiceUI._saved_state = None
        self._hide_edit_banner()

        self.cart_items.clear()

        for row in self.tree.get_children():
            self.tree.delete(row)

        self.customer_combo.set("")

        self.clear_inputs()

        self.paid_entry.delete(0, tk.END)
        self.paid_entry.insert(0, "0")

        self.note_text.delete(0, tk.END)

        self.update_total()

    def save_state(self):
        note_val = self.note_text.get().strip() if hasattr(self.note_text, "get") else ""
        InvoiceUI._saved_state = {
            "cart_items": list(self.cart_items),
            "customer_name": self.customer_combo.get(),
            "product_name": self.product_combo.get(),
            "qty": self.qty_entry.get(),
            "mrp": self.mrp_entry.get(),
            "price": self.price_entry.get(),
            "unit": self.unit_entry.get(),
            "increase": self.increase_entry.get(),
            "discount": self.discount_entry.get(),
            "discount_base": self.discount_base_var.get(),
            "paid_amount": self.paid_entry.get(),
            "note": note_val,
            "auto_fill_paid": self.auto_fill_paid,
            "rounded_total": getattr(self, "rounded_total", 0),
            "editing_invoice_id": self.editing_invoice_id,
            "editing_invoice_number": self.editing_invoice_number,
            "original_invoice_total": self.original_invoice_total
        }

    def restore_state(self):
        state = InvoiceUI._saved_state
        if not state:
            return

        self.cart_items = list(state["cart_items"])
        self.refresh_cart_table()

        self.customer_combo.set(state["customer_name"])
        self.product_combo.set(state["product_name"])

        self.qty_entry.delete(0, tk.END)
        self.qty_entry.insert(0, state["qty"])

        self.mrp_entry.config(state="normal")
        self.mrp_entry.delete(0, tk.END)
        self.mrp_entry.insert(0, state["mrp"])
        self.mrp_entry.config(state="readonly")

        self.price_entry.delete(0, tk.END)
        self.price_entry.insert(0, state["price"])

        self.unit_entry.config(state="normal")
        self.unit_entry.delete(0, tk.END)
        self.unit_entry.insert(0, state["unit"])
        self.unit_entry.config(state="readonly")

        self.increase_entry.delete(0, tk.END)
        self.increase_entry.insert(0, state.get("increase", "0"))

        self.discount_entry.delete(0, tk.END)
        self.discount_entry.insert(0, state["discount"])

        self.discount_base_var.set(state["discount_base"])

        self.auto_fill_paid = state["auto_fill_paid"]
        self.rounded_total = state["rounded_total"]
        self.total_label.config(text=f"Grand Total: ₹ {self.rounded_total}")

        self.paid_entry.delete(0, tk.END)
        self.paid_entry.insert(0, state["paid_amount"])

        self.note_text.delete(0, tk.END)
        self.note_text.insert(0, state.get("note", ""))

        if state.get("editing_invoice_id"):
            self.editing_invoice_id = state["editing_invoice_id"]
            self.editing_invoice_number = state.get("editing_invoice_number")
            self.original_invoice_total = state.get("original_invoice_total", 0.0)
            self._show_edit_banner()
        else:
            self._hide_edit_banner()

    def on_tab_leave(self):
        """Called when user switches tabs away from Invoice page."""
        self.save_state()

    def on_tab_enter(self):
        """Called when user switches tabs back to Invoice page."""
        self.restore_state()


        self.update_pending()

    # =========================
    # SAVE INVOICE
    # =========================

    # =========================
    # SAVE INVOICE & DUAL PDF GENERATION
    # =========================

    def save_invoice(self, format_type="thermal"):
        if not self.cart_items:
            messagebox.showerror(
                "Error",
                "Cart is empty",
                parent=self.frame.winfo_toplevel()
            )
            return

        try:
            paid_amount = float(self.paid_entry.get().strip() or 0)
        except ValueError:
            messagebox.showerror(
                "Invalid Amount",
                "Please enter a valid paid amount.",
                parent=self.frame.winfo_toplevel()
            )
            return

        note = self.note_text.get().strip() if hasattr(self.note_text, "get") else ""

        # compute and round grand total before saving
        grand_total_raw = sum(
            item["total"]
            for item in self.cart_items
        )
        grand_total = round(grand_total_raw)

        raw_customer = self.customer_combo.get().strip()
        customer_name = raw_customer.split(" (")[0].strip() if raw_customer else "Cash / Walk-in Customer"

        is_edit = (self.editing_invoice_id is not None)
        edit_inv_id = self.editing_invoice_id
        edit_inv_num = self.editing_invoice_number

        if is_edit:
            try:
                invoice_id = update_saved_invoice(
                    edit_inv_id,
                    customer_name,
                    self.cart_items,
                    grand_total,
                    paid_amount,
                    note
                )
            except ValueError as ve:
                messagebox.showerror(
                    "Stock Error",
                    str(ve),
                    parent=self.frame.winfo_toplevel()
                )
                return
            except Exception as ex:
                messagebox.showerror(
                    "Update Error",
                    f"Failed to update invoice: {str(ex)}",
                    parent=self.frame.winfo_toplevel()
                )
                return
        else:
            invoice_id = save_complete_invoice(
                customer_name,
                self.cart_items,
                grand_total,
                paid_amount,
                note
            )

        # Generate BOTH formats so both are always ready on disk
        # 1. 80mm Thermal Receipt (POS format for H80i / thermal printers)
        thermal_path = generate_thermal_receipt_pdf(
            invoice_number=invoice_id,
            customer_name=customer_name,
            items=self.cart_items,
            grand_total=grand_total,
            paid_amount=paid_amount,
            note=note,
            open_file=False
        )

        # 2. A4 Standard / Compact PDF (for WhatsApp sharing and standard printers)
        a4_path = generate_a4_invoice_pdf(
            invoice_number=invoice_id,
            customer_name=customer_name,
            items=self.cart_items,
            grand_total=grand_total,
            paid_amount=paid_amount,
            note=note,
            open_file=(format_type == "a4")
        )

        # Clean up any older PDF versions for this invoice number when editing
        if is_edit:
            try:
                clean_inv_str = str(invoice_id).replace("INV-", "").strip()
                search_dirs = [INVOICES_DIR]
                pd_dir = PENDRIVE_DIR or get_pen_drive_dir()
                if pd_dir and os.path.isdir(pd_dir):
                    search_dirs.append(os.path.join(pd_dir, "invoices"))
                current_bases = {os.path.basename(thermal_path), os.path.basename(a4_path)}
                for s_dir in set(search_dirs):
                    if s_dir and os.path.isdir(s_dir):
                        for f_name in os.listdir(s_dir):
                            if (f_name.startswith(f"INV-{clean_inv_str}_") or f_name == f"INV-{clean_inv_str}.pdf") and f_name not in current_bases:
                                try:
                                    os.remove(os.path.join(s_dir, f_name))
                                except Exception:
                                    pass
            except Exception:
                pass

        printed_direct = False
        direct_msg = ""
        if format_type == "thermal":
            from ui.thermal_printer import print_receipt_direct, find_thermal_printer
            t_printer = find_thermal_printer()
            if t_printer:
                ok, msg = print_receipt_direct(
                    invoice_number=invoice_id,
                    customer_name=customer_name,
                    items=self.cart_items,
                    grand_total=grand_total,
                    paid_amount=paid_amount,
                    note=note,
                    printer_name=t_printer
                )
                if ok:
                    printed_direct = True
                    direct_msg = f"\n• Printed directly to POS thermal printer ({t_printer})."
                else:
                    open_pdf_file(thermal_path)
            else:
                open_pdf_file(thermal_path)

        # Clear cart and reset form for the next customer
        self.cart_items = []
        self.refresh_cart_table()
        self.clear_inputs()
        self.customer_combo.set("")
        self.paid_entry.delete(0, tk.END)
        if hasattr(self.note_text, "delete"):
            self.note_text.delete(0, tk.END)
        self.update_total()
        self.customer_combo.entry.focus_set()

        if is_edit:
            self._hide_edit_banner()

        format_label = "80mm Thermal Receipt" if format_type == "thermal" else "A4 PDF"
        if is_edit:
            success_msg = (
                f"Invoice #{invoice_id} updated successfully!\n\n"
                f"• Stock reconciled automatically (returned previous quantities, deducted new).\n"
                f"• Generated: {format_label}{direct_msg}\n"
                f"• Both 80mm Thermal & A4 formats are stored and ready."
            )
        else:
            success_msg = (
                f"Invoice #{invoice_id} saved successfully!\n\n"
                f"• Generated: {format_label}{direct_msg}\n"
                f"• Both 80mm Thermal & A4 formats are stored and ready."
            )

        messagebox.showinfo(
            "Success",
            success_msg,
            parent=self.frame.winfo_toplevel()
        )

    def generate_pdf(self, invoice_number, customer_name, grand_total, paid_amount=0):
        """Backward compatibility wrapper"""
        note = self.note_text.get().strip() if hasattr(self.note_text, "get") else ""
        return generate_thermal_receipt_pdf(
            invoice_number=invoice_number,
            customer_name=customer_name,
            items=self.cart_items,
            grand_total=grand_total,
            paid_amount=paid_amount,
            note=note,
            open_file=True
        )



    def on_paid_changed(self, event=None):

        self.auto_fill_paid = False

        self.update_pending()

    def update_pending(self):

        try:
            paid = float(self.paid_entry.get())
        except Exception:
            paid = 0.0

        rounded_total = getattr(self, "rounded_total", round(sum(item["total"] for item in self.cart_items) if self.cart_items else 0))

        pending_amount = rounded_total - paid

        # display as integer if whole rupee, else keep float
        if float(pending_amount).is_integer():
            pending_display = int(pending_amount)
        else:
            pending_display = pending_amount

        if pending_amount > 0:
            self.pending_label.config(
                text=f"Pending: ₹ {pending_display}",
                fg="#d9534f"
            )
        else:
            self.pending_label.config(
                text=f"Pending: ₹ {pending_display}",
                fg="#28a745"
            )

        
    def handle_table_click(self, event):

        region = self.tree.identify(
            "region",
            event.x,
            event.y
        )

        if region != "cell":
            return

        column = self.tree.identify_column(
            event.x
        )

        item = self.tree.identify_row(
            event.y
        )

        if not item:
            return

        column_number = int(
            column.replace("#", "")
        )

        # EDIT COLUMN
        if column_number == 11:

            self.edit_cart_item(item)

        # DELETE COLUMN
        elif column_number == 12:

            self.delete_cart_item(item)


    def delete_cart_item(self, item):

        index = self.tree.index(item)

        self.tree.delete(item)

        if index < len(self.cart_items):

            del self.cart_items[index]

        if self.editing_cart_index == index:
            self.clear_inputs()
        elif self.editing_cart_index is not None and self.editing_cart_index > index:
            self.editing_cart_index -= 1

        self.refresh_cart_table()

        self.update_total()


    def edit_cart_item(self, item):

        index = self.tree.index(item)

        if index >= len(self.cart_items):
            return

        self.editing_cart_index = index
        cart_item = self.cart_items[index]

        self.product_combo.set(
            cart_item["name"]
        )

        self.qty_entry.delete(0, tk.END)

        self.qty_entry.insert(
            0,
            cart_item["quantity"]
        )

        self.price_entry.delete(
            0,
            tk.END
        )

        self.price_entry.insert(
            0,
            cart_item["price"]
        )

        self.mrp_entry.config(
            state="normal"
        )

        self.mrp_entry.delete(
            0,
            tk.END
        )

        self.mrp_entry.insert(
            0,
            cart_item.get("mrp", 0)
        )

        self.mrp_entry.config(
            state="readonly"
        )

        self.unit_entry.config(
            state="normal"
        )

        self.unit_entry.delete(
            0,
            tk.END
        )

        self.unit_entry.insert(
            0,
            cart_item.get("unit", "Pcs") or "Pcs"
        )


        self.unit_entry.config(
            state="readonly"
        )

        self.increase_entry.delete(
            0,
            tk.END
        )

        self.increase_entry.insert(
            0,
            cart_item.get("increase", 0)
        )

        self.discount_entry.delete(
            0,
            tk.END
        )

        self.discount_entry.insert(
            0,
            cart_item.get("discount", 0)
        )

        self.discount_base_var.set(cart_item.get("discount_base", "Price"))

        self.add_btn.config(
            text=f"💾 Update Row #{index + 1} (Enter)",
            bg="#0066cc",
            activebackground="#0052a3"
        )

        self.qty_entry.focus_set()
        self.qty_entry.selection_range(0, tk.END)



    def refresh_cart_table(self):

        for row in self.tree.get_children():

            self.tree.delete(row)

        serial = 1

        for idx, item in enumerate(self.cart_items):
            tag = "evenrow" if idx % 2 == 0 else "oddrow"
            inc_val = float(item.get("increase", 0) or 0)
            disc_val = float(item.get("discount", 0) or 0)
            inc_str = f"+{int(inc_val) if inc_val.is_integer() else inc_val}%" if inc_val > 0 else "0%"
            disc_str = f"-{int(disc_val) if disc_val.is_integer() else disc_val}%" if disc_val > 0 else "0%"

            self.tree.insert(
                "",
                "end",
                values=(
                    serial,
                    item["quantity"],
                    item["name"],
                    item["mrp"],
                    item["price"],
                    item["unit"],
                    inc_str,
                    disc_str,
                    item.get("discount_base", "Price"),
                    f"{item['total']:,.2f}",
                    " ✏️ ",
                    " ❌ "
                ),
                tags=(tag,)
            )

            serial += 1




    # =========================
    # TALLY GLOBAL KEYBOARD SHORTCUTS
    # =========================

    def _delete_selected_cart_row(self):
        """Delete currently selected row in table via Delete / BackSpace key."""
        selected = self.tree.selection()
        if selected:
            self.delete_cart_item(selected[0])

    def _edit_selected_cart_row(self):
        """Edit currently selected row in table via Enter key."""
        selected = self.tree.selection()
        if selected:
            self.edit_cart_item(selected[0])


