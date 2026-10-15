import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'vehicle-service-analytics-secret-key-2026')
    DATABASE_PATH = os.path.join(BASE_DIR, 'vehicle_service.db')
    DATASET_PATH = os.path.join(BASE_DIR, 'dataset', 'vehicle_service_data.csv')
    ML_MODEL_DIR = os.path.join(BASE_DIR, 'ml', 'saved_models')
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload
    ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls', 'png', 'jpg', 'jpeg'}
