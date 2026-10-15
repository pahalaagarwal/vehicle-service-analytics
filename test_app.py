import unittest
import os
import json
from app import app, setup_app
from db import get_db_connection
from services import (
    auth_service, customer_service, vehicle_service,
    service_record_service, analytics_service, prediction_service
)

class VehicleServiceAnalyticsTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        setup_app()
        cls.client = app.test_client()

    def test_01_database_seeded(self):
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM users")
        self.assertGreaterEqual(c.fetchone()[0], 3)
        c.execute("SELECT COUNT(*) FROM customers")
        self.assertGreaterEqual(c.fetchone()[0], 5)
        c.execute("SELECT COUNT(*) FROM vehicles")
        self.assertGreaterEqual(c.fetchone()[0], 6)
        c.execute("SELECT COUNT(*) FROM services")
        self.assertGreaterEqual(c.fetchone()[0], 10)
        conn.close()

    def test_02_authentication(self):
        # Valid admin credentials
        user = auth_service.authenticate_user('admin', 'admin123')
        self.assertIsNotNone(user)
        self.assertEqual(user['role'], 'admin')

        # Invalid password
        bad_user = auth_service.authenticate_user('admin', 'wrongpass')
        self.assertIsNone(bad_user)

    def test_03_customer_crud(self):
        cid = customer_service.create_customer("Test User", "+1-999-8888", "test@test.com", "Test City")
        self.assertIsInstance(cid, int)
        cust = customer_service.get_customer_by_id(cid)
        self.assertEqual(cust['name'], "Test User")

        customer_service.update_customer(cid, "Test User Updated", "+1-999-8888", "test@test.com", "New City")
        cust_up = customer_service.get_customer_by_id(cid)
        self.assertEqual(cust_up['name'], "Test User Updated")

        customer_service.delete_customer(cid)
        self.assertIsNone(customer_service.get_customer_by_id(cid))

    def test_04_vehicle_service_and_parts(self):
        # Fetch first customer
        customers = customer_service.get_all_customers()
        self.assertTrue(len(customers) > 0)
        cid = customers[0]['customer_id']

        # Create vehicle
        vid = vehicle_service.create_vehicle(cid, "TEST-99-ZZ", "Toyota", "Camry", 2018, 75000, "Petrol")
        self.assertIsInstance(vid, int)

        # Create service ticket
        sid = service_record_service.create_service(vid, "2024-09-01", "Routine", 75000, 100.0, "Completed", "Test oil service")
        self.assertIsInstance(sid, int)

        # Attach part
        pid = service_record_service.add_part_to_service(sid, "Test Oil Filter", 1, 25.0)
        self.assertIsInstance(pid, int)

        # Verify service total
        service = service_record_service.get_service_by_id(sid)
        self.assertEqual(service['total_cost'], 125.0)

        # Cleanup
        vehicle_service.delete_vehicle(vid)

    def test_05_analytics_kpis(self):
        kpis = analytics_service.get_dashboard_kpis()
        self.assertIn('total_vehicles', kpis)
        self.assertIn('total_revenue', kpis)
        self.assertGreaterEqual(kpis['total_vehicles'], 5)

        trends = analytics_service.get_monthly_cost_trends()
        self.assertIn('months', trends)

    def test_06_prediction_service(self):
        # Run prediction
        res = prediction_service.predict_risk(
            vehicle_age_years=8,
            mileage_km=120000,
            days_since_last_service=250,
            service_frequency_per_year=1.0,
            avg_service_cost=300,
            major_repairs_count=2,
            breakdown_history_count=1,
            fuel_type="Diesel"
        )
        self.assertIn('risk_score', res)
        self.assertIn('risk_level', res)
        self.assertIn('breakdown_predicted', res)
        self.assertTrue(res['risk_score'] >= 0.0 and res['risk_score'] <= 1.0)

    def test_07_http_routes(self):
        # Login
        response = self.client.post('/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        # Dashboard
        response = self.client.get('/dashboard')
        self.assertEqual(response.status_code, 200)

        # Customers list
        response = self.client.get('/customers')
        self.assertEqual(response.status_code, 200)

        # Vehicles list
        response = self.client.get('/vehicles')
        self.assertEqual(response.status_code, 200)

        # Services list
        response = self.client.get('/services')
        self.assertEqual(response.status_code, 200)

        # Analytics page
        response = self.client.get('/analytics')
        self.assertEqual(response.status_code, 200)

        # Prediction page
        response = self.client.get('/predict')
        self.assertEqual(response.status_code, 200)

        # Reports page
        response = self.client.get('/reports')
        self.assertEqual(response.status_code, 200)

        # Model Info & Viva page
        response = self.client.get('/model-info')
        self.assertEqual(response.status_code, 200)

        # CSV export endpoints
        resp_csv1 = self.client.get('/reports/export/services')
        self.assertEqual(resp_csv1.status_code, 200)
        self.assertIn(b'Service ID', resp_csv1.data)

        resp_csv2 = self.client.get('/reports/export/predictions')
        self.assertEqual(resp_csv2.status_code, 200)
        self.assertIn(b'Prediction ID', resp_csv2.data)

if __name__ == '__main__':
    unittest.main()
