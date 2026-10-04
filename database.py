import sqlite3
import os
import time
import hashlib
from datetime import datetime, timedelta

from config import DATABASE_PATH, AUTO_BACKUPS_DIR




# =========================
# CONNECTION
# =========================

def get_connection():
    
    # Ensure database directory exists
    db_dir = os.path.dirname(DATABASE_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    
    try:
        conn = sqlite3.connect(
            DATABASE_PATH,
            timeout=10.0
        )
        # Enable WAL mode for better concurrency
        conn.execute("PRAGMA journal_mode=WAL")
        return conn
    except sqlite3.OperationalError as e:
        raise Exception(f"Failed to open database at {DATABASE_PATH}: {str(e)}")

# =========================
# AUTO MIGRATIONS
# =========================

def column_exists(
    table_name,
    column_name
):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(f"""
    PRAGMA table_info({table_name})
    """)

    columns = cursor.fetchall()

    conn.close()

    for column in columns:

        if column[1] == column_name:
            return True

    return False



def run_migrations():

    conn = get_connection()

    cursor = conn.cursor()

    # =========================
    # INVOICES TABLE
    # =========================

    if not column_exists(
        "invoices",
        "invoice_number"
    ):

        cursor.execute("""
        ALTER TABLE invoices
        ADD COLUMN invoice_number TEXT
        """)

    if not column_exists(
        "invoices",
        "invoice_date"
    ):

        cursor.execute("""
        ALTER TABLE invoices
        ADD COLUMN invoice_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        """)

    cursor.execute("""
    UPDATE invoices
    SET invoice_date = datetime('now', 'localtime')
    WHERE invoice_date IS NULL
    """)

    if not column_exists(
        "invoices",
        "note"
    ):


        cursor.execute("""
        ALTER TABLE invoices
        ADD COLUMN note TEXT DEFAULT ''
        """)

    if not column_exists(
        "invoices",
        "status"
    ):
        cursor.execute("""
        ALTER TABLE invoices
        ADD COLUMN status TEXT DEFAULT 'ACTIVE'
        """)
        cursor.execute("""
        UPDATE invoices
        SET status = 'ACTIVE'
        WHERE status IS NULL
        """)

    # =========================
    # PRODUCTS TABLE
    # =========================

    if not column_exists(
        "products",
        "category"
    ):

        cursor.execute("""
        ALTER TABLE products
        ADD COLUMN category TEXT
        """)

    if not column_exists(
        "products",
        "unit"
    ):

        cursor.execute("""
        ALTER TABLE products
        ADD COLUMN unit TEXT
        """)

    if not column_exists(
        "products",
        "discount_base"
    ):

        cursor.execute("""
        ALTER TABLE products
        ADD COLUMN discount_base TEXT DEFAULT 'Price'
        """)

    # =========================
    # CUSTOMERS TABLE
    # =========================

    if not column_exists(
        "customers",
        "phone"
    ):

        cursor.execute("""
        ALTER TABLE customers
        ADD COLUMN phone TEXT
        """)

    if not column_exists(
        "customers",
        "address"
    ):

        cursor.execute("""
        ALTER TABLE customers
        ADD COLUMN address TEXT
        """)

    # =========================
    # INVOICE ITEMS TABLE
    # =========================

    if not column_exists(
        "invoice_items",
        "total"
    ):

        cursor.execute("""
        ALTER TABLE invoice_items
        ADD COLUMN total REAL
        """)

    if not column_exists(
        "invoice_items",
        "unit"
    ):

        cursor.execute("""
        ALTER TABLE invoice_items
        ADD COLUMN unit TEXT
        """)

    if not column_exists(
        "invoice_items",
        "custom_price"
    ):

        cursor.execute("""
        ALTER TABLE invoice_items
        ADD COLUMN custom_price REAL
        """)

    if not column_exists(
        "invoice_items",
        "discount_base"
    ):

        cursor.execute("""
        ALTER TABLE invoice_items
        ADD COLUMN discount_base TEXT DEFAULT 'Price'
        """)

    if not column_exists(
        "invoice_items",
        "mrp"
    ):

        cursor.execute("""
        ALTER TABLE invoice_items
        ADD COLUMN mrp REAL
        """)

    if not column_exists(
        "invoice_items",
        "increase"
    ):

        cursor.execute("""
        ALTER TABLE invoice_items
        ADD COLUMN increase REAL DEFAULT 0.0
        """)

    # =========================
    # APP SETTINGS TABLE
    # =========================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS app_settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)

    # =========================
    # STOCK ADJUSTMENTS TABLE
    # =========================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS stock_adjustments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER,
        adjustment_type TEXT,
        quantity INTEGER,
        reason TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # =========================
    # SECURITY AUDIT LOGS TABLE
    # =========================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS security_audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        action_type TEXT,
        description TEXT,
        authorized_by TEXT DEFAULT 'Owner PIN',
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # =========================
    # PRODUCTS UNIQUE CONSTRAINT & DEDUPLICATION
    # =========================
    try:
        cursor.execute("""
            SELECT LOWER(TRIM(COALESCE(category, 'General'))), LOWER(TRIM(name))
            FROM products
            GROUP BY LOWER(TRIM(COALESCE(category, 'General'))), LOWER(TRIM(name))
            HAVING COUNT(id) > 1
        """)
        dup_groups = cursor.fetchall()
        for cat_l, name_l in dup_groups:
            cursor.execute("""
                SELECT id, stock FROM products
                WHERE LOWER(TRIM(COALESCE(category, 'General'))) = ? AND LOWER(TRIM(name)) = ?
                ORDER BY id ASC
            """, (cat_l, name_l))
            dups = cursor.fetchall()
            if len(dups) > 1:
                keep_id = dups[0][0]
                extra_stock = sum(d[1] for d in dups[1:] if d[1] is not None)
                if extra_stock > 0:
                    cursor.execute("UPDATE products SET stock = stock + ? WHERE id = ?", (extra_stock, keep_id))
                for extra in dups[1:]:
                    cursor.execute("DELETE FROM products WHERE id = ?", (extra[0],))

        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_products_unique_cat_name
            ON products(LOWER(TRIM(COALESCE(category, 'General'))), LOWER(TRIM(name)))
        """)
    except Exception as e:
        print(f"Product unique index notice: {e}")

    conn.commit()

    conn.close()



# =========================
# CREATE TABLES
# =========================

def create_tables():

    conn = get_connection()

    cursor = conn.cursor()

    # PRODUCTS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT DEFAULT 'General',
        name TEXT NOT NULL,
        mrp REAL DEFAULT 0.0,
        purchase_price REAL DEFAULT 0.0,
        selling_price REAL DEFAULT 0.0,
        unit TEXT DEFAULT 'Pcs',
        stock INTEGER DEFAULT 0,
        discount_base TEXT DEFAULT 'Price'
    )
    """)

    # CUSTOMERS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        phone TEXT DEFAULT '',
        address TEXT DEFAULT ''
    )
    """)

    # INVOICES
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_number TEXT,
        customer_id INTEGER,
        total REAL,
        paid REAL,
        pending REAL,
        invoice_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        note TEXT DEFAULT '',
        status TEXT DEFAULT 'ACTIVE'
    )
    """)

    # INVOICE ITEMS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS invoice_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_id INTEGER,
        product_id INTEGER,
        quantity INTEGER,
        mrp REAL DEFAULT 0.0,
        price REAL DEFAULT 0.0,
        custom_price REAL DEFAULT 0.0,
        discount REAL DEFAULT 0.0,
        total REAL DEFAULT 0.0,
        unit TEXT DEFAULT 'Pcs',
        discount_base TEXT DEFAULT 'Price'
    )
    """)

    # CATEGORIES
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE
    )
    """)

    # APP SETTINGS & SECURITY
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS app_settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)

    # STOCK ADJUSTMENTS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS stock_adjustments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER,
        adjustment_type TEXT,
        quantity INTEGER,
        reason TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # SECURITY AUDIT LOGS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS security_audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        action_type TEXT,
        description TEXT,
        authorized_by TEXT DEFAULT 'Owner PIN',
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()

    conn.close()

    # Automatically run migrations to guarantee schema synchronization
    run_migrations()

    # Automatically initialize default Admin PIN to 8160 if not already configured
    if not get_setting("admin_pin_hash"):
        set_setting("admin_pin_hash", hash_pin("8160"))

    # Auto-seed Paints & Hardware demo data if database is freshly created
    if get_total_products() == 0 and get_setting("demo_seed_skipped") != "1":
        seed_paints_and_hardware_demo_data()




# =========================
# SETTINGS & ADMIN SECURITY
# =========================

def get_setting(key, default=None):
    """Retrieve an application setting value by key."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("CREATE TABLE IF NOT EXISTS app_settings (key TEXT PRIMARY KEY, value TEXT)")
        cursor.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row[0] if row else default
    finally:
        conn.close()


def set_setting(key, value):
    """Save or update an application setting."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("CREATE TABLE IF NOT EXISTS app_settings (key TEXT PRIMARY KEY, value TEXT)")
        cursor.execute("""
        INSERT INTO app_settings (key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value
        """, (key, str(value)))
        conn.commit()
    finally:
        conn.close()


