import os
import sys
import ctypes
from ctypes import wintypes
from datetime import datetime

class DOC_INFO_1(ctypes.Structure):
    _fields_ = [
        ('pDocName', wintypes.LPCWSTR),
        ('pOutputFile', wintypes.LPCWSTR),
        ('pDatatype', wintypes.LPCWSTR),
    ]

class PRINTER_INFO_1(ctypes.Structure):
    _fields_ = [
        ('flags', wintypes.DWORD),
        ('pDescription', wintypes.LPCWSTR),
        ('pName', wintypes.LPCWSTR),
        ('pComment', wintypes.LPCWSTR),
    ]

def get_available_printers():
    """Return list of all installed printer names on Windows (instant winspool)."""
    printers = []
    if sys.platform != 'win32':
        return printers
    try:
        winspool = ctypes.WinDLL('winspool.drv')
        flags = 2 | 4  # PRINTER_ENUM_LOCAL | PRINTER_ENUM_CONNECTIONS
        cbNeeded = wintypes.DWORD(0)
        cReturned = wintypes.DWORD(0)
        winspool.EnumPrintersW(flags, None, 1, None, 0, ctypes.byref(cbNeeded), ctypes.byref(cReturned))
        if cbNeeded.value > 0:
            buf = (ctypes.c_byte * cbNeeded.value)()
            if winspool.EnumPrintersW(flags, None, 1, buf, cbNeeded.value, ctypes.byref(cbNeeded), ctypes.byref(cReturned)):
                p_info = ctypes.cast(buf, ctypes.POINTER(PRINTER_INFO_1))
                for i in range(cReturned.value):
                    if p_info[i].pName:
                        printers.append(p_info[i].pName)
    except Exception:
        pass
    return printers

def find_thermal_printer():
    printers = get_available_printers()
    keywords = ['POS80', 'POS-80', 'H80I', 'H80', 'HOIN', 'HELETT', 'XP-80', '80MM', 'RECEIPT', 'THERMAL', 'POS']
    for kw in keywords:
        for p in printers:
            if kw.lower() in p.lower():
                return p
    return None

def _normalize_items(raw_items):
    """Normalizes both dict-based cart items and tuple-based database items into uniform dicts"""
    normalized = []
    for it in raw_items:
        if isinstance(it, dict):
            normalized.append({
                "name": str(it.get("name", "")),
                "quantity": it.get("quantity", 0),
                "price": float(it.get("price", 0) or 0),
                "mrp": float(it.get("mrp", 0) or 0),
                "unit": str(it.get("unit", "Pcs") or "Pcs"),
                "increase": float(it.get("increase", 0) or 0),
                "discount": float(it.get("discount", 0) or 0),
                "discount_base": str(it.get("discount_base", "Price") or "Price"),
                "total": float(it.get("total", 0) or 0)
            })
        elif isinstance(it, (list, tuple)):
            if len(it) == 7:
                qty, name, price, unit, disc, disc_base, tot = it
                normalized.append({
                    "name": str(name),
                    "quantity": qty,
                    "price": float(price or 0),
                    "mrp": 0.0,
                    "unit": str(unit or "Pcs"),
                    "increase": 0.0,
                    "discount": float(disc or 0),
                    "discount_base": str(disc_base or "Price"),
                    "total": float(tot or 0)
                })
            elif len(it) == 8:
                qty, name, mrp, price, unit, disc, disc_base, tot = it[:8]
                normalized.append({
                    "name": str(name),
                    "quantity": qty,
                    "mrp": float(mrp or 0),
                    "price": float(price or 0),
                    "unit": str(unit or "Pcs"),
                    "increase": 0.0,
                    "discount": float(disc or 0),
                    "discount_base": str(disc_base or "Price"),
                    "total": float(tot or 0)
                })
            elif len(it) >= 9:
                qty, name, mrp, price, unit, disc, disc_base, tot, inc = it[:9]
                normalized.append({
                    "name": str(name),
                    "quantity": qty,
                    "mrp": float(mrp or 0),
                    "price": float(price or 0),
                    "unit": str(unit or "Pcs"),
                    "increase": float(inc or 0),
                    "discount": float(disc or 0),
                    "discount_base": str(disc_base or "Price"),
                    "total": float(tot or 0)
                })
            elif len(it) >= 3:
                # Minimal fallback: (qty, name, price, ...)
                qty = it[0]
                name = it[1]
                price = it[2]
                tot = it[3] if len(it) > 3 else (qty * price)
                normalized.append({
                    "name": str(name),
                    "quantity": qty,
                    "mrp": 0.0,
                    "price": float(price or 0),
                    "unit": "Pcs",
                    "discount": 0.0,
                    "discount_base": "Price",
                    "total": float(tot or 0)
                })
    return normalized

