import tkinter as tk
from tkinter import ttk

from ui.dashboard_ui import DashboardUI
from ui.inventory_ui import InventoryUI
from ui.invoice_ui import InvoiceUI
from ui.invoice_history_ui import InvoiceHistoryUI
from ui.ledger_ui import LedgerUI


class MainWindow:

    def __init__(self, root):

        self.root = root

        self.root.title("BizDabba PHWP by wokdens.com")

        self.root.geometry("1200x780")
        self.root.minsize(1024, 650)
        self.current_ui = None

        self._configure_styles()


        # =========================
        # FOOTER STATUS / BRANDING BAR

        # =========================
        footer_frame = tk.Frame(root, bg="#1e222d", height=32)
        footer_frame.pack(side="bottom", fill="x")
        self.footer_frame = footer_frame

        self.status_lbl = tk.Label(
            footer_frame,
            text=" 🟢 Pen Drive Mode | Ready ",
            font=("Arial", 9, "bold"),
            bg="#1e222d",
            fg="#28a745"
        )
        self.status_lbl.pack(side="left", padx=15, pady=5)

        self.license_upgrade_btn = tk.Button(
            footer_frame,
            text="🔑 Activate Master License",
            font=("Arial", 8, "bold"),
            bg="#b45309",
            fg="white",
            activebackground="#92400e",
            activeforeground="white",
            padx=8,
            pady=1,
            relief="flat",
            cursor="hand2",
            command=self.open_master_activation
        )

        center_lbl = tk.Label(
            footer_frame,
            text="Paints & Hardware Wholesale & Retail Management",
            font=("Arial", 9),
            bg="#1e222d",
            fg="#a0aab8"
        )
        center_lbl.pack(side="left", expand=True, pady=5)

        branding_lbl = tk.Label(
            footer_frame,
            text="⚡ BizDabba by Wokdens.com ",
            font=("Arial", 9, "bold"),
            bg="#1e222d",
            fg="#ffcc00"
        )

        branding_lbl.pack(side="right", padx=15, pady=5)

        # =========================
        # MENU FRAME
        # =========================

        menu_frame = tk.Frame(root)

        menu_frame.pack(
            fill="x",
            pady=6
        )


        # =========================
        # BUTTON COLORS
        # =========================

        self.default_bg = "#f0f0f0"

        self.active_bg = "#4a90e2"

        self.active_fg = "white"

        # =========================
        # BUTTONS
        # =========================

        self.inventory_btn = tk.Button(
            menu_frame,
            text="Inventory",
            width=18,
            height=1,
            font=("Arial", 12, "bold"),
            padx=8,
            pady=4,
            command=self.open_inventory
        )

        self.inventory_btn.pack(
            side="left",
            padx=8
        )

        self.invoice_btn = tk.Button(
            menu_frame,
            text="Sales Invoice",
            width=18,
            height=1,
            font=("Arial", 12, "bold"),
            padx=8,
            pady=4,
            command=self.open_invoice
        )

        self.invoice_btn.pack(
            side="left",
            padx=8
        )

        self.invoice_history_btn = tk.Button(
            menu_frame,
            text="Invoice History",
            width=18,
            height=1,
            font=("Arial", 12, "bold"),
            padx=8,
            pady=4,
            command=self.open_invoice_history
        )

        self.invoice_history_btn.pack(
            side="left",
            padx=8
        )

        self.ledger_btn = tk.Button(
            menu_frame,
            text="Ledger",
            width=18,
            height=1,
            font=("Arial", 12, "bold"),
            padx=8,
            pady=4,
            command=self.open_ledger
        )

        self.ledger_btn.pack(
            side="left",
            padx=8
        )

        # Dashboard moved to END
        self.dashboard_btn = tk.Button(
            menu_frame,
            text="Dashboard",
            width=18,
            height=1,
            font=("Arial", 12, "bold"),
            padx=8,
            pady=4,
            command=self.open_dashboard
        )

        self.dashboard_btn.pack(
            side="left",
            padx=8
        )

        # =========================
        # 1-CLICK ROLE TOGGLE & SAFE SAVE (PEN DRIVE)
        # =========================
        self.safe_save_btn = tk.Button(
            menu_frame,
            text="💾 Save to Pen Drive (Ctrl+S)",
            font=("Arial", 10, "bold"),
            bg="#059669",
            fg="white",
            activebackground="#047857",
            activeforeground="white",
            padx=10,
            pady=4,
            command=self.trigger_pen_drive_save
        )
        self.safe_save_btn.pack(
            side="right",
            padx=6
        )

        self.role_toggle_btn = tk.Button(
            menu_frame,
            text="👤 Staff Mode [🔒 Unlock Admin]",
            font=("Arial", 10, "bold"),
            bg="#e9ecef",
            fg="#495057",
            padx=10,
            pady=4,
            command=self.toggle_role
        )
        self.role_toggle_btn.pack(
            side="right",
            padx=6
        )

        from ui.admin_auth_dialog import register_role_listener, is_admin_mode
        register_role_listener(self.update_role_ui)
        self.update_role_ui(is_admin_mode())


        # =========================
        # CONTENT FRAME
        # =========================

        self.content_frame = tk.Frame(
            root,
            bg="white",
            relief="solid",
            borderwidth=1
        )

        self.content_frame.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=12
        )

        # Global Keyboard Shortcut for Safe Pen Drive Save
        self.root.bind_all("<Control-s>", lambda e: self.trigger_pen_drive_save())
        self.root.bind_all("<Control-S>", lambda e: self.trigger_pen_drive_save())

        # Default page
        self.current_ui = None
        self.open_inventory()

        # Update initial license status indicator in footer
        self.update_license_ui()

    # =========================
    # CLEAR CONTENT
    # =========================

    def clear_content(self):

        if self.current_ui and hasattr(self.current_ui, "save_state"):
            self.current_ui.save_state()

        for widget in self.content_frame.winfo_children():

            widget.destroy()

        self.current_ui = None

    # =========================
    # RESET BUTTON COLORS
    # =========================

    def reset_menu_colors(self):

        buttons = [
            self.inventory_btn,
            self.invoice_btn,
            self.invoice_history_btn,
            self.ledger_btn,
            self.dashboard_btn
        ]

        for btn in buttons:

            btn.config(
                bg=self.default_bg,
                fg="black"
            )

    # =========================
    # HIGHLIGHT BUTTON
    # =========================

    def highlight_button(self, button):

        self.reset_menu_colors()

        button.config(
            bg=self.active_bg,
            fg=self.active_fg
        )

    # =========================
    # INVENTORY
    # =========================

    def open_inventory(self):

        self.clear_content()

        self.highlight_button(
            self.inventory_btn
        )

        self.current_ui = InventoryUI(self.content_frame)

    # =========================
    # SALES INVOICE
    # =========================

    def open_invoice(self, invoice_id_to_edit=None, authorized=False):

        self.clear_content()

        self.highlight_button(
            self.invoice_btn
        )

        self.current_ui = InvoiceUI(self.content_frame, app=self)
        if invoice_id_to_edit:
            self.current_ui.load_invoice_for_editing(invoice_id_to_edit, authorized=authorized)

    # =========================
    # INVOICE HISTORY
    # =========================

    def open_invoice_history(self):

        self.clear_content()

        self.highlight_button(
            self.invoice_history_btn
        )

        self.current_ui = InvoiceHistoryUI(self.content_frame, app=self)

    # =========================
    # LEDGER
    # =========================

    def open_ledger(self):

        self.clear_content()

        self.highlight_button(
            self.ledger_btn
        )

        self.current_ui = LedgerUI(self.content_frame)

    # =========================
    # DASHBOARD
    # =========================

    def open_dashboard(self):

        self.clear_content()

        self.highlight_button(
            self.dashboard_btn
        )

        self.current_ui = DashboardUI(self.content_frame, app=self)


    # =========================
    # ROLE MANAGEMENT
    # =========================

    def toggle_role(self):
        from ui.admin_auth_dialog import toggle_admin_mode_dialog
        toggle_admin_mode_dialog(self.root)

    def update_role_ui(self, admin_active):
        if admin_active:
            self.role_toggle_btn.config(
                text="👑 Admin Mode [🔓 Lock]",
                bg="#ffd700",
                fg="#212529"
            )
        else:
            self.role_toggle_btn.config(
                text="👤 Staff Mode [🔒 Unlock Admin]",
                bg="#e9ecef",
                fg="#495057"
            )
        # Notify active UI view if it supports live role change
        if self.current_ui and hasattr(self.current_ui, "on_role_changed"):
            self.current_ui.on_role_changed(admin_active)

    def _configure_styles(self):
        """Apply modern, crisp tabular styles with distinct borders across all ttk tables."""
        style = ttk.Style()
        if "clam" in style.theme_names():
            style.theme_use("clam")

        # Base Treeview Styling
        style.configure(
            "Treeview",
            background="#ffffff",
            foreground="#212529",
            rowheight=28,
            fieldbackground="#ffffff",
            bordercolor="#ced4da",
            borderwidth=1,
            font=("Arial", 10)
        )
        style.map(
            "Treeview",
            background=[("selected", "#0066cc")],
            foreground=[("selected", "#ffffff")]
        )

        # Column Headers Styling
        style.configure(
            "Treeview.Heading",
            font=("Arial", 10, "bold"),
            background="#e9ecef",
            foreground="#212529",
            relief="groove",
            borderwidth=1
        )
        style.map(
            "Treeview.Heading",
            background=[("active", "#dee2e6")]
        )

    # =========================
    # SAFE PEN DRIVE SAVE & SYNC
    # =========================

    def trigger_pen_drive_save(self, event=None):
        """Flushes SQLite WAL pages, commits OS disk buffers, and displays a 3-second auto-dismissing toast."""
        from database import safe_flush_pen_drive
        from datetime import datetime

        # If current UI has unsaved pending field states, let it commit them
        if self.current_ui and hasattr(self.current_ui, "save_state"):
            try:
                self.current_ui.save_state()
            except Exception:
                pass

        ok, msg = safe_flush_pen_drive()
        now_str = datetime.now().strftime("%I:%M:%S %p")

        if ok:
            if hasattr(self, "status_lbl") and self.status_lbl:
                self.status_lbl.config(
                    text=f" 🟢 USB Synced & Safe ({now_str}) ",
                    fg="#28a745"
                )
            self.show_save_toast(success=True, time_str=now_str)
        else:
            self.show_save_toast(success=False, error_msg=msg)

    def show_save_toast(self, success=True, time_str="", error_msg=""):
        """Shows a clean, high-visibility, auto-dismissing toast popup for 3 seconds."""
        toast = tk.Toplevel(self.root)
        toast.overrideredirect(True)
        toast.attributes("-topmost", True)

        bg_color = "#065f46" if success else "#991b1b"
        border_color = "#34d399" if success else "#f87171"

        container = tk.Frame(
            toast,
            bg=bg_color,
            bd=2,
            relief="solid",
            highlightthickness=1,
            highlightbackground=border_color
        )
        container.pack(fill="both", expand=True)

        title_text = "💾 DATA SAFELY SAVED TO PEN DRIVE!" if success else "⚠️ SAVE ERROR"
        body_text = (
            f"All records, stock & invoices committed to USB storage.\n"
            f"Synced at {time_str} • Safe to unplug Pen Drive or exit.\n"
            f"Auto-closing in 3 seconds... (Click to close)"
            if success else
            f"Failed to flush data to USB: {error_msg}\nPlease do not unplug the drive."
        )

        tk.Label(
            container,
            text=title_text,
            font=("Arial", 12, "bold"),
            bg=bg_color,
            fg="#ffffff",
            padx=20,
            pady=6
        ).pack(anchor="center")

        msg_lbl = tk.Label(
            container,
            text=body_text,
            font=("Arial", 10),
            bg=bg_color,
            fg="#e6fffa" if success else "#fee2e2",
            padx=20,
            pady=4,
            justify="center"
        )
        msg_lbl.pack(anchor="center")

        # Position centered on main window
        toast.update_idletasks()
        w = 460
        h = 96
        root_x = self.root.winfo_x()
        root_y = self.root.winfo_y()
        root_w = self.root.winfo_width()
        root_h = self.root.winfo_height()

        x = root_x + max(0, (root_w - w) // 2)
        y = root_y + max(40, (root_h - h) // 4)
        toast.geometry(f"{w}x{h}+{x}+{y}")

        # Allow instant dismiss on click or keys
        def close_toast(e=None):
            if toast.winfo_exists():
                toast.destroy()

        toast.bind("<Button-1>", close_toast)
        container.bind("<Button-1>", close_toast)
        msg_lbl.bind("<Button-1>", close_toast)
        toast.bind("<Escape>", close_toast)
        toast.bind("<Return>", close_toast)

        # 3-second countdown
        def countdown(remaining):
            if not toast.winfo_exists():
                return
            if remaining <= 0:
                toast.destroy()
            else:
                if success:
                    msg_lbl.config(
                        text=f"All records, stock & invoices committed to USB storage.\nSynced at {time_str} • Safe to unplug Pen Drive or exit.\nAuto-closing in {remaining}s... (Click to close)"
                    )
                toast.after(1000, lambda: countdown(remaining - 1))

        toast.after(1000, lambda: countdown(2))

    def update_license_ui(self):
        """Refreshes footer status badge and master upgrade button based on license state."""
        try:
            from license_manager import is_master_activated, get_demo_launches_remaining
            if is_master_activated():
                self.status_lbl.config(
                    text=" 🟢 Lifetime License | Safe USB Mode ",
                    fg="#28a745"
                )
                self.license_upgrade_btn.pack_forget()
            else:
                remaining = get_demo_launches_remaining()
                self.status_lbl.config(
                    text=f" 🟡 Demo Mode ({remaining}/50 left) | Safe USB Mode ",
                    fg="#ffc107"
                )
                self.license_upgrade_btn.pack(side="left", padx=6, pady=4)
        except Exception as e:
            print(f"Update license UI notice: {e}")

    def open_master_activation(self):
        """Opens in-app Master License Key upgrade dialog."""
        try:
            from ui.license_dialog import prompt_master_license_upgrade
            prompt_master_license_upgrade(self.root, on_success_callback=self.update_license_ui)
        except Exception as e:
            print(f"Open master activation notice: {e}")

