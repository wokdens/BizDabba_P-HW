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
        note TEXT DEFAULT ''
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
    """Clear all transactional and inventory data so the app starts fresh."""

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM invoice_items")
    cursor.execute("DELETE FROM invoices")
    cursor.execute("DELETE FROM products")
    cursor.execute("DELETE FROM customers")
    cursor.execute("DELETE FROM categories")

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sqlite_sequence'")
    if cursor.fetchone():
        cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('products', 'customers', 'invoices', 'invoice_items', 'categories')")

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
        invoice_date
    )                    
    VALUES (?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))
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
        COALESCE(invoices.note, '')
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


def close_database_on_exit():
    """
    Executes a WAL truncate checkpoint and database integrity check on clean application exit.
    Ensures that WAL file changes are safely flushed into the main database file.
    """
    try:
        if not os.path.exists(DATABASE_PATH):
            return "no_database"

        conn = get_connection()
        try:
            # Checkpoint WAL cleanly into the primary DB file
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check")
            row = cursor.fetchone()
            status = row[0] if row else "ok"
            return status
        finally:
            conn.close()
    except Exception as e:
        print(f"Database exit check error: {e}")
        return str(e)


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



