import os
import shutil
import sqlite3

def deploy():
    src = r"C:\Users\sobti_ewvfrji\Desktop\BizDabba PHWP PD"
    dest = r"D:\BizDabba PHWP"
    
    print(f"Source folder: {src} (Exists: {os.path.exists(src)})")
    print(f"USB Drive D: accessible: {os.path.exists('D:')}")
    
    if not os.path.exists("D:\\"):
        print("ERROR: Drive D:\\ is not mounted or accessible!")
        return False
        
    print(f"Copying files from {src} to {dest}...")
    shutil.copytree(src, dest, dirs_exist_ok=True)
    print("Files copied successfully!")
    
    # Verify the database on the USB drive
    db_path = os.path.join(dest, "database", "business.db")
    if os.path.isfile(db_path):
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM products")
        prods = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM customers")
        custs = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM invoices")
        invs = cur.fetchone()[0]
        cur.execute("SELECT c.name, SUM(i.pending) FROM customers c JOIN invoices i ON c.id=i.customer_id GROUP BY c.id HAVING SUM(i.pending) > 0")
        pending = cur.fetchall()
        print(f"USB Database Verified:")
        print(f"  Products: {prods}")
        print(f"  Customers: {custs}")
        print(f"  Invoices: {invs}")
        print(f"  Pending Accounts in Ledger: {len(pending)}")
        for p in pending:
            print(f"    - {p[0]}: Rs. {p[1]:,.2f}")
        conn.close()
    else:
        print("WARNING: Database file not found on USB drive!")
        
    # Create top-level launcher batch file on D:\
    launcher_path = r"D:\Start BizDabba PHWP.bat"
    bat_content = "@echo off\r\ncd /d \"%~dp0BizDabba PHWP\"\r\nstart \"\" \"BizDabba_PHWP.exe\"\r\n"
    with open(launcher_path, "w", encoding="utf-8") as f:
        f.write(bat_content)
    print(f"Created convenient launcher shortcut: {launcher_path}")
    
    # List contents of D:\
    d_contents = os.listdir(r"D:\\")
    print(f"Current contents of D:\\: {d_contents}")
    return True

if __name__ == "__main__":
    deploy()