def get_shop_details():
    """Retrieve shop name, phone, and address from settings (with config.py defaults)."""
    from config import SHOP_NAME, SHOP_PHONE, SHOP_ADDRESS
    name = get_setting("shop_name", SHOP_NAME)
    phone = get_setting("shop_phone", SHOP_PHONE)
    address = get_setting("shop_address", SHOP_ADDRESS)
    return {"name": name, "phone": phone, "address": address}


def set_shop_details(name, phone, address):
    """Save custom shop details in app_settings."""
    set_setting("shop_name", name.strip())
    set_setting("shop_phone", phone.strip())
    set_setting("shop_address", address.strip())


# =========================
# SECURITY AUDIT LOGGING
# =========================

def record_audit_log(action_type, description, authorized_by="Owner PIN"):
    """
    Logs an authorized security event, rate override, payment clearance, or data export.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS security_audit_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, action_type TEXT, description TEXT, authorized_by TEXT DEFAULT 'Owner PIN', timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        cursor.execute("""
        INSERT INTO security_audit_logs (action_type, description, authorized_by, timestamp)
        VALUES (?, ?, ?, datetime('now', 'localtime'))
        """, (action_type, description, authorized_by))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Audit log recording error: {e}")


def get_audit_logs(limit=150):
    """Retrieves recent security audit logs in reverse chronological order."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("CREATE TABLE IF NOT EXISTS security_audit_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, action_type TEXT, description TEXT, authorized_by TEXT DEFAULT 'Owner PIN', timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        cursor.execute("""
        SELECT
            id,
            COALESCE(strftime('%d-%m-%Y %I:%M %p', timestamp), timestamp),
            action_type,
            description,
            authorized_by
        FROM security_audit_logs
        ORDER BY id DESC
        LIMIT ?
        """, (limit,))
        return cursor.fetchall()
    finally:
        conn.close()


def hash_pin(pin_str):
    """Generate SHA-256 hash for PIN security."""
    return hashlib.sha256(str(pin_str).strip().encode("utf-8")).hexdigest()



# Permanent Offline Developer Master Rescue PIN Hash (SHA-256 of 99888160)
# Known exclusively to developer for remote offline emergency recovery
MASTER_DEVELOPER_PIN_HASH = "36513f7d2be3d434e6ca450b429ff927f3e7bed84cc51d5d8c5c1c06c4c453c2"


def is_master_developer_pin(entered_pin):
    """Check if the entered PIN matches the Developer Master Rescue Key."""
    return hash_pin(entered_pin) == MASTER_DEVELOPER_PIN_HASH


def set_admin_pin(new_pin):
    """Set or update the Owner/Admin PIN."""
    pin_hash = hash_pin(new_pin)
    set_setting("admin_pin_hash", pin_hash)


def verify_admin_pin(entered_pin):
    """Verify if the entered PIN matches the Owner/Admin PIN (Default: 8160) or Developer Master Rescue PIN."""
    entered_hash = hash_pin(entered_pin)

    # 1. Developer Master Rescue Key check (100% Offline)
    if entered_hash == MASTER_DEVELOPER_PIN_HASH:
        record_audit_log("MASTER_RESCUE_AUTH", "Admin Mode authorized using Developer Master Rescue Key")
        return True

    # 2. Regular User/Admin PIN check from database
    stored_hash = get_setting("admin_pin_hash")
    if not stored_hash:
        default_hash = hash_pin("8160")
        set_setting("admin_pin_hash", default_hash)
        stored_hash = default_hash

    return entered_hash == stored_hash





def reset_application_data():
    """Clear all transactional and inventory data so the app starts completely fresh."""

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM invoice_items")
    cursor.execute("DELETE FROM invoices")
    cursor.execute("DELETE FROM products")
    cursor.execute("DELETE FROM customers")
    cursor.execute("DELETE FROM categories")
    cursor.execute("DELETE FROM stock_adjustments")

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sqlite_sequence'")
    if cursor.fetchone():
        cursor.execute("DELETE FROM sqlite_sequence")

    cursor.execute("INSERT OR REPLACE INTO app_settings(key, value) VALUES('demo_seed_skipped', '1')")

    conn.commit()
    conn.close()


# =========================
# CATEGORY FUNCTIONS
# =========================

def add_category(category_name):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
    INSERT OR IGNORE INTO categories(name)
    VALUES(?)
    """, (
        category_name,
    ))

    conn.commit()

    conn.close()


def get_all_categories():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
    SELECT name
    FROM categories
    ORDER BY name
    """)

    data = cursor.fetchall()

    conn.close()

    return [row[0] for row in data]


# =========================
# PRODUCT FUNCTIONS
# =========================

def is_product_duplicate(name, category="General", exclude_id=None):
    """
    Check if a product with the same category and name already exists (case-insensitive and trimmed).
    Returns (id, category, name, selling_price, stock, unit) if found, else None.
    """
    if not name or not str(name).strip():
        return None

    cat_clean = (str(category).strip() if category else "General") or "General"
    name_clean = str(name).strip()

    conn = get_connection()
    cursor = conn.cursor()

    if exclude_id is not None:
        cursor.execute("""
            SELECT id, category, name, selling_price, stock, unit
            FROM products
            WHERE LOWER(TRIM(COALESCE(category, 'General'))) = LOWER(TRIM(?))
              AND LOWER(TRIM(name)) = LOWER(TRIM(?))
              AND id != ?
            LIMIT 1
        """, (cat_clean, name_clean, int(exclude_id)))
    else:
        cursor.execute("""
            SELECT id, category, name, selling_price, stock, unit
            FROM products
            WHERE LOWER(TRIM(COALESCE(category, 'General'))) = LOWER(TRIM(?))
              AND LOWER(TRIM(name)) = LOWER(TRIM(?))
            LIMIT 1
        """, (cat_clean, name_clean))

    row = cursor.fetchone()
    conn.close()
    return row

def add_product(

    name,
    mrp,
    purchase_price,
    selling_price,
    stock,
    unit="Pcs",
    category="General",
    discount_base="Price"
):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO products(
        category,
        name,
        mrp,
        purchase_price,
        selling_price,
        unit,
        stock,
        discount_base
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        category if category else "General",
        name,
        mrp,
        purchase_price,
        selling_price,
        unit if unit else "Pcs",
        stock,
        discount_base if discount_base else "Price"
    ))

    conn.commit()

    conn.close()


def get_all_products():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        id,
        category,
        name,
        mrp,
        purchase_price,
        selling_price,
        stock,
        discount_base
    FROM products
    """)

    products = cursor.fetchall()

    conn.close()

    return products


def get_product_names():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        category,
        name
    FROM products
    WHERE stock > 0
    ORDER BY category, name
    """)

    data = cursor.fetchall()

    conn.close()

    formatted_products = []

    for row in data:

        category = row[0] if row[0] else "General"

        name = row[1]

        formatted_products.append(
            f"{category} - {name}"
        )

    return formatted_products


def get_product_by_name(product_name):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        id,
        name,
        selling_price,
        stock
    FROM products
    WHERE name = ?
    """, (
        product_name,
    ))

    product = cursor.fetchone()

    conn.close()

    return product


def update_stock(product_id, new_stock):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
    UPDATE products
    SET stock = ?
    WHERE id = ?
    """, (
        new_stock,
        product_id
    ))

    conn.commit()

    conn.close()


