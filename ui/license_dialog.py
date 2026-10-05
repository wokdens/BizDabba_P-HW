import tkinter as tk
from tkinter import ttk, messagebox
import re
from license_manager import (
    is_master_activated,
    get_demo_launch_count,
    get_demo_launches_remaining,
    verify_any_license_input,
    activate_master_license,
    MAX_DEMO_LAUNCHES
)

class LicenseVerificationDialog:
    """
    Enterprise License Verification Dialog.
    Displayed on startup if the software has not been permanently activated with a Master Key.
    Accepts:
      1. Demo License Key (per-session, valid for up to 50 launches).
      2. Master License Key (one-time permanent activation).
    """

    def __init__(self, parent, is_startup=True):
        self.parent = parent
        self.is_startup = is_startup
        self.is_verified = False
        self.activated_type = None

        self.window = tk.Toplevel(parent)
        self.window.title("BizDabba - Software License Verification")
        self.window.geometry("520x460")
        self.window.resizable(False, False)
        self.window.configure(bg="#f8f9fa")

        # Bring to front and grab focus
        self.window.lift()
        self.window.attributes("-topmost", True)
        self.window.after(100, lambda: self.window.attributes("-topmost", False))
        self.window.protocol("WM_DELETE_WINDOW", self.on_cancel)

        # Center on screen
        self.center_window(520, 460)

        self._build_ui()

    def center_window(self, width, height):
        self.window.update_idletasks()
        screen_w = self.window.winfo_screenwidth()
        screen_h = self.window.winfo_screenheight()
        x = (screen_w - width) // 2
        y = (screen_h - height) // 2
        self.window.geometry(f"{width}x{height}+{x}+{y}")

    def _build_ui(self):
        # 1. Header Banner
        header = tk.Frame(self.window, bg="#1e222d", height=85)
        header.pack(fill="x")
        header.pack_propagate(False)

        title_lbl = tk.Label(
            header,
            text="BizDabba by Wokdens.com",
            font=("Arial", 16, "bold"),
            bg="#1e222d",
            fg="#ffcc00"
        )
        title_lbl.pack(pady=(14, 2))

        sub_lbl = tk.Label(
            header,
            text="Paints & Hardware Wholesale & Retail Edition",
            font=("Arial", 9),
            bg="#1e222d",
            fg="#a0aab8"
        )
        sub_lbl.pack()

        # 2. Main Container
        content = tk.Frame(self.window, bg="#f8f9fa", padx=30, pady=20)
        content.pack(fill="both", expand=True)

        # Status Badge / Card
        used = get_demo_launch_count()
        remaining = get_demo_launches_remaining()

        status_frame = tk.Frame(content, bg="#e9ecef", relief="solid", borderwidth=1, padx=12, pady=10)
        status_frame.pack(fill="x", pady=(0, 15))

        if used >= MAX_DEMO_LAUNCHES:
            status_text = f"⚠️ DEMO TRIAL EXPIRED ({used}/{MAX_DEMO_LAUNCHES} used)\nMaster License Key required to unlock BizDabba."
            status_fg = "#dc3545"
        else:
            status_text = f"ℹ️ DEMO / TRIAL MODE\n{used} of {MAX_DEMO_LAUNCHES} launches used ({remaining} remaining)"
            status_fg = "#0f5132"

        self.status_lbl = tk.Label(
            status_frame,
            text=status_text,
            font=("Arial", 10, "bold"),
            bg="#e9ecef",
            fg=status_fg,
            justify="center"
        )
        self.status_lbl.pack()

        # Input Prompt
        prompt_lbl = tk.Label(
            content,
            text="Enter License Key to Continue:",
            font=("Arial", 11, "bold"),
            bg="#f8f9fa",
            fg="#212529"
        )
        prompt_lbl.pack(anchor="w", pady=(5, 6))

        # Entry Box
        self.key_entry = tk.Entry(
            content,
            font=("Consolas", 14, "bold"),
            justify="center",
            relief="solid",
            borderwidth=1,
            bg="white",
            fg="#1e222d"
        )
        self.key_entry.pack(fill="x", ipady=8, pady=(0, 6))
        self.key_entry.bind("<Return>", lambda e: self.on_verify())
        self.key_entry.bind("<Escape>", lambda e: self.on_cancel())

        # Explanatory helper
        hint_lbl = tk.Label(
            content,
            text="• Demo Key: 8 digits for trial session (up to 50 times)\n• Master Key: 10 digits for permanent lifetime activation",
            font=("Arial", 8),
            bg="#f8f9fa",
            fg="#6c757d",
            justify="left"
        )
        hint_lbl.pack(anchor="w", pady=(0, 10))

        # Inline Error Message
        self.error_lbl = tk.Label(
            content,
            text="",
            font=("Arial", 9, "bold"),
            bg="#f8f9fa",
            fg="#dc3545",
            wraplength=450,
            justify="center"
        )
        self.error_lbl.pack(pady=(0, 10))

        # Buttons Bar
        btn_frame = tk.Frame(content, bg="#f8f9fa")
        btn_frame.pack(fill="x", pady=(5, 0))

        verify_btn = tk.Button(
            btn_frame,
            text="🔓 Verify & Launch",
            font=("Arial", 11, "bold"),
            bg="#059669",
            fg="white",
            activebackground="#047857",
            activeforeground="white",
            padx=16,
            pady=8,
            relief="flat",
            cursor="hand2",
            command=self.on_verify
        )
        verify_btn.pack(side="left", expand=True, fill="x", padx=(0, 8))

        cancel_btn = tk.Button(
            btn_frame,
            text="✕ Exit",
            font=("Arial", 11, "bold"),
            bg="#6c757d",
            fg="white",
            activebackground="#5a6268",
            activeforeground="white",
            padx=16,
            pady=8,
            relief="flat",
            cursor="hand2",
            command=self.on_cancel
        )
        cancel_btn.pack(side="right", expand=True, fill="x", padx=(8, 0))

        # Footer Branding
        footer_lbl = tk.Label(
            self.window,
            text="⚡ BizDabba by Wokdens.com",
            font=("Arial", 8, "italic"),
            bg="#f8f9fa",
            fg="#888888"
        )
        footer_lbl.pack(side="bottom", pady=8)

        self.key_entry.focus_set()

    def on_verify(self):
        self.error_lbl.config(text="")
        key_input = self.key_entry.get().strip()

        if not key_input:
            self.error_lbl.config(text="Please enter a License Key.")
            self.key_entry.focus_set()
            return

        ok, key_type, message, details = verify_any_license_input(key_input)

        if not ok:
            # Rejection (invalid key or expired demo)
            self.error_lbl.config(text=message)
            self.key_entry.selection_range(0, tk.END)
            self.key_entry.focus_set()
            return

        # Verification Succeeded!
        self.is_verified = True
        self.activated_type = key_type

        # Show notification popup as requested
        if key_type == "master":
            self.show_master_activated_popup()
        else:
            used = details.get("used", 1)
            remaining = details.get("remaining", MAX_DEMO_LAUNCHES - used)
            self.show_demo_accepted_popup(used, remaining)

    def show_demo_accepted_popup(self, used, remaining):
        """
        Displays a clean, brief notification popup:
        '1 out of 50 done or 49 out of 50 remaining'
        """
        popup = tk.Toplevel(self.window)
        popup.title("BizDabba - Trial Demo Access")
        popup.geometry("420x240")
        popup.resizable(False, False)
        popup.configure(bg="#ffffff")
        popup.attributes("-topmost", True)

        # Center popup
        popup.update_idletasks()
        sw = popup.winfo_screenwidth()
        sh = popup.winfo_screenheight()
        popup.geometry(f"420x240+{(sw - 420)//2}+{(sh - 240)//2}")

        # Top green bar
        bar = tk.Frame(popup, bg="#059669", height=8)
        bar.pack(fill="x")

        icon_lbl = tk.Label(popup, text="✅", font=("Arial", 28), bg="white")
        icon_lbl.pack(pady=(15, 5))

        title = tk.Label(
            popup,
            text="Demo License Accepted",
            font=("Arial", 14, "bold"),
            bg="white",
            fg="#1e222d"
        )
        title.pack()

        # Exact user requested text: '1 out of 50 done or 49 out of 50 remaining'
        counter_msg = f"{used} out of {MAX_DEMO_LAUNCHES} done\n({remaining} out of {MAX_DEMO_LAUNCHES} remaining)"
        msg = tk.Label(
            popup,
            text=counter_msg,
            font=("Arial", 12, "bold"),
            bg="white",
            fg="#059669",
            justify="center"
        )
        msg.pack(pady=8)

        continue_btn = tk.Button(
            popup,
            text="Continue to BizDabba →",
            font=("Arial", 10, "bold"),
            bg="#1e222d",
            fg="#ffcc00",
            relief="flat",
            padx=16,
            pady=6,
            cursor="hand2",
            command=lambda: self._finish_and_close(popup)
        )
        continue_btn.pack(pady=(5, 10))

        # Auto-continue after 2.5 seconds if not clicked
        popup.after(2500, lambda: self._finish_and_close(popup))

    def show_master_activated_popup(self):
        """Displays permanent Master Activation confirmation popup."""
        popup = tk.Toplevel(self.window)
        popup.title("BizDabba - Permanent Activation")
        popup.geometry("440x260")
        popup.resizable(False, False)
        popup.configure(bg="#ffffff")
        popup.attributes("-topmost", True)

        popup.update_idletasks()
        sw = popup.winfo_screenwidth()
        sh = popup.winfo_screenheight()
        popup.geometry(f"440x260+{(sw - 440)//2}+{(sh - 260)//2}")

        bar = tk.Frame(popup, bg="#ffcc00", height=8)
        bar.pack(fill="x")

        icon_lbl = tk.Label(popup, text="🎉", font=("Arial", 28), bg="white")
        icon_lbl.pack(pady=(15, 5))

        title = tk.Label(
            popup,
            text="Master License Activated!",
            font=("Arial", 14, "bold"),
            bg="white",
            fg="#1e222d"
        )
        title.pack()

        msg = tk.Label(
            popup,
            text="BizDabba is now permanently activated for lifetime use.\nNo further license keys will ever be required!",
            font=("Arial", 10),
            bg="white",
            fg="#495057",
            justify="center"
        )
        msg.pack(pady=8)

        continue_btn = tk.Button(
            popup,
            text="Launch BizDabba →",
            font=("Arial", 10, "bold"),
            bg="#059669",
            fg="white",
            relief="flat",
            padx=16,
            pady=6,
            cursor="hand2",
            command=lambda: self._finish_and_close(popup)
        )
        continue_btn.pack(pady=(5, 10))

        popup.after(2500, lambda: self._finish_and_close(popup))

    def _finish_and_close(self, popup=None):
        if popup:
            try:
                popup.destroy()
            except Exception:
                pass
        self.window.destroy()

    def on_cancel(self):
        self.is_verified = False
        self.window.destroy()

    def show(self) -> bool:
        """Modal execution: blocks until closed or verified. Returns True if verified."""
        self.window.grab_set()
        self.parent.wait_window(self.window)
        return self.is_verified


