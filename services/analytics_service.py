from db import get_db_connection
from datetime import datetime

def get_dashboard_kpis():
    """Calculates key performance indicators for the dashboard."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM vehicles")
    total_vehicles = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM customers")
    total_customers = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM services")
    total_services = cursor.fetchone()[0]

    # Total revenue/cost (labour + parts)
    cursor.execute("SELECT COALESCE(SUM(labour_cost), 0.0) FROM services")
    total_labour = cursor.fetchone()[0]

    cursor.execute("SELECT COALESCE(SUM(quantity * cost), 0.0) FROM parts")
    total_parts = cursor.fetchone()[0]
    total_revenue = round(total_labour + total_parts, 2)

    # High risk vehicles count
    cursor.execute("""
        SELECT COUNT(DISTINCT vehicle_id) FROM predictions
        WHERE risk_level = 'High'
    """)
    high_risk_count = cursor.fetchone()[0]

    # Vehicles due for service (either predicted service_due = 1 or last service > 180 days)
    cursor.execute("""
        SELECT COUNT(DISTINCT v.vehicle_id)
        FROM vehicles v
        LEFT JOIN predictions p ON v.vehicle_id = p.vehicle_id
        WHERE p.service_due = 1
           OR v.last_service_date IS NULL
           OR julianday('now') - julianday(v.last_service_date) > 180
    """)
    services_due = cursor.fetchone()[0]

    conn.close()

    return {
        'total_vehicles': total_vehicles,
        'total_customers': total_customers,
        'total_services': total_services,
        'total_revenue': total_revenue,
        'high_risk_count': high_risk_count,
        'services_due': services_due
    }

def get_monthly_cost_trends():
    """Aggregates service cost by month for time-series trend analysis."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            substr(s.service_date, 1, 7) as month,
            COUNT(s.service_id) as service_count,
            SUM(s.labour_cost) as total_labour,
            COALESCE((
                SELECT SUM(p.quantity * p.cost)
                FROM parts p
                JOIN services s2 ON p.service_id = s2.service_id
                WHERE substr(s2.service_date, 1, 7) = substr(s.service_date, 1, 7)
            ), 0.0) as total_parts
        FROM services s
        GROUP BY substr(s.service_date, 1, 7)
        ORDER BY month ASC
    """)
    rows = cursor.fetchall()
    conn.close()

    months = []
    labour_costs = []
    parts_costs = []
    total_costs = []

    for r in rows:
        m = r['month']
        if not m:
            continue
        labour = round(r['total_labour'] or 0.0, 2)
        parts = round(r['total_parts'] or 0.0, 2)
        months.append(m)
        labour_costs.append(labour)
        parts_costs.append(parts)
        total_costs.append(round(labour + parts, 2))

    return {
        'months': months,
        'labour': labour_costs,
        'parts': parts_costs,
        'total': total_costs
    }

def get_service_type_breakdown():
    """Returns distribution of service types."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT service_type, COUNT(*) as count,
               ROUND(AVG(labour_cost), 2) as avg_labour
        FROM services
        GROUP BY service_type
        ORDER BY count DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_top_parts_replaced(limit=6):
    """Returns most frequently replaced parts with costs."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT part_name,
               SUM(quantity) as total_qty,
               ROUND(SUM(quantity * cost), 2) as total_expenditure
        FROM parts
        GROUP BY part_name
        ORDER BY total_qty DESC, total_expenditure DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_risk_distribution():
    """Returns count and percentage of vehicles in each risk tier."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        WITH LatestPredictions AS (
            SELECT p.vehicle_id, p.risk_level,
                   ROW_NUMBER() OVER (PARTITION BY p.vehicle_id ORDER BY p.predicted_at DESC) as rn
            FROM predictions p
        )
        SELECT risk_level, COUNT(*) as count
        FROM LatestPredictions
        WHERE rn = 1
        GROUP BY risk_level
    """)
    rows = cursor.fetchall()
    conn.close()

    dist = {'Low': 0, 'Medium': 0, 'High': 0}
    for r in rows:
        if r['risk_level'] in dist:
            dist[r['risk_level']] = r['count']
    return dist

def get_age_group_cost_analysis():
    """Diagnostic analytics: vehicle age group vs average service cost."""
    conn = get_db_connection()
    cursor = conn.cursor()
    current_year = datetime.now().year
    cursor.execute(f"""
        SELECT
            CASE
                WHEN ({current_year} - v.year) <= 3 THEN '0-3 Years (New)'
                WHEN ({current_year} - v.year) <= 6 THEN '4-6 Years (Moderate)'
                WHEN ({current_year} - v.year) <= 10 THEN '7-10 Years (Aging)'
                ELSE '10+ Years (Senior)'
            END as age_group,
            COUNT(DISTINCT v.vehicle_id) as vehicle_count,
            ROUND(AVG(s.labour_cost + COALESCE((SELECT SUM(p.quantity * p.cost) FROM parts p WHERE p.service_id = s.service_id), 0.0)), 2) as avg_cost
        FROM vehicles v
        JOIN services s ON v.vehicle_id = s.vehicle_id
        GROUP BY age_group
        ORDER BY avg_cost ASC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]