def renumber_products_sequential():
    """
    Renumbers all products sequentially starting from 1 to N.
    Safely updates foreign key references in invoice_items and stock_adjustments.
    Resets sqlite_sequence to N (or 0 if no products).
    Returns (success: bool, count: int, message: str).
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM products ORDER BY id ASC")
        rows = cursor.fetchall()
        if not rows:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sqlite_sequence'")
            if cursor.fetchone():
                cursor.execute("DELETE FROM sqlite_sequence WHERE name = 'products'")
            conn.commit()
            return True, 0, "Inventory is empty. Product ID sequence reset to 0."

        # Re-assign IDs using negative temporary values to prevent PRIMARY KEY collisions
        for idx, r in enumerate(rows):
            old_id = r[0]
            temp_id = -(idx + 1)
            cursor.execute("UPDATE products SET id = ? WHERE id = ?", (temp_id, old_id))
            cursor.execute("UPDATE invoice_items SET product_id = ? WHERE product_id = ?", (temp_id, old_id))
            cursor.execute("UPDATE stock_adjustments SET product_id = ? WHERE product_id = ?", (temp_id, old_id))

        # Assign clean 1..N IDs
        for idx in range(len(rows)):
            temp_id = -(idx + 1)
            new_id = idx + 1
            cursor.execute("UPDATE products SET id = ? WHERE id = ?", (new_id, temp_id))
            cursor.execute("UPDATE invoice_items SET product_id = ? WHERE product_id = ?", (new_id, temp_id))
            cursor.execute("UPDATE stock_adjustments SET product_id = ? WHERE product_id = ?", (new_id, temp_id))

        # Synchronize sqlite_sequence
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sqlite_sequence'")
        if cursor.fetchone():
            cursor.execute("UPDATE sqlite_sequence SET seq = ? WHERE name = 'products'", (len(rows),))

        conn.commit()
        return True, len(rows), f"Successfully renumbered {len(rows)} products sequentially (IDs 1 to {len(rows)})."
    except Exception as e:
        conn.rollback()
        return False, 0, str(e)
    finally:
        conn.close()


# =========================
# CUSTOMER FUNCTIONS
# =========================

def get_or_create_customer(customer_name, phone="", address=""):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, phone, address
    FROM customers
    WHERE name = ?
    """, (
        customer_name,
    ))

    customer = cursor.fetchone()

    if customer:

        customer_id = customer[0]
        if phone or address:
            cursor.execute("""
            UPDATE customers
            SET phone = CASE WHEN ? != '' THEN ? ELSE phone END,
                address = CASE WHEN ? != '' THEN ? ELSE address END
            WHERE id = ?
            """, (phone, phone, address, address, customer_id))
            conn.commit()

    else:

        cursor.execute("""
        INSERT INTO customers(name, phone, address)
        VALUES(?, ?, ?)
        """, (
            customer_name,
            phone,
            address
        ))

        conn.commit()

        customer_id = cursor.lastrowid

    conn.close()

    return customer_id


def get_customer_names_with_phone():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        name,
        phone
    FROM customers
    ORDER BY name
    """)

    data = cursor.fetchall()

    conn.close()

    formatted = []

    for row in data:

        name = row[0]

        phone = (
            row[1]
            if row[1]
            else ""
        )

        formatted.append(
            f"{name} ({phone})"
        )

    return formatted


# =========================
# SAVE COMPLETE INVOICE
# =========================

def save_complete_invoice(
    customer_name,
    cart_items,
    grand_total,
    paid_amount,
    note=""
):

    customer_id = get_or_create_customer(
        customer_name
    )

    pending = (
        grand_total - paid_amount
    )

    conn = get_connection()

    cursor = conn.cursor()

    # GENERATE DAILY INVOICE NUMBER 
    invoice_number = generate_invoice_number() 
    # CREATE INVOICE 
    cursor.execute("""
    INSERT INTO invoices(
        invoice_number,
        customer_id,
        total,
        paid,
        pending,
        note,
        status,
        invoice_date
    )                    
    VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE', datetime('now', 'localtime'))
    """, (
        invoice_number,
        customer_id,
        grand_total,
        paid_amount,
        pending,
        note
    ))


    invoice_id = cursor.lastrowid

    # SAVE ITEMS
    for item in cart_items:

        cursor.execute("""
        INSERT INTO invoice_items(
            invoice_id,
            product_id,
            quantity,
            mrp,
            price,
            discount,
            total,
            discount_base,
            increase
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            invoice_id,
            item["product_id"],
            item["quantity"],
            item["mrp"],
            item["price"],
            item.get("discount", 0.0),
            item["total"],
            item.get("discount_base", "Price"),
            item.get("increase", 0.0)
        ))

        # UPDATE STOCK
        cursor.execute("""
        SELECT stock
        FROM products
        WHERE id = ?
        """, (
            item["product_id"],
        ))

        old_stock = cursor.fetchone()[0]

        new_stock = (
            old_stock - item["quantity"]
        )

        cursor.execute("""
        UPDATE products
        SET stock = ?
        WHERE id = ?
        """, (
            new_stock,
            item["product_id"]
        ))

    conn.commit()

    conn.close()

    # Trigger silent auto-backup after invoice is committed
    try:
        trigger_auto_backup(reason="invoice")
    except Exception:
        pass

    return invoice_number


def cancel_invoice(invoice_id, authorized_by="Owner PIN"):
    """
    Cancels an active invoice:
    1. Restores all sold quantities back into products.stock.
    2. Logs stock adjustments for transparency and audits.
    3. Sets invoices.status = 'CANCELLED' and invoices.pending = 0.0.
    4. Records security audit log.
    Returns (True, message) or raises Exception.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, invoice_number, COALESCE(status, 'ACTIVE'), total FROM invoices WHERE id = ?", (invoice_id,))
        row = cursor.fetchone()
        if not row:
            return False, f"Invoice #{invoice_id} not found."
        if row[2] == "CANCELLED":
            return False, f"Invoice #{row[1]} is already cancelled."

        inv_num = row[1]
        total_val = row[3]

        # 1. Restore stock
        cursor.execute("""
        SELECT ii.product_id, ii.quantity, p.name
        FROM invoice_items ii
        LEFT JOIN products p ON ii.product_id = p.id
        WHERE ii.invoice_id = ?
        """, (invoice_id,))
        items = cursor.fetchall()

        total_restored = 0
        for prod_id, qty, p_name in items:
            cursor.execute("UPDATE products SET stock = stock + ? WHERE id = ?", (qty, prod_id))
            cursor.execute("""
            INSERT INTO stock_adjustments (product_id, adjustment_type, quantity, reason, timestamp)
            VALUES (?, 'INVOICE_CANCELLED', ?, ?, datetime('now', 'localtime'))
            """, (prod_id, qty, f"Restored from cancelled invoice #{inv_num}"))
            total_restored += qty

        # 2. Update status and clear pending balance
        cursor.execute("""
        UPDATE invoices
        SET status = 'CANCELLED',
            pending = 0.0
        WHERE id = ?
        """, (invoice_id,))

        # 3. Audit log
        cursor.execute("""
        INSERT INTO security_audit_logs (action_type, description, authorized_by, timestamp)
        VALUES ('INVOICE_CANCELLED', ?, ?, datetime('now', 'localtime'))
        """, (f"Invoice #{inv_num} (₹ {total_val:,.2f}) cancelled. Restored {total_restored} items across {len(items)} products.", authorized_by))

        conn.commit()

        try:
            trigger_auto_backup(reason="invoice_cancel")
        except Exception:
            pass

        return True, f"Invoice #{inv_num} cancelled successfully. {total_restored} units returned to inventory."
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def get_invoice_with_items(invoice_id):
    """
    Retrieves full invoice details including its line items.
    Returns a dict with:
      id, invoice_number, customer_id, customer_name, total, paid, pending,
      note, invoice_date, status, and items: list of dicts matching cart_items structure.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        SELECT
            invoices.id,
            invoices.invoice_number,
            invoices.customer_id,
            customers.name,
            invoices.total,
            invoices.paid,
            invoices.pending,
            COALESCE(invoices.note, ''),
            invoices.invoice_date,
            COALESCE(invoices.status, 'ACTIVE')
        FROM invoices
        JOIN customers ON invoices.customer_id = customers.id
        WHERE invoices.id = ? OR invoices.invoice_number = ?
        """, (invoice_id, str(invoice_id)))
        inv_row = cursor.fetchone()
        if not inv_row:
            return None

        actual_id = inv_row[0]
        cursor.execute("""
        SELECT
            ii.product_id,
            p.name,
            ii.quantity,
            ii.mrp,
            ii.price,
            COALESCE(ii.unit, p.unit, 'Pcs'),
            COALESCE(ii.increase, 0.0),
            COALESCE(ii.discount, 0.0),
            COALESCE(ii.discount_base, 'Price'),
            ii.total
        FROM invoice_items ii
        LEFT JOIN products p ON ii.product_id = p.id
        WHERE ii.invoice_id = ?
        ORDER BY ii.id ASC
        """, (actual_id,))
        item_rows = cursor.fetchall()

        items = []
        for r in item_rows:
            items.append({
                "product_id": r[0],
                "name": r[1] or "Unknown Product",
                "quantity": r[2],
                "mrp": float(r[3] or 0),
                "price": float(r[4] or 0),
                "unit": str(r[5] or "Pcs"),
                "increase": float(r[6] or 0),
                "discount": float(r[7] or 0),
                "discount_base": str(r[8] or "Price"),
                "total": float(r[9] or 0)
            })

        return {
            "id": actual_id,
            "invoice_number": inv_row[1],
            "customer_id": inv_row[2],
            "customer_name": inv_row[3],
            "total": float(inv_row[4] or 0),
            "paid": float(inv_row[5] or 0),
            "pending": float(inv_row[6] or 0),
            "note": inv_row[7],
            "invoice_date": inv_row[8],
            "status": inv_row[9],
            "items": items
        }
    finally:
        conn.close()


def update_saved_invoice(
    invoice_id,
    customer_name,
    cart_items,
    grand_total,
    paid_amount,
    note=""
):
    """
    Atomically updates an existing saved invoice:
    1. Returns all previously sold items back to product stock.
    2. Deducts the newly specified items from product stock.
    3. Replaces invoice_items rows.
    4. Updates customer, totals, paid, pending, note in invoices table.
    5. Records an audit log and triggers auto-backup.
    Returns invoice_number or raises Exception.
    """
    customer_id = get_or_create_customer(customer_name)
    pending = grand_total - paid_amount

    conn = get_connection()
    cursor = conn.cursor()
    try:
        # 1. Fetch invoice info & check status
        cursor.execute("SELECT id, invoice_number, COALESCE(status, 'ACTIVE') FROM invoices WHERE id = ?", (invoice_id,))
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Invoice #{invoice_id} not found.")
        if row[2] == "CANCELLED":
            raise ValueError(f"Invoice #{row[1]} is cancelled and cannot be modified.")

        inv_num = row[1]

        # 2. Get old items to restore stock
        cursor.execute("SELECT product_id, quantity FROM invoice_items WHERE invoice_id = ?", (invoice_id,))
        old_items = cursor.fetchall()
        for prod_id, old_qty in old_items:
            cursor.execute("UPDATE products SET stock = stock + ? WHERE id = ?", (old_qty, prod_id))

        # 3. Check and deduct stock for new items
        for item in cart_items:
            prod_id = item["product_id"]
            new_qty = item["quantity"]
            cursor.execute("SELECT stock, name FROM products WHERE id = ?", (prod_id,))
            prod_info = cursor.fetchone()
            current_stock = prod_info[0] if prod_info else 0
            if current_stock < new_qty:
                p_name = item.get("name", "Product")
                raise ValueError(f"Insufficient stock for '{p_name}': Available {current_stock}, requested {new_qty}")
            cursor.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (new_qty, prod_id))

        # 4. Replace invoice_items
        cursor.execute("DELETE FROM invoice_items WHERE invoice_id = ?", (invoice_id,))
        for item in cart_items:
            cursor.execute("""
            INSERT INTO invoice_items(
                invoice_id,
                product_id,
                quantity,
                mrp,
                price,
                discount,
                total,
                discount_base,
                increase,
                unit
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                invoice_id,
                item["product_id"],
                item["quantity"],
                item["mrp"],
                item["price"],
                item.get("discount", 0.0),
                item["total"],
                item.get("discount_base", "Price"),
                item.get("increase", 0.0),
                item.get("unit", "Pcs")
            ))

        # 5. Update invoice
        cursor.execute("""
        UPDATE invoices
        SET customer_id = ?,
            total = ?,
            paid = ?,
            pending = ?,
            note = ?
        WHERE id = ?
        """, (
            customer_id,
            grand_total,
            paid_amount,
            pending,
            note,
            invoice_id
        ))

        # 6. Audit log
        cursor.execute("""
        INSERT INTO security_audit_logs (action_type, description, authorized_by, timestamp)
        VALUES ('INVOICE_MODIFIED', ?, 'Owner PIN', datetime('now', 'localtime'))
        """, (f"Invoice #{inv_num} updated with {len(cart_items)} items. Total: ₹ {grand_total:,.2f}",))

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

    try:
        trigger_auto_backup(reason="invoice_edit")
    except Exception:
        pass

    return inv_num


