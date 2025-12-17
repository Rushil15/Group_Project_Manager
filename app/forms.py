from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, EmailField, TextAreaField, SelectField, DateField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Optional
from app.models import User

class LoginForm(FlaskForm):
    email = EmailField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])

class SignUpForm(FlaskForm):
    firstname = StringField('First Name', validators=[DataRequired()])
    lastname = StringField('Last Name', validators=[DataRequired()])
    email = EmailField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password', message='Passwords must match')])
    
    def validate_email(self, email):
        """Check if email already exists"""
        user = User.objects(email=email.data).first()
        if user:
            raise ValidationError('This email is already registered. Please use a different email or log in.')

class CreateGroupForm(FlaskForm):
    name = StringField('Group Name', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[Optional()])
    member_selection = EmailField('Invite Member (Email)', validators=[Optional(), Email()])

class AssignTaskForm(FlaskForm):
    title = StringField('Task Title', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[Optional()])
    assign_to = SelectField('Assign To', coerce=str, validators=[DataRequired()])
    due_date = DateField('Due Date', validators=[Optional()], format='%Y-%m-%d')

class CreateSubtaskForm(FlaskForm):
    title = StringField('Subtask Title', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[Optional()])

