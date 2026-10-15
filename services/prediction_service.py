import os
import joblib
import pandas as pd
from datetime import datetime
from config import Config
from db import get_db_connection

MODEL_PATH = os.path.join(Config.ML_MODEL_DIR, 'breakdown_risk_model.joblib')
_cached_model = None

def get_model():
    """Loads and caches the scikit-learn pipeline."""
    global _cached_model
    if _cached_model is None:
        if os.path.exists(MODEL_PATH):
            try:
                _cached_model = joblib.load(MODEL_PATH)
            except Exception as e:
                print(f"Error loading model from {MODEL_PATH}: {e}")
                _cached_model = None
    return _cached_model

def predict_risk(vehicle_age_years, mileage_km, days_since_last_service,
                 service_frequency_per_year, avg_service_cost,
                 major_repairs_count, breakdown_history_count, fuel_type="Petrol"):
    """
    Computes breakdown risk score and classification.
    Uses trained Scikit-learn pipeline if available, otherwise heuristic fallback.
    """
    model = get_model()

    input_df = pd.DataFrame([{
        'vehicle_age_years': float(vehicle_age_years),
        'mileage_km': float(mileage_km),
        'days_since_last_service': float(days_since_last_service),
        'service_frequency_per_year': float(service_frequency_per_year),
        'avg_service_cost': float(avg_service_cost),
        'major_repairs_count': int(major_repairs_count),
        'breakdown_history_count': int(breakdown_history_count),
        'fuel_type': str(fuel_type)
    }])

    factors = []

    if days_since_last_service > 180:
        factors.append(f"Service overdue by {int(days_since_last_service - 180)} days past standard interval")
    if mileage_km > 100000:
        factors.append(f"High cumulative mileage ({int(mileage_km):,} km)")
    if vehicle_age_years >= 8:
        factors.append(f"Aging vehicle lifecycle ({int(vehicle_age_years)} years)")
    if major_repairs_count >= 2:
        factors.append(f"Recurring major repairs history ({major_repairs_count} previous incidents)")
    if breakdown_history_count >= 1:
        factors.append(f"Prior roadside breakdown recorded ({breakdown_history_count} occurrences)")
    if service_frequency_per_year < 1.0:
        factors.append("Irregular preventive maintenance cadence (< 1 service/yr)")

    if model is not None:
        try:
            prob = float(model.predict_proba(input_df)[0][1])
            pred_class = int(model.predict(input_df)[0])
        except Exception as e:
            print(f"Model inference failed, falling back to heuristic: {e}")
            prob = None
    else:
        prob = None

    if prob is None:
        # Heuristic fallback
        score = 0.05
        score += (min(vehicle_age_years, 15) / 15.0) * 0.25
        score += (min(mileage_km, 200000) / 200000.0) * 0.25
        score += (min(days_since_last_service, 400) / 400.0) * 0.25
        score += (min(breakdown_history_count, 4) / 4.0) * 0.15
        score += (min(major_repairs_count, 5) / 5.0) * 0.10
        if fuel_type == 'Diesel':
            score += 0.05
        prob = round(max(0.02, min(0.98, score)), 3)
        pred_class = 1 if prob >= 0.50 else 0

    risk_score = round(prob, 3)

    if risk_score >= 0.70:
        risk_level = "High"
    elif risk_score >= 0.40:
        risk_level = "Medium"
    else:
        risk_level = "Low"

    service_due = 1 if (days_since_last_service >= 180 or risk_score >= 0.55) else 0

    if not factors:
        factors.append("Vehicle operating within optimal operational parameters")

    key_factors_text = "; ".join(factors)

    return {
        'risk_score': risk_score,
        'risk_percentage': round(risk_score * 100, 1),
        'risk_level': risk_level,
        'breakdown_predicted': pred_class,
        'service_due': service_due,
        'key_factors': key_factors_text,
        'factors_list': factors
    }

def save_prediction(vehicle_id, risk_score, risk_level, breakdown_predicted, service_due, key_factors):
    """Saves prediction output into the predictions table."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO predictions (vehicle_id, risk_score, risk_level, breakdown_predicted, service_due, key_factors)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (vehicle_id, risk_score, risk_level, breakdown_predicted, service_due, key_factors))
    conn.commit()
    pred_id = cursor.lastrowid
    conn.close()
    return pred_id

def get_prediction_history(limit=50):
    """Fetches past predictions with vehicle and customer details."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.*, v.registration_no, v.make, v.model, v.mileage, c.name as customer_name
        FROM predictions p
        JOIN vehicles v ON p.vehicle_id = v.vehicle_id
        JOIN customers c ON v.customer_id = c.customer_id
        ORDER BY p.predicted_at DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def run_prediction_for_vehicle(vehicle_id):
    """Extracts features for a specific vehicle and computes + saves prediction."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT v.*,
               (SELECT COUNT(*) FROM services s WHERE s.vehicle_id = v.vehicle_id) as total_services,
               (SELECT COUNT(*) FROM services s WHERE s.vehicle_id = v.vehicle_id AND s.service_type = 'Major Repair') as major_repairs,
               (SELECT COUNT(*) FROM services s WHERE s.vehicle_id = v.vehicle_id AND s.service_type = 'Emergency Breakdown') as breakdowns,
               (SELECT AVG(s.labour_cost + COALESCE((SELECT SUM(p.quantity*p.cost) FROM parts p WHERE p.service_id = s.service_id), 0))
                FROM services s WHERE s.vehicle_id = v.vehicle_id) as avg_cost
        FROM vehicles v
        WHERE v.vehicle_id = ?
    """, (vehicle_id,))
    v = cursor.fetchone()
    conn.close()

    if not v:
        return None

    current_year = datetime.now().year
    vehicle_age = max(1, current_year - v['year'])

    # Days since last service
    if v['last_service_date']:
        try:
            last_date = datetime.strptime(v['last_service_date'], "%Y-%m-%d")
            days_since = (datetime.now() - last_date).days
        except Exception:
            days_since = 120
    else:
        days_since = 240

    service_freq = round(max(0.5, (v['total_services'] or 1) / float(vehicle_age)), 1)
    avg_cost = round(v['avg_cost'] or 120.0, 2)
    major_repairs = v['major_repairs'] or 0
    breakdowns = v['breakdowns'] or 0

    res = predict_risk(
        vehicle_age_years=vehicle_age,
        mileage_km=v['mileage'],
        days_since_last_service=days_since,
        service_frequency_per_year=service_freq,
        avg_service_cost=avg_cost,
        major_repairs_count=major_repairs,
        breakdown_history_count=breakdowns,
        fuel_type=v['fuel_type'] or 'Petrol'
    )

    save_prediction(
        vehicle_id=vehicle_id,
        risk_score=res['risk_score'],
        risk_level=res['risk_level'],
        breakdown_predicted=res['breakdown_predicted'],
        service_due=res['service_due'],
        key_factors=res['key_factors']
    )

    return res
