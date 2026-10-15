import os
import random
import csv
import math

def generate_dataset(num_records=1200, output_path=None):
    if output_path is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_path = os.path.join(base_dir, 'dataset', 'vehicle_service_data.csv')

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    random.seed(42)

    makes_models = {
        'Toyota': ['Corolla', 'Camry', 'Innova', 'Fortuner', 'Yaris'],
        'Honda': ['Civic', 'City', 'Accord', 'CR-V', 'Jazz'],
        'Ford': ['EcoSport', 'Focus', 'Endeavour', 'Mustang', 'Figo'],
        'Hyundai': ['Creta', 'i20', 'Verna', 'Tucson', 'Venue'],
        'Volkswagen': ['Polo', 'Vento', 'Taigun', 'Tiguan', 'Passat'],
        'Maruti': ['Swift', 'Baleno', 'Brezza', 'Dzire', 'Ertiga']
    }

    fuel_types = ['Petrol', 'Diesel', 'Hybrid', 'Electric']

    headers = [
        'vehicle_id', 'make', 'model', 'vehicle_age_years', 'mileage_km',
        'days_since_last_service', 'service_frequency_per_year', 'avg_service_cost',
        'major_repairs_count', 'fuel_type', 'breakdown_history_count',
        'service_due', 'breakdown_risk', 'risk_score'
    ]

    records = []

    for i in range(1, num_records + 1):
        make = random.choice(list(makes_models.keys()))
        model = random.choice(makes_models[make])
        age = random.randint(1, 15)
        # Mileage roughly correlated with age
        mileage = int(max(5000, age * random.uniform(8000, 20000) + random.uniform(-5000, 10000)))
        days_since_last_service = random.randint(15, 550)
        fuel = random.choices(fuel_types, weights=[0.50, 0.35, 0.10, 0.05])[0]

        # Service frequency per year
        service_freq = round(random.uniform(0.5, 3.5), 1)

        # Major repairs count
        major_repairs = random.randint(0, min(5, math.floor(age / 2)))

        # Breakdown history count
        breakdown_history = random.randint(0, min(4, major_repairs + 1))

        # Average service cost
        base_cost = 100 if fuel == 'Petrol' else (140 if fuel == 'Diesel' else 90)
        avg_cost = round(base_cost + (age * 25) + (major_repairs * 90) + random.uniform(-30, 80), 2)
        avg_cost = max(60.0, avg_cost)

        # Service due logic: typically vehicle due if >180 days or very high mileage interval
        service_due = 1 if (days_since_last_service >= 180 or random.random() < 0.15) else 0

        # Calculate breakdown risk score with realistic non-linear formula
        # Factors: high age, high mileage, long service neglect, diesel engine wear, prior breakdown history
        score = 0.05
        score += (age / 15.0) * 0.25
        score += (min(mileage, 200000) / 200000.0) * 0.25
        score += (min(days_since_last_service, 400) / 400.0) * 0.25
        score += (breakdown_history / 4.0) * 0.15
        score += (major_repairs / 5.0) * 0.10
        if fuel == 'Diesel':
            score += 0.05
        if service_freq < 1.0:
            score += 0.08

        # Add small random noise
        score += random.uniform(-0.08, 0.08)
        score = max(0.02, min(0.98, round(score, 3)))

        # Binary breakdown risk classification (1 if score >= 0.50)
        breakdown_risk = 1 if score >= 0.50 else 0

        records.append([
            i, make, model, age, mileage, days_since_last_service,
            service_freq, avg_cost, major_repairs, fuel, breakdown_history,
            service_due, breakdown_risk, score
        ])

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(records)

    print(f"Generated {num_records} vehicle service records at: {output_path}")
    return output_path

if __name__ == '__main__':
    generate_dataset()
