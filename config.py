import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'secret key'
    MONGODB_SETTINGS = {
        'db': os.environ.get('MONGODB_DB') or 'group_project_manager',
        'host': os.environ.get('MONGODB_URI') or 'mongodb://localhost:27017/group_project_manager'
    }