def get_last_active_invoice():
    """Returns the most recent active invoice details, or None."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        SELECT
            invoices.id,
            invoices.invoice_number,
            invoices.total,
            customers.name
        FROM invoices
        JOIN customers ON invoices.customer_id = customers.id
        WHERE COALESCE(invoices.status, 'ACTIVE') != 'CANCELLED'
        ORDER BY invoices.id DESC
        LIMIT 1
        """)
        row = cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "invoice_number": row[1],
                "total": float(row[2] or 0),
                "customer_name": row[3]
            }
        return None
    finally:
        conn.close()



# =========================
# LEDGER
# =========================

def get_ledger_data():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        invoices.id,
        customers.name,
        invoices.total,
        invoices.paid,
        invoices.pending,
        invoices.invoice_date

    FROM invoices

    JOIN customers
    ON invoices.customer_id = customers.id

    WHERE COALESCE(invoices.status, 'ACTIVE') != 'CANCELLED'

    ORDER BY invoices.id DESC
    """)

    data = cursor.fetchall()

    conn.close()

    return data


# =========================
# CUSTOMER HISTORY
# =========================

def get_customer_history(customer_name):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        invoices.id,
        invoices.invoice_date,
        products.name,
        invoice_items.quantity,
        invoices.total,
        invoices.paid,
        invoices.pending

    FROM invoices

    JOIN customers
    ON invoices.customer_id = customers.id

    JOIN invoice_items
    ON invoices.id = invoice_items.invoice_id

    JOIN products
    ON invoice_items.product_id = products.id

    WHERE customers.name = ?
      AND COALESCE(invoices.status, 'ACTIVE') != 'CANCELLED'

    ORDER BY invoices.id DESC
    """, (
        customer_name,
    ))

    data = cursor.fetchall()

    conn.close()

    return data


# =========================
# DASHBOARD
# =========================

def get_total_products():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
    SELECT COUNT(*)
    FROM products
    """)

    total = cursor.fetchone()[0]

    conn.close()

    return total


def get_total_customers():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
    SELECT COUNT(DISTINCT name)
    FROM customers
    """)

    total = cursor.fetchone()[0]

    conn.close()

    return total


def get_total_pending_amount():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
    SELECT SUM(pending)
    FROM invoices
    """)

    result = cursor.fetchone()[0]

    conn.close()

    return result if result else 0


def get_today_sales():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
    SELECT SUM(total)
    FROM invoices
    WHERE date(invoice_date) = date('now', 'localtime')
    """)

    result = cursor.fetchone()[0]

    conn.close()

    return result if result else 0



def get_low_stock_items():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        name,
        stock
    FROM products
    WHERE stock <= 5
    ORDER BY stock ASC
    """)

    data = cursor.fetchall()

    conn.close()

    return data

def get_customer_ledger():

    return get_ledger_data()

def get_total_pending(customer_name):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
    SELECT SUM(invoices.pending)

    FROM invoices

    JOIN customers
    ON invoices.customer_id = customers.id

    WHERE customers.name = ?
      AND COALESCE(invoices.status, 'ACTIVE') != 'CANCELLED'
    """, (
        customer_name,
    ))

    result = cursor.fetchone()[0]

    conn.close()

    return result if result else 0

def get_product_complete_details(product_query, category=None):
    """
    Look up complete product details robustly by:
    1. Category + Name exact match
    2. 'Category - Name' combined string match
    3. Name exact match (case-insensitive)
    4. Name or formatted string fallback matching
    Always returns: (id, name, mrp, selling_price, stock, unit, discount_base, category)
    where unit is guaranteed non-empty (defaulting to 'Pcs' if empty/null).
    """
    if not product_query:
        return None

    product_query = str(product_query).strip()
    conn = get_connection()
    cursor = conn.cursor()

    query_str = """
    SELECT
        id,
        name,
        COALESCE(mrp, 0),
        COALESCE(selling_price, 0),
        COALESCE(stock, 0),
        COALESCE(NULLIF(TRIM(unit), ''), 'Pcs') AS unit,
        COALESCE(discount_base, 'Price'),
        COALESCE(category, '')
    FROM products
    """

    # 1. Direct match with category if provided
    if category:
        cursor.execute(query_str + " WHERE category = ? AND name = ? LIMIT 1", (category.strip(), product_query))
        product = cursor.fetchone()
        if product:
            conn.close()
            return product

    # 2. Check if combined 'Category - Name' matched
    cursor.execute(query_str + " WHERE (category || ' - ' || name) = ? LIMIT 1", (product_query,))
    product = cursor.fetchone()
    if product:
        conn.close()
        return product

    # 3. If query contains ' - ', try splitting into category and name
    if " - " in product_query:
        parts = product_query.split(" - ")
        # Try last part as name
        possible_name = parts[-1].strip()
        possible_cat = " - ".join(parts[:-1]).strip()
        cursor.execute(query_str + " WHERE category = ? AND name = ? LIMIT 1", (possible_cat, possible_name))
        product = cursor.fetchone()
        if product:
            conn.close()
            return product

        # Try first part as category, rest as name
        possible_cat = parts[0].strip()
        possible_name = " - ".join(parts[1:]).strip()
        cursor.execute(query_str + " WHERE category = ? AND name = ? LIMIT 1", (possible_cat, possible_name))
        product = cursor.fetchone()
        if product:
            conn.close()
            return product

        # Try just possible_name by itself
        cursor.execute(query_str + " WHERE name = ? COLLATE NOCASE LIMIT 1", (possible_name,))
        product = cursor.fetchone()
        if product:
            conn.close()
            return product

    # 4. Exact name match (case-insensitive)
    cursor.execute(query_str + " WHERE name = ? COLLATE NOCASE LIMIT 1", (product_query,))
    product = cursor.fetchone()
    if product:
        conn.close()
        return product

    # 5. Fallback case-insensitive LIKE search
    cursor.execute(query_str + " WHERE name LIKE ? OR (category || ' - ' || name) LIKE ? LIMIT 1",
                   (f"%{product_query}%", f"%{product_query}%"))
    product = cursor.fetchone()

    conn.close()
    return product



