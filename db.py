import sqlite3
import os
from werkzeug.security import generate_password_hash
from config import Config

def get_db_connection():
    """Returns a SQLite connection with Row factory enabled for dictionary-like access."""
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    """Initializes the database schema with normalized relational tables."""
    os.makedirs(os.path.dirname(Config.DATABASE_PATH), exist_ok=True)
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('admin', 'service_advisor', 'customer')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 2. customers table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT NOT NULL,
        email TEXT NOT NULL,
        address TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 3. vehicles table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vehicles (
        vehicle_id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        registration_no TEXT UNIQUE NOT NULL,
        make TEXT NOT NULL,
        model TEXT NOT NULL,
        year INTEGER NOT NULL,
        mileage INTEGER NOT NULL,
        fuel_type TEXT DEFAULT 'Petrol',
        last_service_date TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (customer_id) REFERENCES customers (customer_id) ON DELETE CASCADE
    )
    """)

    # 4. services table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS services (
        service_id INTEGER PRIMARY KEY AUTOINCREMENT,
        vehicle_id INTEGER NOT NULL,
        service_date TEXT NOT NULL,
        service_type TEXT NOT NULL,
        mileage INTEGER NOT NULL,
        labour_cost REAL NOT NULL DEFAULT 0.0,
        status TEXT NOT NULL DEFAULT 'Completed' CHECK(status IN ('Scheduled', 'In Progress', 'Completed', 'Cancelled')),
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (vehicle_id) REFERENCES vehicles (vehicle_id) ON DELETE CASCADE
    )
    """)

    # 5. parts table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS parts (
        part_id INTEGER PRIMARY KEY AUTOINCREMENT,
        service_id INTEGER NOT NULL,
        part_name TEXT NOT NULL,
        quantity INTEGER NOT NULL DEFAULT 1,
        cost REAL NOT NULL DEFAULT 0.0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (service_id) REFERENCES services (service_id) ON DELETE CASCADE
    )
    """)

    # 6. predictions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS predictions (
        prediction_id INTEGER PRIMARY KEY AUTOINCREMENT,
        vehicle_id INTEGER NOT NULL,
        risk_score REAL NOT NULL,
        risk_level TEXT NOT NULL,
        breakdown_predicted INTEGER NOT NULL,
        service_due INTEGER NOT NULL,
        key_factors TEXT,
        predicted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (vehicle_id) REFERENCES vehicles (vehicle_id) ON DELETE CASCADE
    )
    """)

    conn.commit()
    conn.close()

