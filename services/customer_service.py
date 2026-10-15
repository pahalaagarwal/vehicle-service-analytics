from db import get_db_connection

def get_all_customers():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.*, COUNT(v.vehicle_id) as vehicle_count
        FROM customers c
        LEFT JOIN vehicles v ON c.customer_id = v.customer_id
        GROUP BY c.customer_id
        ORDER BY c.customer_id DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_customer_by_id(customer_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM customers WHERE customer_id = ?", (customer_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def create_customer(name, phone, email, address=""):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO customers (name, phone, email, address) VALUES (?, ?, ?, ?)",
        (name.strip(), phone.strip(), email.strip(), address.strip())
    )
    conn.commit()
    customer_id = cursor.lastrowid
    conn.close()
    return customer_id

def update_customer(customer_id, name, phone, email, address=""):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE customers SET name = ?, phone = ?, email = ?, address = ? WHERE customer_id = ?",
        (name.strip(), phone.strip(), email.strip(), address.strip(), customer_id)
    )
    conn.commit()
    conn.close()
    return True

def delete_customer(customer_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM customers WHERE customer_id = ?", (customer_id,))
    conn.commit()
    conn.close()
    return True