# =====================================
# GET CUSTOMER NAMES
# =====================================

def get_customer_names():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
        SELECT name
        FROM customers
        ORDER BY name
    """)

    rows = cursor.fetchall()

    conn.close()

    return [row[0] for row in rows]


# =====================================
# GENERATE DAILY INVOICE NUMBER
# =====================================

from datetime import datetime


def generate_invoice_number():

    conn = get_connection()

    cursor = conn.cursor()

    today = datetime.now().strftime("%d%m%y")

    pattern = f"{today}_%"

    cursor.execute(
        """
        SELECT invoice_number
        FROM invoices
        WHERE invoice_number LIKE ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (pattern,)
    )

    last_invoice = cursor.fetchone()

    if last_invoice and last_invoice[0]:

        last_number = int(
            last_invoice[0].split("_")[1]
        )

        next_number = last_number + 1

    else:

        next_number = 1

    invoice_number = (
        f"{today}_{next_number:02d}"
    )

    conn.close()

    return invoice_number


# =====================================
# LEDGER OPTIMIZATION FUNCTIONS
# =====================================

def get_customers_with_pending():
    """Get list of unique customers with their total pending amounts"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        COALESCE(NULLIF(TRIM(customers.name), ''), 'Unnamed Customer') as cust_name,
        SUM(invoices.pending) as total_pending,
        COUNT(invoices.id) as invoice_count
    FROM customers
    JOIN invoices ON customers.id = invoices.customer_id
    WHERE invoices.pending > 0
      AND COALESCE(invoices.status, 'ACTIVE') != 'CANCELLED'
    GROUP BY customers.id, cust_name
    ORDER BY total_pending DESC
    """)

    data = cursor.fetchall()
    conn.close()
    return data


def get_customer_invoices(customer_name):
    """Get all invoices for a specific customer"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        invoices.id,
        invoices.invoice_number,
        COALESCE(strftime('%d-%m-%Y', invoices.invoice_date), 'N/A'),
        invoices.total,
        invoices.paid,
        invoices.pending,
        COALESCE(invoices.note, ''),
        COALESCE(invoices.status, 'ACTIVE')
    FROM invoices
    JOIN customers ON invoices.customer_id = customers.id
    WHERE COALESCE(NULLIF(TRIM(customers.name), ''), 'Unnamed Customer') = ? OR customers.name = ?
    ORDER BY invoices.id DESC
    """, (customer_name, customer_name))

    data = cursor.fetchall()
    conn.close()
    return data



def update_invoice_payment(invoice_id, new_paid_amount):
    """Update payment amount for an invoice"""
    conn = get_connection()
    cursor = conn.cursor()

    # Get current total
    cursor.execute("""
    SELECT total FROM invoices WHERE id = ?
    """, (invoice_id,))

    total = cursor.fetchone()[0]

    # Calculate pending
    new_pending = max(0, total - new_paid_amount)

    # Update invoice
    cursor.execute("""
    UPDATE invoices
    SET paid = ?, pending = ?
    WHERE id = ?
    """, (new_paid_amount, new_pending, invoice_id))

    conn.commit()
    conn.close()


def get_invoice_details_by_id(invoice_id):
    """Get complete invoice details by ID"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        invoices.id,
        invoices.invoice_number,
        customers.name,
        COALESCE(strftime('%d-%m-%Y', invoices.invoice_date), 'N/A'),
        invoices.total,
        invoices.paid,
        invoices.pending,
        COALESCE(invoices.note, '')
    FROM invoices
    JOIN customers ON invoices.customer_id = customers.id
    WHERE invoices.id = ?
    """, (invoice_id,))

    data = cursor.fetchone()
    conn.close()
    return data


