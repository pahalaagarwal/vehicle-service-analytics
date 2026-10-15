from db import get_db_connection

def get_all_services():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.*, v.registration_no, v.make, v.model, c.name as customer_name,
               COALESCE((SELECT SUM(p.quantity * p.cost) FROM parts p WHERE p.service_id = s.service_id), 0.0) as parts_cost,
               (s.labour_cost + COALESCE((SELECT SUM(p.quantity * p.cost) FROM parts p WHERE p.service_id = s.service_id), 0.0)) as total_cost
        FROM services s
        JOIN vehicles v ON s.vehicle_id = v.vehicle_id
        JOIN customers c ON v.customer_id = c.customer_id
        ORDER BY s.service_date DESC, s.service_id DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_service_by_id(service_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.*, v.registration_no, v.make, v.model, v.customer_id, c.name as customer_name, c.phone as customer_phone,
               COALESCE((SELECT SUM(p.quantity * p.cost) FROM parts p WHERE p.service_id = s.service_id), 0.0) as parts_cost,
               (s.labour_cost + COALESCE((SELECT SUM(p.quantity * p.cost) FROM parts p WHERE p.service_id = s.service_id), 0.0)) as total_cost
        FROM services s
        JOIN vehicles v ON s.vehicle_id = v.vehicle_id
        JOIN customers c ON v.customer_id = c.customer_id
        WHERE s.service_id = ?
    """, (service_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_services_by_vehicle(vehicle_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.*,
               COALESCE((SELECT SUM(p.quantity * p.cost) FROM parts p WHERE p.service_id = s.service_id), 0.0) as parts_cost,
               (s.labour_cost + COALESCE((SELECT SUM(p.quantity * p.cost) FROM parts p WHERE p.service_id = s.service_id), 0.0)) as total_cost
        FROM services s
        WHERE s.vehicle_id = ?
        ORDER BY s.service_date DESC
    """, (vehicle_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def create_service(vehicle_id, service_date, service_type, mileage, labour_cost, status='Completed', notes=''):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO services (vehicle_id, service_date, service_type, mileage, labour_cost, status, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (vehicle_id, service_date, service_type, int(mileage), float(labour_cost), status, notes))
    service_id = cursor.lastrowid

    # Update vehicle's last_service_date and current mileage if newer
    cursor.execute("""
        UPDATE vehicles
        SET mileage = MAX(mileage, ?),
            last_service_date = ?
        WHERE vehicle_id = ?
    """, (int(mileage), service_date, vehicle_id))

    conn.commit()
    conn.close()
    return service_id

def update_service(service_id, service_date, service_type, mileage, labour_cost, status, notes):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE services
        SET service_date = ?, service_type = ?, mileage = ?, labour_cost = ?, status = ?, notes = ?
        WHERE service_id = ?
    """, (service_date, service_type, int(mileage), float(labour_cost), status, notes, service_id))
    conn.commit()
    conn.close()
    return True

def delete_service(service_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM services WHERE service_id = ?", (service_id,))
    conn.commit()
    conn.close()
    return True

# Parts tracking
def get_parts_for_service(service_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT *, (quantity * cost) as total_part_cost
        FROM parts
        WHERE service_id = ?
        ORDER BY part_id ASC
    """, (service_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def add_part_to_service(service_id, part_name, quantity, cost):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO parts (service_id, part_name, quantity, cost)
        VALUES (?, ?, ?, ?)
    """, (service_id, part_name.strip(), int(quantity), float(cost)))
    conn.commit()
    part_id = cursor.lastrowid
    conn.close()
    return part_id

def delete_part(part_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM parts WHERE part_id = ?", (part_id,))
    conn.commit()
    conn.close()
    return True
