from db import get_db_connection

def get_all_vehicles():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT v.*, c.name as customer_name, c.phone as customer_phone,
               (SELECT COUNT(*) FROM services s WHERE s.vehicle_id = v.vehicle_id) as service_count,
               (SELECT risk_level FROM predictions p WHERE p.vehicle_id = v.vehicle_id ORDER BY p.predicted_at DESC LIMIT 1) as latest_risk_level,
               (SELECT risk_score FROM predictions p WHERE p.vehicle_id = v.vehicle_id ORDER BY p.predicted_at DESC LIMIT 1) as latest_risk_score
        FROM vehicles v
        JOIN customers c ON v.customer_id = c.customer_id
        ORDER BY v.vehicle_id DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_vehicle_by_id(vehicle_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT v.*, c.name as customer_name, c.phone as customer_phone, c.email as customer_email
        FROM vehicles v
        JOIN customers c ON v.customer_id = c.customer_id
        WHERE v.vehicle_id = ?
    """, (vehicle_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_vehicles_by_customer(customer_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM vehicles WHERE customer_id = ? ORDER BY vehicle_id DESC", (customer_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def create_vehicle(customer_id, registration_no, make, model, year, mileage, fuel_type="Petrol", last_service_date=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO vehicles (customer_id, registration_no, make, model, year, mileage, fuel_type, last_service_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (customer_id, registration_no.upper().strip(), make.strip(), model.strip(), int(year), int(mileage), fuel_type, last_service_date))
    conn.commit()
    vid = cursor.lastrowid
    conn.close()
    return vid

def update_vehicle(vehicle_id, registration_no, make, model, year, mileage, fuel_type="Petrol", last_service_date=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE vehicles
        SET registration_no = ?, make = ?, model = ?, year = ?, mileage = ?, fuel_type = ?, last_service_date = ?
        WHERE vehicle_id = ?
    """, (registration_no.upper().strip(), make.strip(), model.strip(), int(year), int(mileage), fuel_type, last_service_date, vehicle_id))
    conn.commit()
    conn.close()
    return True

def delete_vehicle(vehicle_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM vehicles WHERE vehicle_id = ?", (vehicle_id,))
    conn.commit()
    conn.close()
    return True
