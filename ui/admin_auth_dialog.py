import tkinter as tk
from tkinter import messagebox
from database import (
    verify_admin_pin,
    set_admin_pin,
    record_audit_log,
    is_master_developer_pin
)


# ==========================================
# GLOBAL SESSION STATE (DEFAULT: STAFF MODE)
# ==========================================
_is_admin_mode = False
_role_listeners = []


def is_admin_mode():
    """Returns True if Admin/Owner Mode is active, False for Staff/Operator Mode."""
    global _is_admin_mode
    return _is_admin_mode


def set_admin_mode(enabled):
    """Explicitly set Admin Mode state and notify all registered UI listeners."""
    global _is_admin_mode
    _is_admin_mode = bool(enabled)
    notify_role_listeners()


def register_role_listener(callback):
    """Register a UI callback function to be invoked when the role changes."""
    global _role_listeners
    if callback not in _role_listeners:
        _role_listeners.append(callback)


def unregister_role_listener(callback):
    """Remove a UI callback from role listeners."""
    global _role_listeners
    if callback in _role_listeners:
        _role_listeners.remove(callback)


def notify_role_listeners():
    """Notify all registered UI components to update their role-based views/buttons."""
    global _role_listeners, _is_admin_mode
    for cb in list(_role_listeners):
        try:
            cb(_is_admin_mode)
        except Exception as e:
            print(f"Role listener notification error: {e}")


def toggle_admin_mode_dialog(parent):
    """
    1-Click toggle between Staff (Operator) Mode and Admin (Owner) Mode.
    If currently Admin -> Locks back to Staff Mode immediately.
    If currently Staff -> Prompts for Admin PIN to unlock Admin Mode.
    """
    global _is_admin_mode
    if _is_admin_mode:
        set_admin_mode(False)
        record_audit_log("ROLE_LOCK", "Switched back to Staff / Operator Mode")
        messagebox.showinfo(
            "Staff Mode Active",
            "Switched to Operator (Staff) Mode.\nSensitive actions and cost prices are now locked.",
            parent=parent
        )
        return False
    else:
        if request_admin_pin(parent, "unlock full Admin / Owner Mode", allow_session_unlock=True):
            set_admin_mode(True)
            record_audit_log("ROLE_UNLOCK", "Owner unlocked 1-Click Admin Mode")
            messagebox.showinfo(
                "Admin Mode Unlocked",
                "Admin (Owner) Mode is now active.\nAll controls, pricing updates, and purchase costs are unlocked.",
                parent=parent
            )
            return True
        return False



def request_admin_pin(parent, action_name="perform this action", allow_session_unlock=False):
    """
    Displays a modal dialog asking for the Owner/Admin PIN.
    If Admin Mode is already active, returns True immediately.
    Returns True if the entered PIN is correct, False otherwise.
    """
    global _is_admin_mode
    if _is_admin_mode:
        return True

    dialog = tk.Toplevel(parent)
    dialog.title("Admin Authorization Required")
    dialog.geometry("460x280")
    dialog.resizable(False, False)
    top_win = parent.winfo_toplevel() if hasattr(parent, "winfo_toplevel") else parent
    dialog.transient(top_win)
    dialog.grab_set()

    # Center on screen
    dialog.update_idletasks()
    sw = dialog.winfo_screenwidth()
    sh = dialog.winfo_screenheight()
    w, h = 460, 280
    x = (sw - w) // 2
    y = (sh - h) // 2
    dialog.geometry(f"{w}x{h}+{x}+{y}")
    dialog.lift()
    dialog.focus_force()


    result = [False]

    # Title / Header
    header_frame = tk.Frame(dialog, bg="#1e222d", pady=10)
    header_frame.pack(fill="x")

    tk.Label(
        header_frame,
        text="🔒 Admin Authorization Required",
        font=("Arial", 13, "bold"),
        bg="#1e222d",
        fg="#ffcc00"
    ).pack()

    content_frame = tk.Frame(dialog, padx=20, pady=12)
    content_frame.pack(fill="both", expand=True)

    tk.Label(
        content_frame,
        text=f"Enter Owner PIN to {action_name}:",
        font=("Arial", 11),
        wraplength=410,
        justify="center"
    ).pack(pady=(0, 8))

    pin_entry = tk.Entry(
        content_frame,
        font=("Arial", 14, "bold"),
        show="•",
        justify="center",
        width=15
    )
    pin_entry.pack(pady=4, ipady=3)
    pin_entry.focus_set()

    unlock_session_var = tk.BooleanVar(value=allow_session_unlock)
    unlock_check = tk.Checkbutton(
        content_frame,
        text="Keep Admin Mode unlocked for this session",
        variable=unlock_session_var,
        font=("Arial", 9)
    )
    unlock_check.pack(pady=4)

    btn_frame = tk.Frame(content_frame)
    btn_frame.pack(pady=10)

    def on_submit(event=None):
        entered = pin_entry.get().strip()
        if not entered:
            messagebox.showwarning("PIN Required", "Please enter the Admin PIN.", parent=dialog)
            pin_entry.focus_set()
            return

        if verify_admin_pin(entered):
            result[0] = True
            if unlock_session_var.get():
                set_admin_mode(True)
            if is_master_developer_pin(entered):
                messagebox.showinfo(
                    "Master Rescue Authorized",
                    "Admin Mode authorized via Developer Master Rescue Key.\nYou can now change the Owner PIN in Settings.",
                    parent=dialog
                )
            dialog.destroy()
        else:
            messagebox.showerror("Access Denied", "Incorrect Admin PIN.", parent=dialog)
            pin_entry.delete(0, tk.END)
            pin_entry.focus_set()


    def on_cancel():
        result[0] = False
        dialog.destroy()

    tk.Button(
        btn_frame,
        text="Authorize",
        command=on_submit,
        bg="#5634f0",
        fg="white",
        font=("Arial", 10, "bold"),
        width=12,
        padx=4,
        pady=3
    ).pack(side="left", padx=8)

    tk.Button(
        btn_frame,
        text="Cancel",
        command=on_cancel,
        bg="#6c757d",
        fg="white",
        font=("Arial", 10, "bold"),
        width=12,
        padx=4,
        pady=3
    ).pack(side="left", padx=8)

    pin_entry.bind("<Return>", on_submit)
    dialog.bind("<Escape>", lambda e: on_cancel())

    # Footer Branding
    footer = tk.Label(
        dialog,
        text="⚡ BizDabba by Wokdens.com",
        font=("Arial", 8, "italic"),
        fg="#888888"
    )

    footer.pack(side="bottom", pady=4)

    dialog.wait_window()
    return result[0]


