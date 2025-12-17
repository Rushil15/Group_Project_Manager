from flask import Blueprint

tasks_bp = Blueprint('tasks', __name__, url_prefix='')

from app.tasks import routes

