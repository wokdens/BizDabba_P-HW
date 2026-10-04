import os
import shutil
import zipfile
import sys

# Ensure current dir is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config
import database

def assemble_release():
    desktop_dir = os.path.expanduser(r"~\Desktop")
    target_dir = os.path.join(desktop_dir, "BizDabba PHWP PD")
    zip_path = os.path.join(desktop_dir, "BizDabba_PHWP_PD.zip")
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    print(f"Assembling portable release at: {target_dir}")

    # 1. Clean existing
    if os.path.exists(target_dir):
        shutil.rmtree(target_dir, ignore_errors=True)
    if os.path.exists(zip_path):
        try:
            os.remove(zip_path)
        except Exception:
            pass

    os.makedirs(target_dir, exist_ok=True)
    os.makedirs(os.path.join(target_dir, "invoices"), exist_ok=True)
    os.makedirs(os.path.join(target_dir, "backups", "auto"), exist_ok=True)
    target_db_dir = os.path.join(target_dir, "database")
    os.makedirs(target_db_dir, exist_ok=True)

    # 2. Copy Executable and _internal
    src_dist = os.path.join(root_dir, "dist", "BizDabba_PHWP")
    exe_src = os.path.join(src_dist, "BizDabba_PHWP.exe")
    internal_src = os.path.join(src_dist, "_internal")

    assert os.path.isfile(exe_src), f"Executable not found at {exe_src}"
    assert os.path.isdir(internal_src), f"_internal folder not found at {internal_src}"

    shutil.copy2(exe_src, os.path.join(target_dir, "BizDabba_PHWP.exe"))
    print("Copied BizDabba_PHWP.exe")

    shutil.copytree(internal_src, os.path.join(target_dir, "_internal"))
    print("Copied _internal folder")

    # 3. Copy DEMO_PAINTS_HARDWARE_CATALOG.csv
    csv_src = os.path.join(root_dir, "DEMO_PAINTS_HARDWARE_CATALOG.csv")
    if os.path.isfile(csv_src):
        shutil.copy2(csv_src, os.path.join(target_dir, "DEMO_PAINTS_HARDWARE_CATALOG.csv"))
        print("Copied DEMO_PAINTS_HARDWARE_CATALOG.csv")

    # 4. Pre-seed database on Pen Drive
    target_db_path = os.path.join(target_db_dir, "business.db")
    old_db_path = database.DATABASE_PATH
    try:
        database.DATABASE_PATH = target_db_path
        database.create_tables()
        database.run_migrations()
        ok, msg = database.seed_paints_and_hardware_demo_data(force=True)
        assert ok, f"Demo data seeding failed: {msg}"
        database.safe_flush_pen_drive()
        print(f"Pre-seeded database verified OK: {target_db_path}")
    finally:
        database.DATABASE_PATH = old_db_path

    # 5. Create README_PEN_DRIVE_QUICKSTART.txt
    readme_content = """================================================================================
   BIZDABBA PHWP - PAINTS & HARDWARE PORTABLE PEN DRIVE EDITION
   Powered by wokdens.com | Delhi Wholesale & Retail Business Suite
================================================================================

WELCOME TO BIZDABBA PHWP (PORTABLE USB EDITION)
Designed specifically for Paints, Enamels, Putty, Brushes, Locks & Hardware 
retailers and wholesalers in Delhi (Chawri Bazar, Hauz Qazi, Rohini, Laxmi Nagar).

--------------------------------------------------------------------------------
1. CORE USP - PURE PEN DRIVE (USB) PORTABILITY
--------------------------------------------------------------------------------
• ZERO HOST LAPTOP INSTALLATION:
  This software does NOT install anything on the computer or laptop.
  Simply plug your Pen Drive into ANY Windows laptop or desktop and double-click:
     ==> BizDabba_PHWP.exe <==

• ZERO RESIDUAL TRACES:
  All business records, sales invoices, stock inventory, and customer ledgers 
  reside STRICTLY on this Pen Drive. When you unplug the drive, nothing remains 
  on the computer!

--------------------------------------------------------------------------------
2. ANTI-CORRUPTION & SAFE REMOVAL SAFEGUARD (Ctrl+S)
--------------------------------------------------------------------------------
Flash pen drives can corrupt if pulled out while background write operations 
are pending. BizDabba PHWP includes a dedicated protection system:

• "Save to Pen Drive" button on every screen (top navigation bar & dashboard).
• Global Shortcut: Press Ctrl + S at any time.
• Eye-catching 3-Second Confirmation Popup:
  Displays an animated countdown confirming:
  - SQLite WAL buffer flushed to flash memory.
  - Automatic rolling backup created on the pen drive.
  - Safe to unplug the pen drive or shut down the laptop.

• EVENING LOG-OFF ROUTINE:
  1. Press Ctrl + S (or click "Save to Pen Drive").
  2. Wait 3 seconds for the green confirmation toast to close.
  3. Close BizDabba PHWP.
  4. Unplug the Pen Drive and take your entire business data safely home!

--------------------------------------------------------------------------------
3. PRE-LOADED TRY-BEFORE-YOU-BUY DELHI DEMO DATA (10 CUSTOMERS / 8 PENDING)
--------------------------------------------------------------------------------
BizDabba PHWP comes pre-seeded with genuine Delhi market Paints & Hardware data:

• Curated Catalog (51 Items across 8 Categories):
  - Asian Paints: Apex Ultima (20L, 4L), Royale Luxury Emulsion, Tractor Emulsion
  - Berger: WeatherCoat All Guard, Walmasta Emulsion
  - Nerolac: Beauty Smooth Finish
  - Enamels & Primers: Apcolite Gloss Enamel, Red Oxide Primer, NC & Commercial Thinner
  - Putty & Distemper: TruCare Acrylic Putty, JK WallMaxx White Putty, Distemper
  - Tools: Paint Brushes (2", 3", 4"), 9" Roller sets, Waterproof Sandpaper (#120, #220), Masking Tape
  - Hardware & Locks: Brass Mortise Handle 6-lever locks, SS Butt Hinges, Aldrop, Tower Bolts
  - Fasteners: Drywall Gypsum Screws (1.5"), SS Wood Screws, Wire Nails (1kg), PVC Rawl Plugs
  - Plumbing: CPVC Brass Elbows, Ball Valves, Solvent Cement, Teflon Tape, Bib Taps
  - Hand Tools: Claw Hammers, 5m Steel Measuring Tapes, 8-in-1 Screwdriver sets, Hacksaws, Pliers

• Customer Ledgers (Exactly 10 Delhi Profiles - 8 with Pending Dues):
  1. Choudhary Builders & Developers (Dwarka)             [Pending: ₹ 12,500.00]
  2. Sharma Contractors & Builders (Chawri Bazar)         [Pending: ₹ 10,096.80]
  3. Gupta Construction Co. (Karol Bagh)                 [Pending: ₹  9,600.00]
  4. Verma Hardware & Sanitary Store (Rohini)             [Pending: ₹  4,350.00]
  5. Aggarwal Hardware & Mill Store (Hauz Qazi)           [Pending: ₹  3,920.00]
  6. Malhotra Interiors & Paint Decor (South Ex)          [Pending: ₹  3,850.00]
  7. Kapoor Sanitary & Plumbing Works (Pitampura)         [Pending: ₹  2,850.00]
  8. Rajesh Painter & Polish Works (Laxmi Nagar)          [Pending: ₹  2,680.00]
  9. Sunil Kumar (Civil Lines)                            [Fully Paid - ₹ 0.00 Dues]
 10. Walk-in Cash Customer                                [Fully Paid - ₹ 0.00 Dues]

• Demo Catalog File:
  - DEMO_PAINTS_HARDWARE_CATALOG.csv is included in this folder for reference 
    or re-import anytime.

--------------------------------------------------------------------------------
4. DUAL PRINTING: 80MM THERMAL POS & STANDARD A4 PDF ON ALL PENDING SCREENS
--------------------------------------------------------------------------------
Every page featuring pending payments supports BOTH printing modes:
• Ledger Page:
  - [Thermal Statement] : 80mm ESC/POS statement of account (Helix 1 calibrated / PDF fallback).
  - [Statement PDF (A4)]: Formal full-sheet Statement of Account with running debit/credit balance.
• Ledger Payment Dialog:
  - [80mm Thermal]      : Immediate receipt printout showing paid amount & remaining pending balance.
  - [A4 PDF]            : Full invoice document.
• Invoice History:
  - [80mm Thermal POS Receipt] & [Standard A4 PDF].
• Sales Invoice:
  - [Save & Print 80mm Receipt (Ctrl+P)] & [Save & Print A4 PDF (Ctrl+J)].

--------------------------------------------------------------------------------
5. SECURITY & PASSWORDS
--------------------------------------------------------------------------------
• Default Master Owner PIN: 8160
  (Required for administrative actions like editing shop profile, PIN change, 
  database restore, and profit Z-report).
• 1-Click Role Toggle:
  Switch between "Staff Mode" (safe for counter staff) and "Admin Mode" 
  from the top-right button.
• Master Password for Encrypted CSV Exports: Wokdens@CSV#2026

--------------------------------------------------------------------------------
   ⚡ Powered by wokdens.com | Quality Software for Growing Businesses
================================================================================
"""
    readme_path = os.path.join(target_dir, "README_PEN_DRIVE_QUICKSTART.txt")
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(readme_content)
    print("Created README_PEN_DRIVE_QUICKSTART.txt")

    # 6. Create ZIP Archive
    print(f"Creating ZIP archive at {zip_path}...")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(target_dir):
            for file in files:
                file_full = os.path.join(root, file)
                rel_path = os.path.relpath(file_full, os.path.dirname(target_dir))
                zf.write(file_full, rel_path)
    
    zip_size_mb = os.path.getsize(zip_path) / (1024 * 1024)
    print(f"Successfully generated ZIP: {zip_path} ({zip_size_mb:.2f} MB)")
    print("Portable Pen Drive release assembly COMPLETE!")

if __name__ == "__main__":
    assemble_release()
