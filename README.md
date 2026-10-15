# Vehicle Service Analytics & Breakdown Risk Prediction

A production-ready academic web application designed for comprehensive automotive service management, workshop analytics, and machine learning-driven vehicle breakdown risk prediction.

---

## 📌 1. Project Overview
Modern automotive workshops frequently face challenges with reactive repairs, unscheduled downtime, and paper-based record keeping. This application provides:
- **Centralized Service Management:** Complete relational tracking of customers, vehicles, service tickets, and itemized replacement parts.
- **Descriptive & Diagnostic Analytics:** Interactive dashboards displaying workshop revenue trends, service categories, parts wear frequency, and vehicle age-cost escalation.
- **Machine Learning Breakdown Prediction:** Trained supervised classification model predicting breakdown probability (Low/Medium/High risk) and service urgency based on vehicle telemetry, mileage, and service history.
- **Audit Logging & Reporting:** Persistent prediction logs, high-risk fleet alerts, and one-click CSV report exports.

---

## 🛠️ 2. Technology Stack & Architecture

- **Backend:** Python (Flask), Werkzeug (Security & Password Hashing), Jinja2 Templating
- **Database:** SQLite (default for zero-configuration local deployment) / easily configurable for MySQL
- **Frontend:** HTML5, CSS3, JavaScript (ES6), Bootstrap 5, Bootstrap Icons, Chart.js (Interactive visual charts)
- **Data Science & ML:** Pandas, NumPy, Scikit-learn (Logistic Regression & Random Forest Classifier), Matplotlib, Joblib
- **Architecture Pattern:** Multi-tier separation of concerns:
  - **Presentation Layer:** Jinja2 templates, Bootstrap responsive cards, Chart.js canvas elements
  - **Controller / Routing Layer:** Flask routes (`app.py`), session handling, RBAC decorators
  - **Service & Business Logic Layer:** `services/` (`auth_service`, `customer_service`, `vehicle_service`, `service_record_service`, `analytics_service`, `prediction_service`)
  - **Persistence Layer:** Normalized relational database (`db.py`, `vehicle_service.db`)
  - **Predictive AI Layer:** Scikit-learn serialized pipelines (`ml/saved_models/breakdown_risk_model.joblib`)

---

## 🗄️ 3. Relational Database Design

The schema follows Third Normal Form (3NF) with primary and foreign key constraints:

| Table Name | Primary Key | Foreign Keys | Key Attributes & Description |
|---|---|---|---|
| `users` | `user_id` | — | `username` (UNIQUE), `email`, `password_hash`, `role` (`admin`, `service_advisor`, `customer`), `created_at` |
| `customers` | `customer_id` | — | `name`, `phone`, `email`, `address`, `created_at` |
| `vehicles` | `vehicle_id` | `customer_id` | `registration_no` (UNIQUE), `make`, `model`, `year`, `mileage`, `fuel_type`, `last_service_date`, `created_at` |
| `services` | `service_id` | `vehicle_id` | `service_date`, `service_type` (Routine, Major Repair, Emergency Breakdown, Inspection), `mileage`, `labour_cost`, `status`, `notes` |
| `parts` | `part_id` | `service_id` | `part_name`, `quantity`, `cost`, `created_at` |
| `predictions` | `prediction_id` | `vehicle_id` | `risk_score` (0.0–1.0), `risk_level` (Low, Medium, High), `breakdown_predicted` (0/1), `service_due` (0/1), `key_factors`, `predicted_at` |

---

## 🤖 4. Machine Learning & Predictive Analytics

### Feature Set
1. `vehicle_age_years`: Elapsed age of vehicle
2. `mileage_km`: Cumulative odometer distance
3. `days_since_last_service`: Elapsed time since previous maintenance
4. `service_frequency_per_year`: Number of services logged per active year
5. `avg_service_cost`: Historical workshop expenditure
6. `major_repairs_count`: Number of past major engine/transmission repairs
7. `breakdown_history_count`: Prior roadside breakdowns
8. `fuel_type`: One-Hot Encoded (Petrol, Diesel, Hybrid, Electric)

### Candidate Model Comparison
Two supervised classification pipelines were trained on an 80/20 stratified split:
- **Logistic Regression:** Linear decision boundary with probabilistic sigmoid output.
- **Random Forest Classifier:** 100 decision trees modeling non-linear interactions.

Both models achieve >91% accuracy and >0.93 F1-score. Evaluation curves and confusion matrix are saved to `static/img/model_evaluation.png`.

---

## 📁 5. Directory Structure