def prompt_master_license_upgrade(parent, on_success_callback=None) -> bool:
    """
    In-app dialog allowing the user to enter the Master License Key
    while already running in Demo Mode to permanently activate on the spot.
    """
    dialog = tk.Toplevel(parent)
    dialog.title("BizDabba - Upgrade to Master License")
    dialog.geometry("480x360")
    dialog.resizable(False, False)
    dialog.configure(bg="#f8f9fa")
    dialog.attributes("-topmost", True)
    dialog.after(100, lambda: dialog.attributes("-topmost", False))

    dialog.update_idletasks()
    sw = dialog.winfo_screenwidth()
    sh = dialog.winfo_screenheight()
    dialog.geometry(f"480x360+{(sw - 480)//2}+{(sh - 360)//2}")

    header = tk.Frame(dialog, bg="#1e222d", height=70)
    header.pack(fill="x")
    header.pack_propagate(False)

    tk.Label(
        header,
        text="🔑 Permanent Lifetime Activation",
        font=("Arial", 14, "bold"),
        bg="#1e222d",
        fg="#ffcc00"
    ).pack(pady=(12, 2))

    tk.Label(
        header,
        text="Enter Master License Key to unlock BizDabba permanently",
        font=("Arial", 9),
        bg="#1e222d",
        fg="#a0aab8"
    ).pack()

    body = tk.Frame(dialog, bg="#f8f9fa", padx=25, pady=20)
    body.pack(fill="both", expand=True)

    tk.Label(
        body,
        text="Enter 10-Digit Master License Key:",
        font=("Arial", 10, "bold"),
        bg="#f8f9fa",
        fg="#212529"
    ).pack(anchor="w", pady=(0, 5))

    key_entry = tk.Entry(
        body,
        font=("Consolas", 14, "bold"),
        justify="center",
        relief="solid",
        borderwidth=1,
        bg="white"
    )
    key_entry.pack(fill="x", ipady=6, pady=(0, 6))

    err_lbl = tk.Label(
        body,
        text="",
        font=("Arial", 9, "bold"),
        bg="#f8f9fa",
        fg="#dc3545",
        wraplength=420
    )
    err_lbl.pack(pady=(0, 10))

    success_holder = [False]

    def do_activate():
        err_lbl.config(text="")
        val = key_entry.get().strip()
        ok, msg = activate_master_license(val)
        if ok:
            success_holder[0] = True
            messagebox.showinfo(
                "Activation Successful",
                "🎉 Master License Activated!\n\nBizDabba is now permanently unlocked for lifetime use.\nNo further license keys will ever be required.",
                parent=dialog
            )
            dialog.destroy()
            if on_success_callback:
                on_success_callback()
        else:
            err_lbl.config(text=msg)
            key_entry.selection_range(0, tk.END)
            key_entry.focus_set()

    key_entry.bind("<Return>", lambda e: do_activate())
    key_entry.bind("<Escape>", lambda e: dialog.destroy())

    btn_row = tk.Frame(body, bg="#f8f9fa")
    btn_row.pack(fill="x", pady=10)

    tk.Button(
        btn_row,
        text="Activate Lifetime License",
        font=("Arial", 10, "bold"),
        bg="#059669",
        fg="white",
        relief="flat",
        padx=12,
        pady=6,
        cursor="hand2",
        command=do_activate
    ).pack(side="left", expand=True, fill="x", padx=(0, 5))

    tk.Button(
        btn_row,
        text="Cancel",
        font=("Arial", 10, "bold"),
        bg="#6c757d",
        fg="white",
        relief="flat",
        padx=12,
        pady=6,
        cursor="hand2",
        command=dialog.destroy
    ).pack(side="right", expand=True, fill="x", padx=(5, 0))

    # Footer Branding
    tk.Label(
        dialog,
        text="⚡ BizDabba by Wokdens.com",
        font=("Arial", 8, "italic"),
        bg="#f8f9fa",
        fg="#888888"
    ).pack(side="bottom", pady=6)

    key_entry.focus_set()
    dialog.grab_set()
    parent.wait_window(dialog)
    return success_holder[0]
