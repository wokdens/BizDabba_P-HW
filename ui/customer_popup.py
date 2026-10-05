import re
import tkinter as tk
from tkinter import messagebox
from database import get_connection

def validate_and_normalize_indian_mobile(phone_input: str, allow_empty: bool = False):
    """
    Validates and normalizes an Indian mobile number.
    Rules:
      - If allow_empty=True and input is blank, returns (True, "").
      - Must be 10 digits starting with 6, 7, 8, or 9 (e.g., 9876543210).
      - If 11 digits, must start with 0 followed by 6-9 (e.g., 09876543210).
      - If starts with +91 or +91- or 91, the 10-digit number must follow (e.g., +91-9876543210).
      - Ignores optional spaces, hyphens, parentheses.
    Returns:
      (True, '9876543210') if valid
      (False, error_message) if invalid
    """
    if not phone_input or not phone_input.strip():
        if allow_empty:
            return True, ""
        return False, "Mobile number is required."

    raw = phone_input.strip()

    # Normalize separators: remove spaces, hyphens, parentheses, dots
    cleaned = re.sub(r"[\s\-\(\)\.]+", "", raw)

    # Check prefixes
    if cleaned.startswith("+91"):
        digits = cleaned[3:]
    elif cleaned.startswith("91") and len(cleaned) == 12:
        digits = cleaned[2:]
    elif cleaned.startswith("0") and len(cleaned) == 11:
        digits = cleaned[1:]
    else:
        if cleaned.startswith("+"):
            return False, "Only Indian mobile numbers (+91) are supported."
        digits = cleaned

    if not digits.isdigit():
        return False, "Mobile number must contain only numeric digits."

    if len(digits) != 10:
        if len(digits) < 10:
            return False, f"Mobile number has only {len(digits)} digits. A valid Indian mobile number must be 10 digits (or 11 digits with 0, or with +91-)."
        else:
            return False, f"Mobile number has {len(digits)} digits, which exceeds 10 digits."

    if digits[0] not in ("6", "7", "8", "9"):
        return False, f"Invalid mobile number '{digits}'. Valid Indian mobile numbers must start with 6, 7, 8, or 9."

    return True, digits


class CustomerPopup:

    def __init__(self, parent, refresh_callback):
        self.refresh_callback = refresh_callback
        self.window = tk.Toplevel(parent)
        self.window.title("Add Customer")
        self.window.geometry("420x380")
        self.window.grab_set()

        # =========================
        # TITLE
        # =========================
        title = tk.Label(
            self.window,
            text="Add New Customer",
            font=("Arial", 15, "bold")
        )
        title.pack(pady=(12, 6))

        # =========================
        # FORM FRAME
        # =========================
        form_frame = tk.Frame(self.window)
        form_frame.pack(padx=20, pady=5, fill="both")

        # NAME
        tk.Label(
            form_frame,
            text="Customer Name *",
            font=("Arial", 9, "bold")
        ).pack(anchor="w")

        self.name_entry = tk.Entry(form_frame, width=42, font=("Arial", 10))
        self.name_entry.pack(pady=(2, 8))

        # PHONE
        tk.Label(
            form_frame,
            text="Mobile Number (Optional - 10 digits / +91- / 0)",
            font=("Arial", 9, "bold")
        ).pack(anchor="w")

        self.phone_entry = tk.Entry(form_frame, width=42, font=("Arial", 10))
        self.phone_entry.pack(pady=(2, 8))

        # ADDRESS
        tk.Label(
            form_frame,
            text="Address (Optional)",
            font=("Arial", 9)
        ).pack(anchor="w")

        self.address_text = tk.Text(
            form_frame,
            width=42,
            height=4,
            font=("Arial", 9)
        )
        self.address_text.pack(pady=(2, 6))

        # Enter key shortcuts
        self.name_entry.bind("<Return>", lambda e: self.phone_entry.focus_set())
        self.phone_entry.bind("<Return>", lambda e: self.save_customer())

        # =========================
        # BUTTONS
        # =========================
        btn_frame = tk.Frame(self.window)
        btn_frame.pack(pady=12)

        add_btn = tk.Button(
            btn_frame,
            text="✓ Save Customer",
            width=15,
            bg="#28a745",
            fg="white",
            font=("Arial", 10, "bold"),
            command=self.save_customer
        )
        add_btn.pack(side="left", padx=8)

        cancel_btn = tk.Button(
            btn_frame,
            text="Cancel",
            width=12,
            font=("Arial", 10),
            command=self.window.destroy
        )
        cancel_btn.pack(side="left", padx=8)

        # Footer Branding
        footer = tk.Label(
            self.window,
            text="⚡ BizDabba by Wokdens.com",
            font=("Arial", 8, "italic"),
            fg="#888888"
        )
        footer.pack(side="bottom", pady=4)

        self.name_entry.focus_set()

    # =========================
    # SAVE CUSTOMER
    # =========================
    def save_customer(self):
        name = self.name_entry.get().strip()
        phone_raw = self.phone_entry.get().strip()
        address = self.address_text.get("1.0", tk.END).strip()

        if not name:
            messagebox.showerror(
                "Missing Customer Name",
                "Please enter the customer's name.",
                parent=self.window
            )
            self.name_entry.focus_set()
            return

        # Validate and normalize Indian mobile number (optional)
        normalized_phone = ""
        if phone_raw:
            is_valid, phone_result = validate_and_normalize_indian_mobile(phone_raw, allow_empty=True)
            if not is_valid:
                messagebox.showerror(
                    "Invalid Mobile Number",
                    f"{phone_result}\n\n"
                    "Accepted formats:\n"
                    "• 10 Digits: 9876543210 (starts with 6, 7, 8, or 9)\n"
                    "• With 0: 09876543210 (11 digits)\n"
                    "• With +91: +91-9876543210 or +91 9876543210",
                    parent=self.window
                )
                self.phone_entry.focus_set()
                return
            normalized_phone = phone_result

        conn = get_connection()
        cursor = conn.cursor()

        try:
            # Check for existing customer with the same phone (only if phone provided)
            if normalized_phone:
                cursor.execute(
                    "SELECT id, name FROM customers WHERE phone = ?",
                    (normalized_phone,)
                )
                existing = cursor.fetchone()
                if existing:
                    messagebox.showwarning(
                        "Duplicate Mobile Number",
                        f"A customer with mobile number {normalized_phone} is already registered as '{existing[1]}'.",
                        parent=self.window
                    )
                    conn.close()
                    self.phone_entry.focus_set()
                    return

            cursor.execute("""
            INSERT INTO customers(
                name,
                phone,
                address
            )
            VALUES (?, ?, ?)
            """, (
                name,
                normalized_phone,
                address
            ))
            conn.commit()

        except Exception as e:
            messagebox.showerror(
                "Database Error",
                str(e),
                parent=self.window
            )
            conn.close()
            return

        conn.close()

        display_phone = f" ({normalized_phone})" if normalized_phone else ""
        messagebox.showinfo(
            "Success",
            f"Customer '{name}'{display_phone} added successfully!",
            parent=self.window
        )

        self.refresh_callback()
        self.window.destroy()