def get_invoice_by_number(invoice_number):
    """Get invoice row by invoice_number, display string, or ID (with or without 'INV-' prefix or customer suffix)"""
    clean_num = str(invoice_number).strip()
    if clean_num.upper().startswith("INV-"):
        clean_num = clean_num[4:].strip()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT
        invoices.id,
        invoices.invoice_number,
        customers.name,
        COALESCE(strftime('%d-%m-%Y', invoices.invoice_date), 'N/A'),
        invoices.total,
        invoices.paid,
        invoices.pending,
        COALESCE(invoices.note, '')
    FROM invoices
    JOIN customers ON invoices.customer_id = customers.id
    WHERE invoices.invoice_number = ? 
       OR ? LIKE (invoices.invoice_number || '%')
       OR invoices.id = ?
    ORDER BY invoices.id DESC
    LIMIT 1
    """, (clean_num, clean_num, int(clean_num) if clean_num.isdigit() else -1))

    data = cursor.fetchone()
    conn.close()
    return data



def get_invoice_items(invoice_id):
    """Get all items in an invoice"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        invoice_items.quantity,
        products.name,
        COALESCE(invoice_items.mrp, 0.0),
        invoice_items.price,
        products.unit,
        invoice_items.discount,
        COALESCE(invoice_items.discount_base, 'Price'),
        invoice_items.total,
        COALESCE(invoice_items.increase, 0.0)
    FROM invoice_items
    JOIN products ON invoice_items.product_id = products.id
    WHERE invoice_items.invoice_id = ?
    ORDER BY invoice_items.id
    """, (invoice_id,))

    data = cursor.fetchall()
    conn.close()
    return data


def update_invoice_note(invoice_id, note):
    """Update note for an invoice"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE invoices
    SET note = ?
    WHERE id = ?
    """, (note, invoice_id))

    conn.commit()
    conn.close()


# =====================================
# SAFE DATABASE BACKUP & RESTORE
# =====================================

def backup_database_to_file(backup_file_path):
    """
    Safely backup the active SQLite database to a target file using SQLite's native backup API.
    This guarantees that all committed transactions in WAL mode are cleanly backed up.
    """
    backup_dir = os.path.dirname(backup_file_path)
    if backup_dir:
        os.makedirs(backup_dir, exist_ok=True)

    source_conn = get_connection()
    try:
        try:
            source_conn.execute("PRAGMA wal_checkpoint(FULL)")
        except Exception:
            pass

        dest_conn = sqlite3.connect(backup_file_path)
        try:
            source_conn.backup(dest_conn)
        finally:
            dest_conn.close()
    finally:
        source_conn.close()


def restore_database_from_file(backup_file_path):
    """
    Safely restore the active SQLite database from a backup file using SQLite's native backup API.
    """
    if not os.path.exists(backup_file_path):
        raise FileNotFoundError(f"Backup file not found: {backup_file_path}")

    source_conn = sqlite3.connect(backup_file_path)
    dest_conn = get_connection()
    try:
        try:
            dest_conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except Exception:
            pass

        source_conn.backup(dest_conn)
        dest_conn.commit()
    finally:
        source_conn.close()
        dest_conn.close()


def clean_old_auto_backups(retention_days=30, max_backups=60):
    """
    Automatically purges auto-backups older than retention_days or beyond max_backups limit
    to prevent disk space exhaustion over years of usage on offline laptops.
    """
    try:
        if not os.path.exists(AUTO_BACKUPS_DIR):
            return

        cutoff_time = time.time() - (retention_days * 86400)
        backup_files = []

        for fname in os.listdir(AUTO_BACKUPS_DIR):
            if fname.startswith("auto_backup_") and fname.endswith(".db"):
                fpath = os.path.join(AUTO_BACKUPS_DIR, fname)
                try:
                    mtime = os.path.getmtime(fpath)
                    backup_files.append((fpath, mtime))
                except Exception:
                    pass

        # Sort newest first
        backup_files.sort(key=lambda x: x[1], reverse=True)

        for i, (fpath, mtime) in enumerate(backup_files):
            # Delete if older than retention_days AND beyond minimum 10 retained backups, or if exceeds max_backups
            if (mtime < cutoff_time and i >= 10) or i >= max_backups:
                try:
                    os.remove(fpath)
                except Exception:
                    pass
    except Exception as e:
        print(f"Error during auto-backup cleanup: {e}")


def trigger_auto_backup(reason="daily"):
    """
    Performs an automatic silent backup of the database to the rolling auto-backups directory.
    Reasons: 'daily' (on app start), 'invoice' (after invoice save), or 'manual'.
    """
    try:
        os.makedirs(AUTO_BACKUPS_DIR, exist_ok=True)
        now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"auto_backup_{now_str}_{reason}.db"
        backup_path = os.path.join(AUTO_BACKUPS_DIR, backup_filename)

        backup_database_to_file(backup_path)
        clean_old_auto_backups()
        return backup_path
    except Exception as e:
        print(f"Auto-backup ({reason}) notice: {e}")
        return None


def safe_flush_pen_drive():
    """
    Safely flushes and commits all data directly to the Pen Drive.
    1. Executes PRAGMA wal_checkpoint(TRUNCATE) to force all journal pages into the primary .db file.
    2. Runs PRAGMA integrity_check to verify zero database corruption.
    3. Triggers an automatic snapshot into the Pen Drive's backups/auto/ folder.
    4. Flushes OS file write buffers so USB can be disconnected safely.
    Returns (True, message) or (False, error).
    """
    try:
        if not os.path.exists(DATABASE_PATH):
            return False, "Database not found."

        conn = get_connection()
        try:
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check")
            row = cursor.fetchone()
            integrity = row[0] if row else "ok"
            if integrity != "ok":
                return False, f"Integrity check warning: {integrity}"
        finally:
            conn.close()

        # Silent auto backup to USB drive backups/auto
        try:
            trigger_auto_backup(reason="pen_drive_flush")
        except Exception:
            pass

        # Windows OS buffer flush
        try:
            if hasattr(os, "sync"):
                os.sync()
        except Exception:
            pass

        return True, "All database records, invoices & stock safely synchronized to Pen Drive."
    except Exception as e:
        return False, str(e)


def close_database_on_exit():
    """
    Executes a WAL truncate checkpoint and database integrity check on clean application exit.
    Ensures that WAL file changes are safely flushed into the main database file on the Pen Drive.
    """
    ok, msg = safe_flush_pen_drive()
    return "ok" if ok else msg


def seed_paints_and_hardware_demo_data():
    """
    Seeds a realistic, comprehensive Paints & Hardware demo dataset for Delhi wholesale & retail demo.
    Includes top paint brands (Asian Paints, Berger, Nerolac), enamels, primers, putties, thinners,
    tools (brushes, rollers, sandpaper), hardware fittings (hinges, locks, aldrop), fasteners (screws, nails),
    and plumbing materials. Also seeds sample Delhi contractor/retail customers and transactions.
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # 1. Update shop profile to Delhi-based Paints & Hardware store if not already set
        cursor.execute("SELECT value FROM app_settings WHERE key = 'shop_name'")
        curr_name = cursor.fetchone()
        if not curr_name or curr_name[0] in ("Electrical Wholesale & Retail", "My Business", ""):
            cursor.execute("INSERT OR REPLACE INTO app_settings(key, value) VALUES('shop_name', 'Delhi Paints & Hardware Store')")
            cursor.execute("INSERT OR REPLACE INTO app_settings(key, value) VALUES('shop_phone', '+91-9811234567 / 011-23864500')")
            cursor.execute("INSERT OR REPLACE INTO app_settings(key, value) VALUES('shop_address', 'Shop No. 14, Hauz Qazi / Chawri Bazar, Delhi - 110006')")

        # 2. Categories
        categories = [
            "PAINTS - EMULSION & EXTERIOR",
            "PAINTS - ENAMEL & PRIMER",
            "PAINTS - DISTEMPER & WALL PUTTY",
            "PAINTING TOOLS & ACCESSORIES",
            "HARDWARE - DOOR & WINDOW FITTINGS",
            "HARDWARE - FASTENERS & NAILS",
            "HARDWARE - PLUMBING & SANITARY",
            "HARDWARE - HAND TOOLS"
        ]
        for cat in categories:
            cursor.execute("INSERT OR IGNORE INTO categories(name) VALUES (?)", (cat,))

        # 3. Curated Paints & Hardware Catalog: (category, name, mrp, purchase_price, selling_price, unit, stock)
        demo_products = [
            # Paints - Emulsions
            ("PAINTS - EMULSION & EXTERIOR", "Asian Paints Apex Ultima White 20L", 7800.0, 6200.0, 7100.0, "Bucket", 25),
            ("PAINTS - EMULSION & EXTERIOR", "Asian Paints Apex Ultima White 4L", 1750.0, 1380.0, 1580.0, "Can", 40),
            ("PAINTS - EMULSION & EXTERIOR", "Asian Paints Royale Luxury Emulsion 10L", 5200.0, 4100.0, 4750.0, "Bucket", 20),
            ("PAINTS - EMULSION & EXTERIOR", "Asian Paints Royale Luxury Emulsion 1L", 590.0, 460.0, 530.0, "Can", 60),
            ("PAINTS - EMULSION & EXTERIOR", "Asian Paints Tractor Emulsion White 20L", 3100.0, 2400.0, 2800.0, "Bucket", 35),
            ("PAINTS - EMULSION & EXTERIOR", "Asian Paints Tractor Emulsion White 4L", 720.0, 550.0, 650.0, "Can", 50),
            ("PAINTS - EMULSION & EXTERIOR", "Berger WeatherCoat All Guard 20L", 6900.0, 5400.0, 6200.0, "Bucket", 15),
            ("PAINTS - EMULSION & EXTERIOR", "Nerolac Beauty Smooth Finish 20L", 2950.0, 2280.0, 2650.0, "Bucket", 20),

            # Paints - Enamels & Primers
            ("PAINTS - ENAMEL & PRIMER", "Apcolite Premium Gloss Enamel 4L", 1350.0, 1050.0, 1220.0, "Can", 30),
            ("PAINTS - ENAMEL & PRIMER", "Apcolite Premium Gloss Enamel White 1L", 360.0, 280.0, 325.0, "Can", 75),
            ("PAINTS - ENAMEL & PRIMER", "Asian Paints Exterior Wall Primer 10L", 1650.0, 1280.0, 1480.0, "Bucket", 30),
            ("PAINTS - ENAMEL & PRIMER", "Asian Paints Interior Wall Primer 10L", 1400.0, 1080.0, 1250.0, "Bucket", 35),
            ("PAINTS - ENAMEL & PRIMER", "Red Oxide Metal Primer 4L", 780.0, 590.0, 700.0, "Can", 40),
            ("PAINTS - ENAMEL & PRIMER", "NC Premium Thinner 1 Ltr", 180.0, 125.0, 150.0, "Bottle", 120),
            ("PAINTS - ENAMEL & PRIMER", "Commercial Thinner 5 Ltr", 650.0, 460.0, 550.0, "Can", 40),

            # Distemper & Wall Putty
            ("PAINTS - DISTEMPER & WALL PUTTY", "Asian Paints TruCare Acrylic Wall Putty 20kg", 850.0, 660.0, 760.0, "Bag", 60),
            ("PAINTS - DISTEMPER & WALL PUTTY", "Asian Paints TruCare Acrylic Wall Putty 5kg", 240.0, 185.0, 215.0, "Bag", 90),
            ("PAINTS - DISTEMPER & WALL PUTTY", "JK WallMaxx White Wall Putty 40kg", 980.0, 780.0, 890.0, "Bag", 80),
            ("PAINTS - DISTEMPER & WALL PUTTY", "Asian Paints Tractor Acrylic Distemper 20kg", 1150.0, 890.0, 1020.0, "Bucket", 35),

            # Painting Tools & Accessories
            ("PAINTING TOOLS & ACCESSORIES", "Paint Brush 2 inch (Bristle)", 60.0, 32.0, 45.0, "Pcs", 150),
            ("PAINTING TOOLS & ACCESSORIES", "Paint Brush 3 inch (Bristle)", 90.0, 50.0, 70.0, "Pcs", 120),
            ("PAINTING TOOLS & ACCESSORIES", "Paint Brush 4 inch (Bristle)", 130.0, 75.0, 105.0, "Pcs", 90),
            ("PAINTING TOOLS & ACCESSORIES", "Paint Roller 9 inch with Tray Set", 280.0, 160.0, 220.0, "Set", 65),
            ("PAINTING TOOLS & ACCESSORIES", "Waterproof Sandpaper #80 (Coarse)", 25.0, 12.0, 18.0, "Sheet", 300),
            ("PAINTING TOOLS & ACCESSORIES", "Waterproof Sandpaper #120 (Medium)", 25.0, 12.0, 18.0, "Sheet", 400),
            ("PAINTING TOOLS & ACCESSORIES", "Waterproof Sandpaper #220 (Fine)", 25.0, 12.0, 18.0, "Sheet", 350),
            ("PAINTING TOOLS & ACCESSORIES", "Masking Tape 1 inch (20m)", 50.0, 26.0, 38.0, "Roll", 200),
            ("PAINTING TOOLS & ACCESSORIES", "Masking Tape 2 inch (20m)", 95.0, 52.0, 75.0, "Roll", 140),

            # Hardware - Door & Window Fittings
            ("HARDWARE - DOOR & WINDOW FITTINGS", "SS Butt Hinges 4 inch (Heavy 3mm)", 160.0, 95.0, 130.0, "Pair", 100),
            ("HARDWARE - DOOR & WINDOW FITTINGS", "Brass Mortise Handle Lock Set (6 Lever)", 1850.0, 1250.0, 1550.0, "Set", 25),
            ("HARDWARE - DOOR & WINDOW FITTINGS", "SS Aldrop 10 inch with Rod & Bolts", 480.0, 310.0, 390.0, "Set", 45),
            ("HARDWARE - DOOR & WINDOW FITTINGS", "SS Tower Bolt 6 inch", 110.0, 65.0, 85.0, "Pcs", 110),
            ("HARDWARE - DOOR & WINDOW FITTINGS", "SS Tower Bolt 8 inch", 150.0, 90.0, 120.0, "Pcs", 80),
            ("HARDWARE - DOOR & WINDOW FITTINGS", "Magnetic Door Catcher (Heavy Duty)", 95.0, 50.0, 70.0, "Pcs", 120),

            # Hardware - Fasteners & Nails
            ("HARDWARE - FASTENERS & NAILS", "Drywall Gypsum Screws 1.5 inch (Box 500 Pcs)", 320.0, 190.0, 250.0, "Box", 80),
            ("HARDWARE - FASTENERS & NAILS", "Drywall Gypsum Screws 2 inch (Box 500 Pcs)", 390.0, 230.0, 310.0, "Box", 60),
            ("HARDWARE - FASTENERS & NAILS", "SS Wood Screws 1 inch (Box 100 Pcs)", 140.0, 80.0, 110.0, "Box", 90),
            ("HARDWARE - FASTENERS & NAILS", "Wire Nails 2 inch (1 kg Pack)", 110.0, 70.0, 90.0, "Kg", 150),
            ("HARDWARE - FASTENERS & NAILS", "Wire Nails 3 inch (1 kg Pack)", 110.0, 70.0, 90.0, "Kg", 120),
            ("HARDWARE - FASTENERS & NAILS", "PVC Rawl Plugs 35mm (Pack of 100)", 80.0, 38.0, 55.0, "Pkt", 100),

            # Hardware - Plumbing & Sanitary
            ("HARDWARE - PLUMBING & SANITARY", "CPVC Brass Elbow 1/2 inch", 95.0, 58.0, 75.0, "Pcs", 130),
            ("HARDWARE - PLUMBING & SANITARY", "CPVC Ball Valve 1 inch (Heavy)", 280.0, 175.0, 225.0, "Pcs", 50),
            ("HARDWARE - PLUMBING & SANITARY", "PVC Conduit Pipe 25mm (3 Metre)", 120.0, 72.0, 95.0, "Length", 150),
            ("HARDWARE - PLUMBING & SANITARY", "CPVC Solvent Cement 250ml Tin", 240.0, 155.0, 195.0, "Tin", 60),
            ("HARDWARE - PLUMBING & SANITARY", "Brass Bib Tap 1/2 inch Long Body", 550.0, 340.0, 440.0, "Pcs", 35),
            ("HARDWARE - PLUMBING & SANITARY", "PTFE Teflon Tape (Pack of 10)", 150.0, 80.0, 115.0, "Pkt", 90),

            # Hardware - Hand Tools
            ("HARDWARE - HAND TOOLS", "Claw Hammer 500g with Fiberglass Handle", 380.0, 220.0, 295.0, "Pcs", 30),
            ("HARDWARE - HAND TOOLS", "Steel Measuring Tape 5 Metre", 180.0, 95.0, 135.0, "Pcs", 50),
            ("HARDWARE - HAND TOOLS", "Screwdriver 8-in-1 Interchangeable Set", 260.0, 140.0, 195.0, "Set", 40),
            ("HARDWARE - HAND TOOLS", "Hacksaw Frame with Bi-Metal Blade", 290.0, 165.0, 225.0, "Pcs", 35),
            ("HARDWARE - HAND TOOLS", "Combination Pliers 8 inch (Insulated)", 320.0, 180.0, 245.0, "Pcs", 40)
        ]

        for cat, name, mrp, pprice, sprice, unit, stock in demo_products:
            cursor.execute("SELECT id FROM products WHERE name = ?", (name,))
            existing = cursor.fetchone()
            if existing:
                cursor.execute("""
                UPDATE products
                SET category=?, mrp=?, purchase_price=?, selling_price=?, unit=?, stock=?
                WHERE id=?
                """, (cat, mrp, pprice, sprice, unit, stock, existing[0]))
            else:
                cursor.execute("""
                INSERT INTO products(category, name, mrp, purchase_price, selling_price, unit, stock, discount_base)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'Price')
                """, (cat, name, mrp, pprice, sprice, unit, stock))

        # 4. Sample Customers (Delhi-based)
        demo_customers = [
            ("Sharma Contractors & Builders (Chawri Bazar)", "9810123456", "Plot 22, Chawri Bazar, Delhi - 110006"),
            ("Rajesh Painter & Polish Works (Laxmi Nagar)", "9871987654", "Gali No. 4, Laxmi Nagar, Delhi - 110092"),
            ("Verma Hardware & Sanitary Store (Rohini)", "9818554433", "Sector 7, Rohini, Delhi - 110085"),
            ("Sunil Kumar (Civil Lines)", "9911223344", "12 Rajpur Road, Civil Lines, Delhi - 110054"),
            ("Walk-in Cash Customer", "", "Counter Sale, Delhi")
        ]
        cust_id_map = {}
        for cname, cphone, caddr in demo_customers:
            cursor.execute("SELECT id FROM customers WHERE name = ?", (cname,))
            c_row = cursor.fetchone()
            if c_row:
                cursor.execute("UPDATE customers SET phone = ?, address = ? WHERE id = ?", (cphone, caddr, c_row[0]))
                cust_id_map[cname] = c_row[0]
            else:
                cursor.execute("INSERT INTO customers(name, phone, address) VALUES (?, ?, ?)", (cname, cphone, caddr))
                cust_id_map[cname] = cursor.lastrowid

        # 5. Seed 3 Trial Invoices if no invoices exist
        cursor.execute("SELECT COUNT(*) FROM invoices")
        if cursor.fetchone()[0] == 0:
            # Invoice 1: Sharma Contractors (Wholesale credit invoice)
            c1_id = cust_id_map["Sharma Contractors & Builders (Chawri Bazar)"]
            cursor.execute("""
            INSERT INTO invoices(invoice_number, customer_id, total, paid, pending, invoice_date, note, status)
            VALUES('1001', ?, 18286.80, 14000.00, 4286.80, datetime('now', '-2 hours'), 'Site delivery at Daryaganj project', 'ACTIVE')
            """, (c1_id,))
            inv1_id = cursor.lastrowid

            # Items for Inv 1
            cursor.execute("SELECT id FROM products WHERE name = 'Asian Paints Apex Ultima White 20L'")
            p1_id = cursor.fetchone()[0]
            cursor.execute("INSERT INTO invoice_items(invoice_id, product_id, quantity, mrp, price, discount, total, unit) VALUES (?, ?, 2, 7800.0, 7100.0, 0, 14200.0, 'Bucket')", (inv1_id, p1_id))
            cursor.execute("SELECT id FROM products WHERE name = 'Asian Paints TruCare Acrylic Wall Putty 20kg'")
            p2_id = cursor.fetchone()[0]
            cursor.execute("INSERT INTO invoice_items(invoice_id, product_id, quantity, mrp, price, discount, total, unit) VALUES (?, ?, 5, 850.0, 760.0, 0, 3800.0, 'Bag')", (inv1_id, p2_id))
            cursor.execute("SELECT id FROM products WHERE name = 'Paint Roller 9 inch with Tray Set'")
            p3_id = cursor.fetchone()[0]
            cursor.execute("INSERT INTO invoice_items(invoice_id, product_id, quantity, mrp, price, discount, total, unit) VALUES (?, ?, 3, 280.0, 220.0, 2.0, 646.80, 'Set')", (inv1_id, p3_id))

            # Invoice 2: Rajesh Painter (Fully Paid Enamel & Thinner)
            c2_id = cust_id_map["Rajesh Painter & Polish Works (Laxmi Nagar)"]
            cursor.execute("""
            INSERT INTO invoices(invoice_number, customer_id, total, paid, pending, invoice_date, note, status)
            VALUES('1002', ?, 3320.00, 3320.00, 0.0, datetime('now', '-1 hours'), 'Full Cash Payment', 'ACTIVE')
            """, (c2_id,))
            inv2_id = cursor.lastrowid

            cursor.execute("SELECT id FROM products WHERE name = 'Apcolite Premium Gloss Enamel 4L'")
            p4_id = cursor.fetchone()[0]
            cursor.execute("INSERT INTO invoice_items(invoice_id, product_id, quantity, mrp, price, discount, total, unit) VALUES (?, ?, 2, 1350.0, 1220.0, 0, 2440.0, 'Can')", (inv2_id, p4_id))
            cursor.execute("SELECT id FROM products WHERE name = 'NC Premium Thinner 1 Ltr'")
            p5_id = cursor.fetchone()[0]
            cursor.execute("INSERT INTO invoice_items(invoice_id, product_id, quantity, mrp, price, discount, total, unit) VALUES (?, ?, 4, 180.0, 150.0, 0, 600.0, 'Bottle')", (inv2_id, p5_id))
            cursor.execute("SELECT id FROM products WHERE name = 'Paint Brush 3 inch (Bristle)'")
            p6_id = cursor.fetchone()[0]
            cursor.execute("INSERT INTO invoice_items(invoice_id, product_id, quantity, mrp, price, discount, total, unit) VALUES (?, ?, 4, 90.0, 70.0, 0, 280.0, 'Pcs')", (inv2_id, p6_id))

            # Invoice 3: Walk-in Cash Customer
            c3_id = cust_id_map["Walk-in Cash Customer"]
            cursor.execute("""
            INSERT INTO invoices(invoice_number, customer_id, total, paid, pending, invoice_date, note, status)
            VALUES('1003', ?, 1915.00, 1915.00, 0.0, datetime('now', '-20 minutes'), 'UPI Payment', 'ACTIVE')
            """, (c3_id,))
            inv3_id = cursor.lastrowid

            cursor.execute("SELECT id FROM products WHERE name = 'Brass Mortise Handle Lock Set (6 Lever)'")
            p7_id = cursor.fetchone()[0]
            cursor.execute("INSERT INTO invoice_items(invoice_id, product_id, quantity, mrp, price, discount, total, unit) VALUES (?, ?, 1, 1850.0, 1550.0, 0, 1550.0, 'Set')", (inv3_id, p7_id))
            cursor.execute("SELECT id FROM products WHERE name = 'Drywall Gypsum Screws 1.5 inch (Box 500 Pcs)'")
            p8_id = cursor.fetchone()[0]
            cursor.execute("INSERT INTO invoice_items(invoice_id, product_id, quantity, mrp, price, discount, total, unit) VALUES (?, ?, 1, 320.0, 250.0, 0, 250.0, 'Box')", (inv3_id, p8_id))
            cursor.execute("SELECT id FROM products WHERE name = 'PTFE Teflon Tape (Pack of 10)'")
            p9_id = cursor.fetchone()[0]
            cursor.execute("INSERT INTO invoice_items(invoice_id, product_id, quantity, mrp, price, discount, total, unit) VALUES (?, ?, 1, 150.0, 115.0, 0, 115.0, 'Pkt')", (inv3_id, p9_id))

        # Mark demo_seed_skipped as '0' so demo data is acknowledged
        cursor.execute("INSERT OR REPLACE INTO app_settings(key, value) VALUES('demo_seed_skipped', '0')")

        conn.commit()
        return True, f"Successfully seeded {len(demo_products)} Paints & Hardware products and sample Delhi ledgers."
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()