```
vehicle_service_analytics/
│── app.py                   # Main Flask application and HTTP route handlers
│── config.py                # Centralized app configuration and file paths
│── db.py                    # Database schema creation and initial seeding
│── requirements.txt         # Python package dependencies
│── test_app.py              # Automated unit and integration test suite
│── README.md                # Project documentation and setup guide
│
├── dataset/
│   └── vehicle_service_data.csv   # 1,200 synthetic vehicle service records
│
├── ml/
│   ├── generate_dataset.py        # Generates realistic synthetic dataset
│   ├── train_model.py             # Model training, comparison, and evaluation pipeline
│   └── saved_models/
│       ├── breakdown_risk_model.joblib  # Serialized Scikit-learn pipeline
│       └── model_metrics.json          # Metrics summary (Accuracy, F1, ROC-AUC)
│
├── services/
│   ├── __init__.py
│   ├── auth_service.py            # User authentication and password hashing
│   ├── customer_service.py        # Customer CRUD operations
│   ├── vehicle_service.py         # Vehicle registration and fleet lookups
│   ├── service_record_service.py  # Service tickets and replacement parts management
│   ├── analytics_service.py       # Descriptive and diagnostic metrics
│   └── prediction_service.py      # Real-time ML inference and risk scoring
│
├── templates/
│   ├── base.html                  # Master layout with responsive navbar and footer
│   ├── dashboard.html             # Executive KPI cards and interactive charts
│   ├── model_info.html            # ML metrics table, confusion matrix, and Viva guide
│   ├── auth/                      # Login and registration templates
│   ├── customers/                 # Customer directory, form, and view templates
│   ├── vehicles/                  # Vehicle fleet, form, and 360-degree telemetry view
│   ├── services/                  # Service tickets, booking form, and invoice view
│   ├── analytics/                 # Dedicated descriptive/diagnostic analytics dashboard
│   ├── predictions/               # Risk prediction simulator and audit history
│   └── reports/                   # Management reports and CSV export hub
│
└── static/
    ├── css/custom.css             # Custom stylesheets
    ├── js/main.js                 # Client-side scripts
    └── img/
        └── model_evaluation.png   # Generated model comparison and confusion matrix
```

---

## 🚀 6. Step-by-Step Local Setup Instructions

### Prerequisites
- Python 3.9 or higher (tested on Python 3.10, 3.11, 3.12, 3.13, 3.14)
- Web browser (Chrome, Edge, Firefox, Safari)

### Step 1: Extract or Navigate to the Project Directory
```bash
cd vehicle_service_analytics
```

### Step 2: (Optional but Recommended) Create a Virtual Environment
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Required Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Initialize and Seed Database & Train ML Model
The project comes pre-seeded and pre-trained, but you can re-run at any time:
```bash
python db.py
python ml/train_model.py
```

### Step 5: Run Automated Unit Tests (Optional Verification)
```bash
python test_app.py
```

### Step 6: Start the Flask Web Server
```bash
python app.py
```

### Step 7: Open in Your Browser
Visit [http://127.0.0.1:5000](http://127.0.0.1:5000) in your web browser.

---

## 🔑 7. Default Demo Accounts

For instant evaluation and viva demonstration, one-click fill buttons are provided on the login page:

| Role | Username | Password | Access Privileges |
|---|---|---|---|
| **Administrator** | `admin` | `admin123` | Full access: CRUD, delete records, batch prediction, exports |
| **Service Advisor** | `advisor` | `advisor123` | Operational access: Log services, register vehicles, run ML predictions |
| **Customer** | `john_doe` | `customer123` | View personal vehicles, service history, and breakdown alerts |

---

## 🎓 8. Suggested Viva / Demonstration Talking Points

1. **Problem Statement:** Explain the shift from traditional reactive vehicle repairs to predictive fleet health monitoring using machine learning.
2. **Relational Database Design:** Highlight the normalized 3NF schema, foreign keys (`customer_id`, `vehicle_id`, `service_id`), and how deletion cascades preserve data integrity.
3. **Live CRUD Demonstration:** Demonstrate registering a new vehicle, creating a service ticket, and attaching itemized replacement parts.
4. **Dashboard KPIs:** Point out Total Revenue, High Risk Count, and Maintenance Due indicators. Explain how Chart.js renders the monthly labour vs parts trend.
5. **Machine Learning Pipeline:**
   - Explain why the dataset was stratified and how categorical variables (`fuel_type`) were one-hot encoded and numerical variables scaled.
   - Explain why **F1-Score and Recall** are critical: In vehicle breakdown prediction, a false negative is dangerous because an unflagged vehicle may break down on a highway.
6. **Live Prediction:** Go to the Risk Prediction screen, select an older vehicle or enter high mileage (>120,000 km) and long service delay (>200 days), and show how the model flags the risk and generates diagnostic explanations.
7. **Security Measures:** Password hashing using PBKDF2/SHA-256 via Werkzeug, parameterized SQL queries preventing SQL injection, and session validation.
