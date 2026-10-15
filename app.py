import os
import csv
import io
import json
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for, flash,
    session, jsonify, send_file, Response
)
from config import Config
from db import init_db, seed_database, get_db_connection
from services import (
    auth_service, customer_service, vehicle_service,
    service_record_service, analytics_service, prediction_service
)

app = Flask(__name__)
app.config.from_object(Config)

# Decorators for auth and role control
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please sign in to access this page.", "warning")
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def role_required(allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash("Please sign in first.", "warning")
                return redirect(url_for('login'))
            user_role = session.get('role', 'customer')
            if user_role not in allowed_roles:
                flash("You do not have permission to access that resource.", "danger")
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.context_processor
def inject_context():
    return {
        'current_user': {
            'user_id': session.get('user_id'),
            'username': session.get('username'),
            'role': session.get('role')
        } if 'user_id' in session else None
    }

# ----------------- AUTHENTICATION ROUTES -----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        user = auth_service.authenticate_user(username, password)
        if user:
            session['user_id'] = user['user_id']
            session['username'] = user['username']
            session['role'] = user['role']
            flash(f"Welcome back, {user['username']}! ({user['role'].replace('_', ' ').title()})", "success")
            next_url = request.args.get('next')
            return redirect(next_url or url_for('dashboard'))
        else:
            flash("Invalid username or password.", "danger")

    return render_template('auth/login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        role = request.form.get('role', 'service_advisor')

        if not username or not email or not password:
            flash("All fields are required.", "danger")
            return render_template('auth/register.html')

        res = auth_service.register_user(username, email, password, role)
        if res.get('success'):
            flash("Account registered successfully! Please sign in.", "success")
            return redirect(url_for('login'))
        else:
            flash(f"Registration failed: {res.get('error')}", "danger")

    return render_template('auth/register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been signed out.", "info")
    return redirect(url_for('login'))

# ----------------- DASHBOARD ROUTE -----------------
@app.route('/')
@app.route('/dashboard')
@login_required
def dashboard():
    kpis = analytics_service.get_dashboard_kpis()
    monthly_trends = analytics_service.get_monthly_cost_trends()
    risk_dist = analytics_service.get_risk_distribution()
    recent_services = service_record_service.get_all_services()[:5]

    # Get vehicles with high risk or overdue service
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT v.*, c.name as customer_name, c.phone as customer_phone,
               p.risk_score, p.risk_level, p.service_due
        FROM vehicles v
        JOIN customers c ON v.customer_id = c.customer_id
        LEFT JOIN predictions p ON v.vehicle_id = p.vehicle_id
        WHERE p.risk_level = 'High' OR p.service_due = 1
        ORDER BY p.risk_score DESC
        LIMIT 6
    """)
    urgent_vehicles = [dict(r) for r in cursor.fetchall()]
    conn.close()

    return render_template(
        'dashboard.html',
        kpis=kpis,
        monthly_trends=monthly_trends,
        risk_dist=risk_dist,
        recent_services=recent_services,
        urgent_vehicles=urgent_vehicles
    )

# ----------------- CUSTOMER MANAGEMENT -----------------
@app.route('/customers')
@login_required
def customers_list():
    customers = customer_service.get_all_customers()
    return render_template('customers/list.html', customers=customers)

@app.route('/customers/add', methods=['GET', 'POST'])
@login_required
def customer_add():
    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        email = request.form.get('email')
        address = request.form.get('address', '')

        if not name or not phone or not email:
            flash("Name, Phone, and Email are mandatory fields.", "danger")
            return render_template('customers/form.html', action='Add', customer=request.form)

        cid = customer_service.create_customer(name, phone, email, address)
        flash(f"Customer '{name}' added successfully (ID: #{cid}).", "success")
        return redirect(url_for('customers_list'))

    return render_template('customers/form.html', action='Add', customer={})

@app.route('/customers/<int:customer_id>/edit', methods=['GET', 'POST'])
@login_required
def customer_edit(customer_id):
    customer = customer_service.get_customer_by_id(customer_id)
    if not customer:
        flash("Customer not found.", "warning")
        return redirect(url_for('customers_list'))

    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        email = request.form.get('email')
        address = request.form.get('address', '')

        customer_service.update_customer(customer_id, name, phone, email, address)
        flash("Customer details updated successfully.", "success")
        return redirect(url_for('customers_list'))

    return render_template('customers/form.html', action='Edit', customer=customer)

@app.route('/customers/<int:customer_id>')
@login_required
def customer_view(customer_id):
    customer = customer_service.get_customer_by_id(customer_id)
    if not customer:
        flash("Customer not found.", "warning")
        return redirect(url_for('customers_list'))

    vehicles = vehicle_service.get_vehicles_by_customer(customer_id)
    return render_template('customers/view.html', customer=customer, vehicles=vehicles)

@app.route('/customers/<int:customer_id>/delete', methods=['POST'])
@login_required
@role_required(['admin'])
def customer_delete(customer_id):
    customer_service.delete_customer(customer_id)
    flash("Customer and associated records deleted.", "info")
    return redirect(url_for('customers_list'))

# ----------------- VEHICLE REGISTRATION -----------------
@app.route('/vehicles')
@login_required
def vehicles_list():
    vehicles = vehicle_service.get_all_vehicles()
    return render_template('vehicles/list.html', vehicles=vehicles)

@app.route('/vehicles/add', methods=['GET', 'POST'])
@login_required
def vehicle_add():
    customers = customer_service.get_all_customers()
    if request.method == 'POST':
        customer_id = request.form.get('customer_id')
        reg_no = request.form.get('registration_no')
        make = request.form.get('make')
        model = request.form.get('model')
        year = request.form.get('year')
        mileage = request.form.get('mileage')
        fuel_type = request.form.get('fuel_type', 'Petrol')
        last_service = request.form.get('last_service_date') or None

        try:
            vid = vehicle_service.create_vehicle(
                customer_id=customer_id,
                registration_no=reg_no,
                make=make,
                model=model,
                year=year,
                mileage=mileage,
                fuel_type=fuel_type,
                last_service_date=last_service
            )
            # Run initial risk prediction on new vehicle
            prediction_service.run_prediction_for_vehicle(vid)
            flash(f"Vehicle '{reg_no}' registered successfully and initial risk score calculated.", "success")
            return redirect(url_for('vehicles_list'))
        except Exception as e:
            flash(f"Error registering vehicle: {e}", "danger")

    return render_template('vehicles/form.html', action='Add', vehicle={}, customers=customers)

@app.route('/vehicles/<int:vehicle_id>/edit', methods=['GET', 'POST'])
@login_required
def vehicle_edit(vehicle_id):
    vehicle = vehicle_service.get_vehicle_by_id(vehicle_id)
    if not vehicle:
        flash("Vehicle not found.", "warning")
        return redirect(url_for('vehicles_list'))

    customers = customer_service.get_all_customers()

    if request.method == 'POST':
        reg_no = request.form.get('registration_no')
        make = request.form.get('make')
        model = request.form.get('model')
        year = request.form.get('year')
        mileage = request.form.get('mileage')
        fuel_type = request.form.get('fuel_type')
        last_service = request.form.get('last_service_date') or None

        try:
            vehicle_service.update_vehicle(
                vehicle_id=vehicle_id,
                registration_no=reg_no,
                make=make,
                model=model,
                year=year,
                mileage=mileage,
                fuel_type=fuel_type,
                last_service_date=last_service
            )
            prediction_service.run_prediction_for_vehicle(vehicle_id)
            flash("Vehicle updated and risk metrics recalculated.", "success")
            return redirect(url_for('vehicles_list'))
        except Exception as e:
            flash(f"Error updating vehicle: {e}", "danger")

    return render_template('vehicles/form.html', action='Edit', vehicle=vehicle, customers=customers)

@app.route('/vehicles/<int:vehicle_id>')
@login_required
def vehicle_view(vehicle_id):
    vehicle = vehicle_service.get_vehicle_by_id(vehicle_id)
    if not vehicle:
        flash("Vehicle not found.", "warning")
        return redirect(url_for('vehicles_list'))

    services = service_record_service.get_services_by_vehicle(vehicle_id)

    # Get predictions for this vehicle
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM predictions
        WHERE vehicle_id = ?
        ORDER BY predicted_at DESC
    """, (vehicle_id,))
    predictions = [dict(r) for r in cursor.fetchall()]
    conn.close()

    latest_pred = predictions[0] if predictions else None

    return render_template(
        'vehicles/view.html',
        vehicle=vehicle,
        services=services,
        predictions=predictions,
        latest_pred=latest_pred
    )

@app.route('/vehicles/<int:vehicle_id>/delete', methods=['POST'])
@login_required
@role_required(['admin'])
def vehicle_delete(vehicle_id):
    vehicle_service.delete_vehicle(vehicle_id)
    flash("Vehicle and associated records deleted.", "info")
    return redirect(url_for('vehicles_list'))

# ----------------- SERVICE BOOKING & PARTS -----------------
@app.route('/services')
@login_required
def services_list():
    services = service_record_service.get_all_services()
    return render_template('services/list.html', services=services)

@app.route('/services/add', methods=['GET', 'POST'])
@login_required
def service_add():
    vehicles = vehicle_service.get_all_vehicles()
    if request.method == 'POST':
        vehicle_id = request.form.get('vehicle_id')
        service_date = request.form.get('service_date')
        service_type = request.form.get('service_type')
        mileage = request.form.get('mileage')
        labour_cost = request.form.get('labour_cost', 0.0)
        status = request.form.get('status', 'Completed')
        notes = request.form.get('notes', '')

        try:
            sid = service_record_service.create_service(
                vehicle_id=vehicle_id,
                service_date=service_date,
                service_type=service_type,
                mileage=mileage,
                labour_cost=labour_cost,
                status=status,
                notes=notes
            )
            # Recompute vehicle risk
            prediction_service.run_prediction_for_vehicle(int(vehicle_id))
            flash(f"Service record #{sid} created successfully. You can now attach parts.", "success")
            return redirect(url_for('service_view', service_id=sid))
        except Exception as e:
            flash(f"Error booking service: {e}", "danger")

    return render_template('services/form.html', action='Add', service={}, vehicles=vehicles)

@app.route('/services/<int:service_id>')
@login_required
def service_view(service_id):
    service = service_record_service.get_service_by_id(service_id)
    if not service:
        flash("Service record not found.", "warning")
        return redirect(url_for('services_list'))

    parts = service_record_service.get_parts_for_service(service_id)
    return render_template('services/view.html', service=service, parts=parts)

@app.route('/services/<int:service_id>/add-part', methods=['POST'])
@login_required
def service_add_part(service_id):
    part_name = request.form.get('part_name')
    quantity = request.form.get('quantity', 1)
    cost = request.form.get('cost', 0.0)

    if part_name and quantity and cost:
        service_record_service.add_part_to_service(service_id, part_name, quantity, cost)
        flash("Part added to service ticket.", "success")
    else:
        flash("Please provide valid part name, quantity, and cost.", "danger")

    return redirect(url_for('service_view', service_id=service_id))

@app.route('/services/part/<int:part_id>/delete', methods=['POST'])
@login_required
def service_delete_part(part_id):
    service_id = request.form.get('service_id')
    service_record_service.delete_part(part_id)
    flash("Part removed from ticket.", "info")
    return redirect(url_for('service_view', service_id=service_id))

@app.route('/services/<int:service_id>/delete', methods=['POST'])
@login_required
@role_required(['admin'])
def service_delete(service_id):
    service_record_service.delete_service(service_id)
    flash("Service record deleted.", "info")
    return redirect(url_for('services_list'))

# ----------------- ANALYTICS & DASHBOARD -----------------
@app.route('/analytics')
@login_required
def analytics():
    kpis = analytics_service.get_dashboard_kpis()
    monthly_trends = analytics_service.get_monthly_cost_trends()
    service_types = analytics_service.get_service_type_breakdown()
    top_parts = analytics_service.get_top_parts_replaced(8)
    risk_dist = analytics_service.get_risk_distribution()
    age_analysis = analytics_service.get_age_group_cost_analysis()

    return render_template(
        'analytics/dashboard.html',
        kpis=kpis,
        monthly_trends=monthly_trends,
        service_types=service_types,
        top_parts=top_parts,
        risk_dist=risk_dist,
        age_analysis=age_analysis
    )

@app.route('/api/analytics/charts')
@login_required
def api_charts():
    monthly = analytics_service.get_monthly_cost_trends()
    risk = analytics_service.get_risk_distribution()
    types = analytics_service.get_service_type_breakdown()
    return jsonify({
        'monthly': monthly,
        'risk': risk,
        'service_types': types
    })

# ----------------- RISK PREDICTION -----------------
@app.route('/predict', methods=['GET', 'POST'])
@login_required
def predict():
    vehicles = vehicle_service.get_all_vehicles()
    prediction_result = None

    if request.method == 'POST':
        mode = request.form.get('prediction_mode', 'manual')

        if mode == 'existing_vehicle':
            vehicle_id = int(request.form.get('vehicle_id'))
            prediction_result = prediction_service.run_prediction_for_vehicle(vehicle_id)
            selected_v = vehicle_service.get_vehicle_by_id(vehicle_id)
            if prediction_result:
                prediction_result['vehicle_info'] = f"{selected_v['make']} {selected_v['model']} ({selected_v['registration_no']})"
            flash("Prediction calculated and saved to database.", "success")
        else:
            # Manual feature input
            age = float(request.form.get('vehicle_age_years', 5))
            mileage = float(request.form.get('mileage_km', 60000))
            days_since = float(request.form.get('days_since_last_service', 120))
            freq = float(request.form.get('service_frequency_per_year', 1.5))
            avg_cost = float(request.form.get('avg_service_cost', 150))
            major_repairs = int(request.form.get('major_repairs_count', 0))
            breakdown_hist = int(request.form.get('breakdown_history_count', 0))
            fuel_type = request.form.get('fuel_type', 'Petrol')

            prediction_result = prediction_service.predict_risk(
                vehicle_age_years=age,
                mileage_km=mileage,
                days_since_last_service=days_since,
                service_frequency_per_year=freq,
                avg_service_cost=avg_cost,
                major_repairs_count=major_repairs,
                breakdown_history_count=breakdown_hist,
                fuel_type=fuel_type
            )
            prediction_result['vehicle_info'] = f"Custom Vehicle Profile ({fuel_type}, {int(age)} yrs, {int(mileage):,} km)"

    return render_template('predictions/predict.html', vehicles=vehicles, result=prediction_result)

@app.route('/predict/batch', methods=['POST'])
@login_required
def predict_batch():
    """Runs automated batch prediction across all registered vehicles."""
    vehicles = vehicle_service.get_all_vehicles()
    count = 0
    for v in vehicles:
        prediction_service.run_prediction_for_vehicle(v['vehicle_id'])
        count += 1

    flash(f"Successfully executed ML risk prediction for all {count} registered vehicles.", "success")
    return redirect(url_for('predictions_history'))

@app.route('/predictions/history')
@login_required
def predictions_history():
    history = prediction_service.get_prediction_history(limit=100)
    return render_template('predictions/history.html', history=history)

# ----------------- REPORTS & EXPORTS -----------------
@app.route('/reports')
@login_required
def reports():
    kpis = analytics_service.get_dashboard_kpis()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT v.registration_no, v.make, v.model, c.name as customer_name, c.phone,
               p.risk_score, p.risk_level, p.service_due, p.predicted_at, p.key_factors
        FROM predictions p
        JOIN vehicles v ON p.vehicle_id = v.vehicle_id
        JOIN customers c ON v.customer_id = c.customer_id
        WHERE p.risk_level = 'High'
        ORDER BY p.risk_score DESC
    """)
    high_risk_list = [dict(r) for r in cursor.fetchall()]
    conn.close()

    return render_template('reports/index.html', kpis=kpis, high_risk_list=high_risk_list)

@app.route('/reports/export/services')
@login_required
def export_services_csv():
    services = service_record_service.get_all_services()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Service ID', 'Registration No', 'Vehicle', 'Customer', 'Date', 'Type', 'Mileage', 'Labour Cost', 'Parts Cost', 'Total Cost', 'Status', 'Notes'])

    for s in services:
        writer.writerow([
            s['service_id'], s['registration_no'], f"{s['make']} {s['model']}",
            s['customer_name'], s['service_date'], s['service_type'],
            s['mileage'], s['labour_cost'], s['parts_cost'], s['total_cost'],
            s['status'], s['notes'] or ''
        ])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=vehicle_services_report.csv"}
    )

@app.route('/reports/export/predictions')
@login_required
def export_predictions_csv():
    history = prediction_service.get_prediction_history(500)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Prediction ID', 'Registration No', 'Vehicle', 'Customer', 'Mileage', 'Risk Score', 'Risk Level', 'Breakdown Predicted', 'Service Due', 'Key Factors', 'Timestamp'])

    for p in history:
        writer.writerow([
            p['prediction_id'], p['registration_no'], f"{p['make']} {p['model']}",
            p['customer_name'], p['mileage'], p['risk_score'], p['risk_level'],
            'Yes' if p['breakdown_predicted'] else 'No',
            'Yes' if p['service_due'] else 'No',
            p['key_factors'] or '', p['predicted_at']
        ])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=breakdown_risk_predictions.csv"}
    )

# ----------------- MODEL EVALUATION & VIVA GUIDE -----------------
@app.route('/model-info')
@login_required
def model_info():
    metrics_path = os.path.join(Config.ML_MODEL_DIR, 'model_metrics.json')
    metrics = None
    if os.path.exists(metrics_path):
        try:
            with open(metrics_path, 'r', encoding='utf-8') as f:
                metrics = json.load(f)
        except Exception:
            metrics = None

    return render_template('model_info.html', metrics=metrics)

# Initialization function
def setup_app():
    init_db()
    seed_database()

if __name__ == '__main__':
    setup_app()
    app.run(debug=True, host='127.0.0.1', port=5000)