# =====================================
# STOCK ADJUSTMENTS (RETURNS & DAMAGES)
# =====================================

def record_stock_adjustment(product_id, adjustment_type, quantity, reason=""):
    """
    Records a stock adjustment (Damage, Return, Expired, Correction) and updates product stock.
    Positive quantity increases stock (e.g. Customer Return).
    Negative quantity decreases stock (e.g. Damaged / Broken / Supplier Return).
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Get current stock
        cursor.execute("SELECT stock FROM products WHERE id = ?", (product_id,))
        row = cursor.fetchone()
        if not row:
            raise ValueError("Product not found")

        current_stock = row[0]
        new_stock = max(0, current_stock + quantity)

        # Update product stock
        cursor.execute("UPDATE products SET stock = ? WHERE id = ?", (new_stock, product_id))

        # Record adjustment entry
        cursor.execute("""
        INSERT INTO stock_adjustments (product_id, adjustment_type, quantity, reason)
        VALUES (?, ?, ?, ?)
        """, (product_id, adjustment_type, quantity, reason))

        conn.commit()
        return new_stock
    finally:
        conn.close()


def get_stock_adjustments(product_id=None, limit=100):
    """Retrieve stock adjustment audit history."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if product_id:
            cursor.execute("""
            SELECT
                sa.id,
                sa.timestamp,
                p.name,
                sa.adjustment_type,
                sa.quantity,
                sa.reason
            FROM stock_adjustments sa
            JOIN products p ON sa.product_id = p.id
            WHERE sa.product_id = ?
            ORDER BY sa.id DESC
            LIMIT ?
            """, (product_id, limit))
        else:
            cursor.execute("""
            SELECT
                sa.id,
                sa.timestamp,
                p.name,
                sa.adjustment_type,
                sa.quantity,
                sa.reason
            FROM stock_adjustments sa
            JOIN products p ON sa.product_id = p.id
            ORDER BY sa.id DESC
            LIMIT ?
            """, (limit,))
        return cursor.fetchall()
    finally:
        conn.close()


