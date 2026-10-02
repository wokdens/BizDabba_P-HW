import tkinter as tk
from tkinter import ttk


class AutocompleteCombobox(tk.Frame):
    """
    A modern, user-friendly Autocomplete Combobox with:
    - Floating overlay dropdown (Zero layout displacement / no pushing other elements)
    - Integrated vertical scrollbar for large product/customer lists
    - Full keyboard navigation (Down/Up arrow navigation, Enter to select, Escape to close)
    - Mouse hover live selection and single-click pick
    - Multi-word search matching (e.g. '2.5 wire' matches 'Polycab 2.5 sq mm Wire')
    - Bulletproof event dispatcher that prevents external bind calls from wiping internal lifecycle handlers
    """

    def __init__(self, parent, width=30, placeholder="", font=("Arial", 11)):
        super().__init__(parent)

        self.completion_list = []
        self.current_matches = []
        self.placeholder = placeholder
        self._font = font

        # Main Entry Field with High-Visibility Focus Highlight
        self.entry = tk.Entry(
            self,
            width=width,
            font=font,
            relief="solid",
            bd=1,
            highlightthickness=1,
            highlightbackground="#ced4da",
            highlightcolor="#2563eb",
            bg="#ffffff",
            fg="#212529"
        )
        self.entry.pack(fill="x", expand=True, ipady=6)

        # Fallback dummy listbox to avoid AttributeError on legacy config calls
        self.listbox = tk.Listbox(self)
        self.popup = None
        self.scrollbar = None
        self._listbox_font = font

        # Custom callback registries
        self._keyrelease_callbacks = []
        self._return_callbacks = []
        self._selection_callbacks = []
        self._focusout_callbacks = []
        self._focusin_callbacks = []

        # Internal Bindings on Entry
        self.entry.bind("<KeyRelease>", self._on_key_release)
        self.entry.bind("<Down>", self._on_down_arrow)
        self.entry.bind("<Up>", self._on_up_arrow)
        self.entry.bind("<Tab>", self._on_entry_tab)
        self.entry.bind("<Shift-Tab>", lambda e: self.hide_popup())

        self.entry.bind("<Return>", self._on_enter_pressed)
        self.entry.bind("<KP_Enter>", self._on_enter_pressed)
        self.entry.bind("<Escape>", lambda e: self.hide_popup())
        self.entry.bind("<FocusIn>", self._on_entry_focus_in)
        self.entry.bind("<FocusOut>", self._on_entry_focus_out)
        self.entry.bind("<Button-1>", self._on_entry_clicked)

        # Protect self.entry.bind from clobbering internal handlers
        _orig_entry_bind = self.entry.bind

        def safe_entry_bind(sequence=None, func=None, add=None):
            if sequence == "<KeyRelease>":
                if func and func not in self._keyrelease_callbacks:
                    self._keyrelease_callbacks.append(func)
                return
            elif sequence in ("<Return>", "<KP_Enter>"):
                if func and func not in self._return_callbacks:
                    self._return_callbacks.append(func)
                return
            elif sequence == "<<ComboboxSelected>>":
                if func and func not in self._selection_callbacks:
                    self._selection_callbacks.append(func)
                return
            elif sequence == "<FocusOut>":
                if func and func not in self._focusout_callbacks:
                    self._focusout_callbacks.append(func)
                return
            return _orig_entry_bind(sequence, func, add="+")

        self.entry.bind = safe_entry_bind


    # =========================
    # PUBLIC API & PROPERTIES
    # =========================

    def set_completion_list(self, completion_list):
        """Set or update the list of items for autocomplete."""
        self.completion_list = [str(item) for item in completion_list if item is not None]

    def get(self):
        """Get the current text in the entry."""
        return self.entry.get()

    def set(self, value):
        """Set the text in the entry."""
        self.entry.delete(0, tk.END)
        if value:
            self.entry.insert(0, str(value))
        self.hide_popup()

    def focus_set(self):
        """Focus the entry."""
        self.entry.focus_set()

    def bind(self, sequence=None, func=None, add=None):
        """Register callbacks safely without overwriting internal handlers."""
        if not sequence or not func:
            return
        if sequence == "<KeyRelease>":
            if func not in self._keyrelease_callbacks:
                self._keyrelease_callbacks.append(func)
        elif sequence in ("<Return>", "<KP_Enter>"):
            if func not in self._return_callbacks:
                self._return_callbacks.append(func)
        elif sequence == "<<ComboboxSelected>>":
            if func not in self._selection_callbacks:
                self._selection_callbacks.append(func)
        elif sequence == "<FocusOut>":
            if func not in self._focusout_callbacks:
                self._focusout_callbacks.append(func)
        else:
            super().bind(sequence, func, add="+")
            self.entry.bind(sequence, func, add="+")




    # =========================
    # POPUP WINDOW MANAGEMENT
    # =========================

    def _create_popup(self):
        """Create the floating borderless popup window."""
        if self.popup and self.popup.winfo_exists():
            return

        self.popup = tk.Toplevel(self)
        self.popup.wm_overrideredirect(True)
        self.popup.wm_attributes("-topmost", True)

        container = tk.Frame(
            self.popup,
            bd=1,
            relief="solid",
            bg="#0066cc"
        )
        container.pack(fill="both", expand=True)

        inner = tk.Frame(container, bg="#ffffff")
        inner.pack(fill="both", expand=True, padx=1, pady=1)

        self.scrollbar = ttk.Scrollbar(inner, orient="vertical")
        self.listbox = tk.Listbox(
            inner,
            font=self._listbox_font,
            selectmode="single",
            bg="#ffffff",
            fg="#212529",
            selectbackground="#0078d7",
            selectforeground="#ffffff",
            activestyle="none",
            highlightthickness=0,
            bd=0,
            yscrollcommand=self.scrollbar.set
        )
        self.scrollbar.config(command=self.listbox.yview)

        self.scrollbar.pack(side="right", fill="y")
        self.listbox.pack(side="left", fill="both", expand=True)

        # Listbox Bindings
        self.listbox.bind("<ButtonRelease-1>", self._on_listbox_select)
        self.listbox.bind("<Return>", self._on_listbox_enter)
        self.listbox.bind("<KP_Enter>", self._on_listbox_enter)
        self.listbox.bind("<Escape>", lambda e: self.hide_popup(focus_entry=True))
        self.listbox.bind("<Up>", self._on_listbox_up)
        self.listbox.bind("<Down>", self._on_listbox_down)
        self.listbox.bind("<Tab>", self._on_listbox_down)
        self.listbox.bind("<Shift-Tab>", self._on_listbox_up)

        self.listbox.bind("<Motion>", self._on_mouse_motion)
        self.listbox.bind("<FocusOut>", self._on_listbox_focus_out)


    def show_popup(self, matches):
        """Show the floating popup positioned right below the entry."""
        if not matches:
            self.hide_popup()
            return

        self.current_matches = matches
        self._create_popup()

        # Update Listbox Items
        self.listbox.delete(0, tk.END)
        for item in matches:
            self.listbox.insert(tk.END, item)

        # Highlight first match by default
        self.listbox.selection_set(0)
        self.listbox.activate(0)

        # Calculate exact geometry
        self.update_idletasks()
        try:
            x = self.entry.winfo_rootx()
            y = self.entry.winfo_rooty() + self.entry.winfo_height() + 2
            w = max(self.entry.winfo_width(), 260)
            items_count = min(len(matches), 7)
            h = items_count * 28 + 6

            # Ensure within screen bounds
            screen_h = self.winfo_screenheight()
            if y + h > screen_h - 40:
                y = self.entry.winfo_rooty() - h - 2

            self.popup.geometry(f"{w}x{h}+{x}+{y}")
            self.popup.deiconify()
            self.popup.lift()
        except Exception:
            pass

    def hide_popup(self, focus_entry=False):
        """Hide the floating popup."""
        if self.popup and self.popup.winfo_exists():
            self.popup.withdraw()
        if focus_entry:
            self.entry.focus_set()

    # =========================
    # EVENT HANDLERS
    # =========================

    def _on_key_release(self, event):
        """Filter matches as the user types."""
        # Ignore navigation keys that are handled separately
        if event.keysym in ("Up", "Down", "Return", "KP_Enter", "Escape", "Tab", "Shift_L", "Shift_R", "Control_L", "Control_R"):
            return

        typed = self.entry.get().strip().lower()
        if not typed:
            self.hide_popup()
            self._notify_change()
        else:
            # Smart Multi-Word Search (e.g., '2.5 wire' matches 'Polycab 2.5 sq mm Wire')
            search_terms = typed.split()
            matches = []
            for item in self.completion_list:
                item_lower = item.lower()
                if all(term in item_lower for term in search_terms):
                    matches.append(item)

            if matches:
                self.show_popup(matches)
            else:
                self.hide_popup()

        # Run registered keyrelease callbacks
        for cb in list(self._keyrelease_callbacks):
            try:
                cb(event)
            except Exception:
                pass


    def _on_entry_clicked(self, event):
        """Open all or filtered items on click."""
        typed = self.entry.get().strip().lower()
        if typed:
            search_terms = typed.split()
            matches = [
                item for item in self.completion_list
                if all(t in item.lower() for t in search_terms)
            ]
            if matches:
                self.show_popup(matches)
        elif self.completion_list:
            self.show_popup(self.completion_list[:30])

    def _on_entry_tab(self, event):
        """Tab key on entry: if popup is viewable, enter listbox; otherwise normal tab."""
        if self.popup and self.popup.winfo_exists() and self.popup.winfo_viewable() and self.listbox and self.listbox.size() > 0:
            self.listbox.focus_set()
            sel = self.listbox.curselection()
            if not sel:
                self.listbox.selection_set(0)
                self.listbox.activate(0)
                self.listbox.see(0)
            return "break"
        self.hide_popup()
        return None

    def _on_down_arrow(self, event):
        """Move from entry into popup listbox."""
        if self.popup and self.popup.winfo_exists() and self.popup.winfo_viewable():
            if self.listbox and self.listbox.size() > 0:
                self.listbox.focus_set()
                sel = self.listbox.curselection()
                if not sel:
                    nxt = 0
                else:
                    nxt = min(sel[0] + 1, self.listbox.size() - 1)
                self.listbox.selection_clear(0, tk.END)
                self.listbox.selection_set(nxt)
                self.listbox.activate(nxt)
                self.listbox.see(nxt)
            return "break"
        else:
            # Open popup with all items if available
            typed = self.entry.get().strip().lower()
            if typed:
                matches = [item for item in self.completion_list if typed in item.lower()]
                if matches:
                    self.show_popup(matches)
            elif self.completion_list:
                self.show_popup(self.completion_list[:30])
            return "break"

    def _on_up_arrow(self, event):
        """Navigate up."""
        if self.popup and self.popup.winfo_exists() and self.popup.winfo_viewable():
            if self.listbox and self.listbox.size() > 0:
                sel = self.listbox.curselection()
                if sel and sel[0] > 0:
                    prev_idx = sel[0] - 1
                    self.listbox.selection_clear(0, tk.END)
                    self.listbox.selection_set(prev_idx)
                    self.listbox.activate(prev_idx)
                    self.listbox.see(prev_idx)
                else:
                    self.entry.focus_set()
            return "break"

    def _on_listbox_down(self, event):
        """Down arrow or Tab inside listbox: move selection down one item."""
        if self.listbox and self.listbox.size() > 0:
            sel = self.listbox.curselection()
            cur = sel[0] if sel else 0
            nxt = min(cur + 1, self.listbox.size() - 1)
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(nxt)
            self.listbox.activate(nxt)
            self.listbox.see(nxt)
        return "break"

    def _on_listbox_up(self, event):
        """Up arrow or Shift-Tab inside listbox: move selection up one item; if at top, return focus to entry."""
        if self.listbox and self.listbox.size() > 0:
            sel = self.listbox.curselection()
            if not sel or sel[0] == 0:
                self.entry.focus_set()
                return "break"
            prev_idx = sel[0] - 1
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(prev_idx)
            self.listbox.activate(prev_idx)
            self.listbox.see(prev_idx)
        return "break"


    def _on_enter_pressed(self, event):
        """Enter key on entry: select first match if popup is visible, and trigger selection callbacks."""
        if self.popup and self.popup.winfo_exists() and self.popup.winfo_viewable() and self.listbox:
            sel = self.listbox.curselection()
            if sel and sel[0] < self.listbox.size():
                val = self.listbox.get(sel[0])
                self.set(val)
                self.hide_popup()
                self._notify_change()
            elif self.current_matches:
                self.set(self.current_matches[0])
                self.hide_popup()
                self._notify_change()
            else:
                self.hide_popup()
        else:
            self.hide_popup()
            self._notify_change()

        # Run registered return callbacks
        for cb in list(self._return_callbacks):
            try:
                cb(event)
            except Exception:
                pass

    def _on_listbox_enter(self, event):
        """Enter key on listbox: select and trigger change notification."""
        sel = self.listbox.curselection()
        if sel and sel[0] < self.listbox.size():
            val = self.listbox.get(sel[0])
            self.set(val)
            self._notify_change()
        self.hide_popup(focus_entry=True)
        # Forward Enter event to entry so parent navigation handlers fire
        try:
            self.entry.event_generate("<Return>")
        except Exception:
            pass
        return "break"

    def _on_listbox_select(self, event):
        """Mouse click on listbox item."""
        sel = self.listbox.curselection()
        if sel and sel[0] < self.listbox.size():
            val = self.listbox.get(sel[0])
            self.set(val)
            self._notify_change()
        self.hide_popup(focus_entry=True)


    def _on_mouse_motion(self, event):
        """Hover highlight item in listbox."""
        if self.listbox:
            idx = self.listbox.nearest(event.y)
            if 0 <= idx < self.listbox.size():
                self.listbox.selection_clear(0, tk.END)
                self.listbox.selection_set(idx)
                self.listbox.activate(idx)

    def _on_entry_focus_in(self, event):
        """Highlight entry with high-visibility blue border on focus."""
        try:
            self.entry.config(
                highlightthickness=2,
                highlightbackground="#2563eb",
                highlightcolor="#2563eb",
                bg="#f0f7ff"
            )
            self.entry.selection_range(0, tk.END)
        except Exception:
            pass
        for cb in list(self._focusin_callbacks):
            try:
                cb(event)
            except Exception:
                pass

    def _on_entry_focus_out(self, event):
        """Close popup and restore normal entry styling when focus leaves."""
        try:
            self.entry.config(
                highlightthickness=1,
                highlightbackground="#ced4da",
                highlightcolor="#ced4da",
                bg="#ffffff"
            )
        except Exception:
            pass
        self.after(180, self._check_focus_loss)
        for cb in list(self._focusout_callbacks):
            try:
                cb(event)
            except Exception:
                pass

    def _on_listbox_focus_out(self, event):
        """Close popup when listbox loses focus."""
        self.after(180, self._check_focus_loss)


    def _check_focus_loss(self):
        """Verify if neither entry nor listbox has focus before hiding popup."""
        try:
            focused = self.focus_get()
            if focused not in (self.entry, self.listbox, self.scrollbar):
                self.hide_popup()
        except Exception:
            self.hide_popup()

    def _notify_change(self):
        """Emit ComboboxSelected event and invoke callbacks to trigger autofill listeners."""
        try:
            self.event_generate("<<ComboboxSelected>>")
            self.entry.event_generate("<<ComboboxSelected>>")
            for cb in self._selection_callbacks:
                try:
                    cb(None)
                except Exception:
                    pass
        except Exception:
            pass