def amount_to_indian_words(num):
    """Converts a numerical amount into Indian currency words."""
    try:
        val = float(num)
    except (ValueError, TypeError):
        return ""
    if val == 0:
        return "Rupees Zero Only"
    is_negative = val < 0
    val = abs(val)
    rupees = int(val)
    paise = int(round((val - rupees) * 100))
    if paise == 100:
        rupees += 1
        paise = 0
    ones = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
            "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
            "Seventeen", "Eighteen", "Nineteen"]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]
    def two_digits(n):
        if n == 0:
            return ""
        elif n < 20:
            return ones[n]
        else:
            t = tens[n // 10]
            o = ones[n % 10]
            return f"{t} {o}".strip()
    def three_digits(n):
        h = n // 100
        r = n % 100
        res = []
        if h > 0:
            res.append(f"{ones[h]} Hundred")
        if r > 0:
            res.append(two_digits(r))
        return " ".join(res).strip()
    crore = rupees // 10000000
    rupees %= 10000000
    lakh = rupees // 100000
    rupees %= 100000
    thousand = rupees // 1000
    rupees %= 1000
    hundreds = rupees
    parts = []
    if crore > 0:
        parts.append(f"{two_digits(crore)} Crore")
    if lakh > 0:
        parts.append(f"{two_digits(lakh)} Lakh")
    if thousand > 0:
        parts.append(f"{two_digits(thousand)} Thousand")
    if hundreds > 0:
        parts.append(three_digits(hundreds))
    rupees_str = " ".join(parts).strip()
    if not rupees_str:
        rupees_str = "Zero"
    words = f"Rupees {rupees_str}"
    if is_negative:
        words = f"Minus {words}"
    if paise > 0:
        words += f" and {two_digits(paise)} Paise"
    words += " Only"
    return words

def format_esc_pos_receipt(invoice_number, customer_name, items, grand_total, paid_amount=0, note='', date_str=None):
    clean_num = str(invoice_number).replace('INV-', '').strip()
    d_str = date_str or datetime.now().strftime('%d-%m-%Y  %I:%M %p')
    ESC = b'\x1b'
    GS = b'\x1d'
    INIT = ESC + b'@'
    FONT_A = ESC + b'M\x00'
    ALIGN_LEFT = ESC + b'a\x00'
    ALIGN_CENTER = ESC + b'a\x01'
    ALIGN_RIGHT = ESC + b'a\x02'
    BOLD_ON = ESC + b'E\x01'
    BOLD_OFF = ESC + b'E\x00'
    FEED_CUT = b'\n\n' + GS + b'V\x42\x00'

    normalized_items = _normalize_items(items)

    out = bytearray()
    out.extend(INIT)
    out.extend(FONT_A)
    out.extend(ALIGN_CENTER + BOLD_ON + b'ESTIMATE ONLY\n' + BOLD_OFF)
    out.extend(b'Date: ' + d_str.encode('ascii', 'replace') + b'\n')
    out.extend(ALIGN_LEFT)
    out.extend(f' Est No   : INV-{clean_num}\n'.encode('ascii', 'replace'))
    out.extend(BOLD_ON + f' Customer : {customer_name.upper()}\n'.encode('ascii', 'replace') + BOLD_OFF)
    out.extend(b'=' * 48 + b'\n')

    # Header: 48 Chars Font A
    out.extend(BOLD_ON + f" {'Item Description & Pricing Details':<37}{'Amount':>10}\n".encode('ascii', 'replace') + BOLD_OFF)
    out.extend(b'-' * 48 + b'\n')

    serial = 1
    total_qty = 0
    for it in normalized_items:
        qty = it.get('quantity', 0)
        total_qty += qty
        name = str(it.get('name', ''))[:42]
        mrp = float(it.get('mrp', 0) or 0)
        price = float(it.get('price', 0) or 0)
        unit = str(it.get('unit', 'Pcs') or 'Pcs').strip()
        inc = float(it.get('increase', 0) or 0)
        disc = float(it.get('discount', 0) or 0)
        tot = float(it.get('total', 0) or 0)
        tot_str = f"{tot:,.2f}"

        # Line 1: Item Name in Bold
        out.extend(BOLD_ON + f" {serial}. {name}\n".encode('ascii', 'replace') + BOLD_OFF)

        # Line 2: Details & Tags
        unit_str = f" {unit}" if unit else " pcs"
        left_sub = f"    {qty}{unit_str} x Rs.{price:,.2f}"

        extra_tags = []
        if mrp > 0:
            extra_tags.append(f"MRP: {mrp:,.0f}")
        if inc > 0:
            inc_tag = f"{int(inc) if inc.is_integer() else inc}%"
            extra_tags.append(f"Inc: +{inc_tag}")
        if disc > 0:
            disc_tag = f"{int(disc) if disc.is_integer() else disc}%"
            extra_tags.append(f"Disc: -{disc_tag}")

        if extra_tags:
            left_sub += f" ({' | '.join(extra_tags)})"

        if len(left_sub) > 34:
            left_sub = left_sub[:34]

        out.extend(f"{left_sub:<35}{tot_str:>12}\n".encode('ascii', 'replace'))
        if serial < len(normalized_items):
            out.extend(b'\n')  # Explicit blank line between items for guaranteed physical separation
        serial += 1

    out.extend(b'=' * 48 + b'\n')
    out.extend(f" Total Items: {len(normalized_items)}   |   Total Qty: {total_qty}\n".encode('ascii', 'replace'))
    out.extend(b'\n')  # Clean breathing gap before Grand Total
    out.extend(ALIGN_RIGHT + BOLD_ON + f"GRAND TOTAL: Rs. {grand_total:,.2f}\n".encode('ascii', 'replace') + BOLD_OFF)
    
    # Grand Total in Words
    words = amount_to_indian_words(grand_total)
    if words:
        import textwrap
        wrapped_words = textwrap.wrap(f"({words})", width=46)
        for w_line in wrapped_words:
            out.extend(ALIGN_RIGHT + f"{w_line}\n".encode('ascii', 'replace'))

    if note and note.strip():
        out.extend(ALIGN_LEFT + f"Note: {note.strip()}\n".encode('ascii', 'replace'))
    out.extend(ALIGN_CENTER + b'------------------------------------------------\n')
    out.extend(b'Goods exchangeable in 7 days in sealed pack.\n')
    out.extend(b'No return on tinted paints. GST applicable.\n')
    out.extend(BOLD_ON + b'BizDabba by Wokdens.com\n' + BOLD_OFF)
    out.extend(FEED_CUT)
    return bytes(out)

def send_raw_to_printer(printer_name, data: bytes, doc_name='Receipt'):
    if sys.platform != 'win32':
        return False, 'Direct printing is only supported on Windows.'
    try:
        winspool = ctypes.WinDLL("winspool.drv")
        hPrinter = wintypes.HANDLE()
        if not winspool.OpenPrinterW(printer_name, ctypes.byref(hPrinter), None):
            return False, f'Could not open printer {printer_name} (Error: {ctypes.GetLastError()})'
        doc_info = DOC_INFO_1()
        doc_info.pDocName = doc_name
        doc_info.pOutputFile = None
        doc_info.pDatatype = 'RAW'
        job_id = winspool.StartDocPrinterW(hPrinter, 1, ctypes.byref(doc_info))
        if job_id == 0:
            winspool.ClosePrinter(hPrinter)
            return False, f'StartDocPrinter failed (Error: {ctypes.GetLastError()})'
        winspool.StartPagePrinter(hPrinter)
        written = wintypes.DWORD()
        winspool.WritePrinter(hPrinter, data, len(data), ctypes.byref(written))
        winspool.EndPagePrinter(hPrinter)
        winspool.EndDocPrinter(hPrinter)
        winspool.ClosePrinter(hPrinter)
        return True, f'Successfully printed on {printer_name}'
    except Exception as e:
        return False, str(e)

def print_receipt_direct(invoice_number, customer_name, items, grand_total, paid_amount=0, note='', date_str=None, printer_name=None):
    target_printer = printer_name or find_thermal_printer()
    if not target_printer:
        return False, 'No thermal POS printer detected.'
    raw_data = format_esc_pos_receipt(
        invoice_number=invoice_number,
        customer_name=customer_name,
        items=items,
        grand_total=grand_total,
        paid_amount=paid_amount,
        note=note,
        date_str=date_str
    )
    return send_raw_to_printer(target_printer, raw_data, doc_name=f'INV-{invoice_number}')
