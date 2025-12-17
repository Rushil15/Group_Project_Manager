from functools import wraps
from flask import session, redirect, url_for
from app.models import User


def get_socketio():
    from app import socketio
    return socketio


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def get_current_user():
    if 'user_id' not in session:
        return None
    try:
        return User.objects(id=session['user_id']).first()
    except:  
        return None


def emit_progress_update(group_id, task_id=None):
    socketio = get_socketio()
    socketio.emit(
        'subtask_status_changed',
        {'group_id': str(group_id), 'task_id': str(task_id) if task_id else None},
        room=f'group_{group_id}',
    )
    socketio.emit(
        'subtask_status_changed',
        {'group_id': str(group_id), 'task_id': str(task_id) if task_id else None},
    )


def emit_task_status_update(group_id, task_id):
    socketio = get_socketio()
    socketio.emit(
        'task_status_changed',
        {'group_id': str(group_id), 'task_id': str(task_id)},
        room=f'group_{group_id}',
    )
    socketio.emit(
        'task_status_changed',
        {'group_id': str(group_id), 'task_id': str(task_id)},
    )

