from flask import session
from flask_socketio import emit, join_room, leave_room
from app import socketio
from app.models import User, Group, ChatMessage
from app.utils import get_current_user
from datetime import datetime

@socketio.on('join_group')
def handle_join_group(data):
    """Handle client joining a group's SocketIO room"""
    group_id = data.get('group_id')
    
    if not group_id:
        emit('error', {'message': 'Group ID is required'})
        return
    
    user = get_current_user()
    if not user:
        emit('error', {'message': 'Authentication required'})
        return
    
    group = Group.objects(group_id=group_id).first()
    if not group:
        emit('error', {'message': 'Group not found'})
        return
    
    if user not in group.members:
        emit('error', {'message': 'You are not a member of this group'})
        return
    
    room = f'group_{group_id}'
    join_room(room)
    emit('joined_group', {'group_id': group_id, 'message': f'Joined group {group.name}'})

@socketio.on('leave_group')
def handle_leave_group(data):
    """Handle client leaving a group's SocketIO room"""
    group_id = data.get('group_id')
    
    if not group_id:
        emit('error', {'message': 'Group ID is required'})
        return
    
    room = f'group_{group_id}'
    leave_room(room)
    emit('left_group', {'group_id': group_id, 'message': 'Left group'})

@socketio.on('send_message')
def handle_send_message(data):
    """Handle client sending a chat message"""
    group_id = data.get('group_id')
    message_text = data.get('message', '').strip()
    
    if not group_id:
        emit('error', {'message': 'Group ID is required'})
        return
    
    if not message_text:
        emit('error', {'message': 'Message cannot be empty'})
        return
    
    user = get_current_user()
    if not user:
        emit('error', {'message': 'Authentication required'})
        return
    
    group = Group.objects(group_id=group_id).first()
    if not group:
        emit('error', {'message': 'Group not found'})
        return
    
    if user not in group.members:
        emit('error', {'message': 'You are not a member of this group'})
        return
    
    chat_message = ChatMessage(
        group=group,
        user=user,
        message=message_text,
        timestamp=datetime.utcnow()
    )
    chat_message.save()
    
    room = f'group_{group_id}'
    emit('message_received', {
        'message_id': str(chat_message.id),
        'user_id': str(user.id),
        'user_name': f'{user.firstname} {user.lastname}',
        'message': message_text,
        'timestamp': chat_message.timestamp.isoformat()
    }, room=room)


