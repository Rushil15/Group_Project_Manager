from mongoengine import Document, StringField, ListField, ReferenceField, DateTimeField
from datetime import datetime
import bcrypt

class User(Document):
    firstname = StringField(required=True, max_length=100)
    lastname = StringField(required=True, max_length=100)
    email = StringField(required=True, unique=True, max_length=255)
    password_hash = StringField(required=True)
    groups = ListField(ReferenceField('Group'))
    invite = ListField(StringField())  # List of group_ids for pending invites
    
    meta = {
        'collection': 'users',
        'indexes': ['email']
    }
    
    def set_password(self, password):
        """Hash and set the password"""
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def check_password(self, password):
        """Verify the password"""
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    def __str__(self):
        return f"{self.firstname} {self.lastname} ({self.email})"


class Group(Document):
    name = StringField(required=True, max_length=200)
    description = StringField()
    members = ListField(ReferenceField('User'), required=True)
    created_by = ReferenceField('User', required=True)
    created_at = DateTimeField(required=True, default=datetime.utcnow)
    group_id = StringField(required=True, unique=True)
    
    meta = {
        'collection': 'groups',
        'indexes': ['group_id']
    }
    
    def __str__(self):
        return f"{self.name} ({self.group_id})"


class Task(Document):
    title = StringField(required=True, max_length=200)
    description = StringField()
    assigned_to = ReferenceField('User', required=True)
    group = ReferenceField('Group', required=True)
    created_by = ReferenceField('User', required=True)
    created_at = DateTimeField(required=True, default=datetime.utcnow)
    status = StringField(choices=["pending", "in_progress", "completed"], default="pending")
    due_date = DateTimeField()
    
    meta = {
        'collection': 'tasks',
        'indexes': ['group', 'assigned_to']
    }
    
    def __str__(self):
        return f"{self.title} ({self.status})"


class Subtask(Document):
    title = StringField(required=True, max_length=200)
    description = StringField()
    task = ReferenceField('Task', required=True)
    assigned_to = ReferenceField('User', required=True)
    status = StringField(required=True, choices=["not_started", "in_progress", "done"], default="not_started")
    created_at = DateTimeField(required=True, default=datetime.utcnow)
    
    meta = {
        'collection': 'subtasks',
        'indexes': ['task', 'assigned_to']
    }
    
    def __str__(self):
        return f"{self.title} ({self.status})"


class ChatMessage(Document):
    group = ReferenceField('Group', required=True)
    user = ReferenceField('User', required=True)
    message = StringField(required=True)
    timestamp = DateTimeField(required=True, default=datetime.utcnow)
    
    meta = {
        'collection': 'chat_messages',
        'indexes': ['group', 'timestamp']
    }
    
    def __str__(self):
        return f"{self.user.firstname} {self.user.lastname}: {self.message[:50]}"