def seed_database():
    """Seeds the database with initial users, customers, vehicles, services, and parts."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if data already exists
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] > 0:
        conn.close()
        return

    # Seed Users
    admin_pw = generate_password_hash("admin123")
    advisor_pw = generate_password_hash("advisor123")
    customer_pw = generate_password_hash("customer123")

    users = [
        ("admin", "admin@autocare.com", admin_pw, "admin"),
        ("advisor", "advisor@autocare.com", advisor_pw, "service_advisor"),
        ("john_doe", "john@example.com", customer_pw, "customer")
    ]
    cursor.executemany("INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)", users)

    # Seed Customers
    customers = [
        ("John Doe", "+1-555-0101", "john@example.com", "742 Evergreen Terrace, Springfield"),
        ("Sarah Jenkins", "+1-555-0102", "sarah.j@example.com", "124 Conch Street, Bikini"),
        ("Michael Chang", "+1-555-0103", "m.chang@example.com", "42 Wallaby Way, Sydney"),
        ("Emily Watson", "+1-555-0104", "emily.w@example.com", "221B Baker Street, London"),
        ("Robert Taylor", "+1-555-0105", "robert.t@example.com", "1040 Elm Street, Dallas")
    ]
    cursor.executemany("INSERT INTO customers (name, phone, email, address) VALUES (?, ?, ?, ?)", customers)

    # Seed Vehicles
    vehicles = [
        (1, "KA-01-AB-1234", "Toyota", "Corolla", 2017, 85000, "Petrol", "2024-03-15"),
        (1, "KA-01-CD-5678", "Honda", "Civic", 2020, 42000, "Petrol", "2024-07-20"),
        (2, "MH-02-XY-9012", "Ford", "EcoSport", 2016, 112000, "Diesel", "2023-11-10"),
        (3, "DL-04-GH-3456", "Hyundai", "Creta", 2019, 68000, "Diesel", "2024-05-02"),
        (4, "KA-05-JK-7890", "Volkswagen", "Polo", 2015, 134000, "Petrol", "2023-09-18"),
        (5, "TN-07-LM-2345", "Maruti", "Swift", 2021, 28000, "Petrol", "2024-08-10")
    ]
    cursor.executemany("""
    INSERT INTO vehicles (customer_id, registration_no, make, model, year, mileage, fuel_type, last_service_date)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, vehicles)

    # Seed Services
    services_data = [
        (1, "2023-03-10", "Routine", 70000, 120.0, "Completed", "Periodic 70k service and fluid check"),
        (1, "2024-03-15", "Routine", 85000, 150.0, "Completed", "Engine oil replacement and filter change"),
        (2, "2023-08-12", "Inspection", 30000, 80.0, "Completed", "General multipoint safety inspection"),
        (2, "2024-07-20", "Routine", 42000, 140.0, "Completed", "40k service, tyre rotation"),
        (3, "2023-04-18", "Routine", 95000, 160.0, "Completed", "Regular oil, brake inspection"),
        (3, "2023-11-10", "Major Repair", 112000, 450.0, "Completed", "Suspension repair and brake pad replacement"),
        (4, "2023-10-05", "Routine", 55000, 130.0, "Completed", "Routine checkup and wheel alignment"),
        (4, "2024-05-02", "Routine", 68000, 175.0, "Completed", "Coolant flush and spark plugs"),
        (5, "2022-12-14", "Major Repair", 115000, 520.0, "Completed", "Clutch plate assembly and timing belt"),
        (5, "2023-09-18", "Emergency Breakdown", 134000, 680.0, "Completed", "Alternator breakdown and battery replacement"),
        (6, "2024-08-10", "Routine", 28000, 110.0, "Completed", "First paid scheduled service")
    ]
    cursor.executemany("""
    INSERT INTO services (vehicle_id, service_date, service_type, mileage, labour_cost, status, notes)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, services_data)

    # Seed Parts
    parts_data = [
        (1, "Engine Oil 5W-30 (4L)", 1, 55.0),
        (1, "Oil Filter", 1, 15.0),
        (2, "Synthetic Oil (4L)", 1, 65.0),
        (2, "Air Filter", 1, 20.0),
        (3, "Wiper Blades Set", 1, 35.0),
        (4, "Cabin Air Filter", 1, 25.0),
        (5, "Engine Oil 15W-40", 1, 50.0),
        (6, "Front Brake Pads", 2, 90.0),
        (6, "Brake Rotor Set", 1, 140.0),
        (7, "Engine Oil & Filter", 1, 70.0),
        (8, "Spark Plugs (Set of 4)", 1, 45.0),
        (8, "Coolant 3L", 1, 35.0),
        (9, "Clutch Plate Kit", 1, 280.0),
        (9, "Timing Belt Kit", 1, 120.0),
        (10, "Alternator Unit", 1, 310.0),
        (10, "12V 65Ah Battery", 1, 130.0),
        (11, "Engine Oil 0W-20", 1, 60.0),
        (11, "Oil Filter", 1, 18.0)
    ]
    cursor.executemany("INSERT INTO parts (service_id, part_name, quantity, cost) VALUES (?, ?, ?, ?)", parts_data)

    # Seed Predictions
    predictions_data = [
        (3, 0.78, "High", 1, 1, "High mileage (>110k), 330+ days since last service, diesel engine wear"),
        (5, 0.89, "High", 1, 1, "Vehicle age 9 yrs, >130k mileage, past emergency alternator breakdown"),
        (1, 0.45, "Medium", 0, 1, "Mileage 85k, 210 days since last service, due for periodic checkup"),
        (2, 0.15, "Low", 0, 0, "Low mileage (42k), recent routine service, optimal operating health"),
        (4, 0.32, "Low", 0, 0, "Well maintained, regular 6-month service cadence, healthy diagnostics"),
        (6, 0.10, "Low", 0, 0, "New vehicle (2021), 28k mileage, recently serviced")
    ]
    cursor.executemany("""
    INSERT INTO predictions (vehicle_id, risk_score, risk_level, breakdown_predicted, service_due, key_factors)
    VALUES (?, ?, ?, ?, ?, ?)
    """, predictions_data)

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    seed_database()
    print("Database schema created and initial records seeded successfully.")