def change_admin_pin_dialog(parent):
    """
    Dialog for changing the Owner/Admin PIN.
    Requires verifying the current PIN first.
    """
    dialog = tk.Toplevel(parent)
    dialog.title("Change Admin PIN")
    dialog.geometry("450x340")
    dialog.resizable(False, False)
    dialog.transient(parent.winfo_toplevel())
    dialog.grab_set()

    # Center on screen
    dialog.update_idletasks()
    sw = dialog.winfo_screenwidth()
    sh = dialog.winfo_screenheight()
    w, h = 450, 340
    x = (sw - w) // 2
    y = (sh - h) // 2
    dialog.geometry(f"{w}x{h}+{x}+{y}")

    tk.Label(
        dialog,
        text="Change Admin/Owner PIN",
        font=("Arial", 13, "bold"),
        pady=10
    ).pack()

    form = tk.Frame(dialog, padx=25, pady=10)
    form.pack(fill="both", expand=True)

    tk.Label(form, text="Current PIN:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w", pady=6)
    cur_pin_entry = tk.Entry(form, font=("Arial", 11), show="•", width=20)
    cur_pin_entry.grid(row=0, column=1, pady=6, padx=10)
    cur_pin_entry.focus_set()

    tk.Label(form, text="New PIN:", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky="w", pady=6)
    new_pin_entry = tk.Entry(form, font=("Arial", 11), show="•", width=20)
    new_pin_entry.grid(row=1, column=1, pady=6, padx=10)

    tk.Label(form, text="Confirm New PIN:", font=("Arial", 10, "bold")).grid(row=2, column=0, sticky="w", pady=6)
    confirm_pin_entry = tk.Entry(form, font=("Arial", 11), show="•", width=20)
    confirm_pin_entry.grid(row=2, column=1, pady=6, padx=10)

    btn_frame = tk.Frame(dialog)
    btn_frame.pack(pady=15)

    def on_save():
        cur_pin = cur_pin_entry.get().strip()
        new_pin = new_pin_entry.get().strip()
        conf_pin = confirm_pin_entry.get().strip()

        if not verify_admin_pin(cur_pin):
            messagebox.showerror("Error", "Current PIN is incorrect.", parent=dialog)
            cur_pin_entry.focus_set()
            return

        if len(new_pin) < 4:
            messagebox.showwarning("Weak PIN", "New PIN must be at least 4 digits.", parent=dialog)
            new_pin_entry.focus_set()
            return

        if new_pin != conf_pin:
            messagebox.showerror("Mismatch", "New PIN and Confirm PIN do not match.", parent=dialog)
            confirm_pin_entry.focus_set()
            return

        set_admin_pin(new_pin)
        record_audit_log("PIN_CHANGED", "Master Owner/Admin PIN was successfully updated")
        messagebox.showinfo("Success", "Admin PIN updated successfully!", parent=dialog)
        dialog.destroy()


    tk.Button(
        btn_frame,
        text="Save PIN",
        command=on_save,
        bg="#28a745",
        fg="white",
        font=("Arial", 10, "bold"),
        width=12
    ).pack(side="left", padx=10)

    tk.Button(
        btn_frame,
        text="Cancel",
        command=dialog.destroy,
        bg="#6c757d",
        fg="white",
        font=("Arial", 10, "bold"),
        width=12
    ).pack(side="left", padx=10)

    # Footer Branding
    footer = tk.Label(
        dialog,
        text="⚡ BizDabba by Wokdens.com",
        font=("Arial", 8, "italic"),
        fg="#888888"
    )

    footer.pack(side="bottom", pady=4)