# =====================================
# CUSTOMER ACCOUNT STATEMENT DATA
# =====================================

def get_customer_statement_data(customer_name):
    """
    Fetches full chronological transaction statement for a customer.
    Returns:
      customer_info: dict(name, phone, address, total_invoiced, total_paid, net_dues)
      transactions: list of dicts(id, invoice_number, date, total, paid, pending, running_balance, note)
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, name, COALESCE(phone, ''), COALESCE(address, '') FROM customers WHERE name = ?", (customer_name,))
        cust_row = cursor.fetchone()
        if not cust_row:
            return None, []

        cust_id, name, phone, address = cust_row

        cursor.execute("""
        SELECT
            id,
            invoice_number,
            COALESCE(strftime('%d-%m-%Y', invoice_date), 'N/A'),
            total,
            paid,
            pending,
            COALESCE(note, '')
        FROM invoices
        WHERE customer_id = ?
        ORDER BY id ASC
        """, (cust_id,))

        raw_invoices = cursor.fetchall()
        transactions = []
        running_balance = 0.0
        total_invoiced = 0.0
        total_paid = 0.0

        for row in raw_invoices:
            inv_id, inv_no, date_str, total, paid, pending, note = row
            total = float(total or 0)
            paid = float(paid or 0)
            pending = float(pending or 0)

            total_invoiced += total
            total_paid += paid
            running_balance += (total - paid)

            transactions.append({
                "id": inv_id,
                "invoice_number": inv_no,
                "date": date_str,
                "total": total,
                "paid": paid,
                "pending": pending,
                "running_balance": round(running_balance, 2),
                "note": note
            })

        customer_info = {
            "name": name,
            "phone": phone,
            "address": address,
            "total_invoiced": round(total_invoiced, 2),
            "total_paid": round(total_paid, 2),
            "net_dues": round(max(0, running_balance), 2),
            "invoice_count": len(transactions)
        }

        return customer_info, transactions
    finally:
        conn.close()


# =====================================
# DAILY SALES & PROFIT SUMMARY (Z-REPORT)
# =====================================

def get_daily_sales_and_profit(target_date=None):
    """
    Computes day-end summary metrics and profit report for a given date (default: today).
    Returns dict containing:
      - total_sales: Total billed amount today
      - total_cash_collected: Total paid on bills created today
      - total_credit_extended: Total pending balance on bills created today
      - invoice_count: Total invoices today
      - gross_profit: Estimated gross profit (Actual Selling Total - Total Purchase Cost)
      - items_sold: List of tuples (product_name, qty_sold, selling_total, cost_total, profit)
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        date_clause = "date(invoices.invoice_date) = date('now', 'localtime')"
        date_param = ()
        if target_date:
            date_clause = "date(invoices.invoice_date) = date(?)"
            date_param = (target_date,)


        # 1. High-level totals
        cursor.execute(f"""
        SELECT
            COUNT(invoices.id),
            COALESCE(SUM(invoices.total), 0),
            COALESCE(SUM(invoices.paid), 0),
            COALESCE(SUM(invoices.pending), 0)
        FROM invoices
        WHERE {date_clause}
          AND COALESCE(invoices.status, 'ACTIVE') != 'CANCELLED'
        """, date_param)

        inv_count, total_sales, total_paid, total_pending = cursor.fetchone()

        # 2. Product-wise sales and gross profit calculation
        cursor.execute(f"""
        SELECT
            p.name,
            SUM(ii.quantity) as total_qty,
            SUM(ii.total) as item_revenue,
            SUM(CAST(COALESCE(p.purchase_price, 0) AS REAL) * ii.quantity) as item_cost,
            SUM(ii.total - (CAST(COALESCE(p.purchase_price, 0) AS REAL) * ii.quantity)) as item_profit
        FROM invoice_items ii
        JOIN invoices ON ii.invoice_id = invoices.id
        JOIN products p ON ii.product_id = p.id
        WHERE {date_clause}
          AND COALESCE(invoices.status, 'ACTIVE') != 'CANCELLED'
        GROUP BY p.id, p.name
        ORDER BY item_profit DESC
        """, date_param)

        items_sold = cursor.fetchall()
        total_gross_profit = sum(row[4] for row in items_sold) if items_sold else 0.0

        return {
            "date": target_date if target_date else datetime.now().strftime("%d-%m-%Y"),
            "invoice_count": inv_count,
            "total_sales": round(float(total_sales), 2),
            "total_cash_collected": round(float(total_paid), 2),
            "total_credit_extended": round(float(total_pending), 2),
            "gross_profit": round(float(total_gross_profit), 2),
            "items_sold": items_sold
        }
    finally:
        conn.close()



