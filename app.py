import atexit
import ctypes
import os
import sys
import tkinter as tk
from tkinter import ttk
from ctypes import wintypes

from database import (
    create_tables,
    reset_application_data,
    run_migrations,
    trigger_auto_backup,
    close_database_on_exit
)

from ui.main_window import MainWindow

# Enable Windows High-DPI scaling awareness for crisp rendering across all screen resolutions
if sys.platform == "win32":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # Per-monitor DPI aware
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()  # System DPI aware fallback
        except Exception:
            pass

# =========================
# SINGLE INSTANCE LOCK
# =========================
_app_mutex = None

def enforce_single_instance(app_title="BizDibba Diwali v2.0 by wokdens.com"):
    global _app_mutex
    if sys.platform == "win32":
        try:
            kernel32 = ctypes.windll.kernel32
            kernel32.CreateMutexW.restype = wintypes.HANDLE
            kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
            kernel32.GetLastError.restype = wintypes.DWORD

            _app_mutex = kernel32.CreateMutexW(None, False, r"Local\Wokdens_BizDibba_Diwali_v2_SingleInstance_Mutex")
            if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
                user32 = ctypes.windll.user32
                hwnd = user32.FindWindowW(None, app_title)
                if hwnd:
                    user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                    user32.SetForegroundWindow(hwnd)
                sys.exit(0)
        except Exception as e:
            print(f"Single instance check notice: {e}")

enforce_single_instance("BizDibba Diwali v2.0 by wokdens.com")

# =========================
# CREATE DATABASE TABLES & MIGRATIONS
# =========================

if "--reset" in sys.argv:
    reset_application_data()
    print("Application data cleared successfully.")
    sys.exit(0)

create_tables()

run_migrations()

# Silent daily auto-backup on application start
try:
    trigger_auto_backup(reason="daily")
except Exception as e:
    print(f"Startup auto-backup notice: {e}")


# =========================
# START APPLICATION
# =========================

root = tk.Tk()

# Make buttons easier to read and tap across the app.
root.option_add("*Button.Font", "Arial 13 bold")
root.option_add("*Button.padX", 10)
root.option_add("*Button.padY", 6)

style = ttk.Style()
style.configure("TButton", font=("Arial", 13, "bold"), padding=(12, 8))

app = MainWindow(root)

# Register clean exit handlers
def on_closing():
    try:
        close_database_on_exit()
    except Exception:
        pass
    finally:
        global _app_mutex
        if _app_mutex and sys.platform == "win32":
            try:
                ctypes.windll.kernel32.CloseHandle(_app_mutex)
            except Exception:
                pass
        root.destroy()

root.protocol("WM_DELETE_WINDOW", on_closing)
atexit.register(close_database_on_exit)

root.mainloop()

