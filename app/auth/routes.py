from flask import render_template, redirect, url_for, flash, session, request
from app.auth import auth_bp
from app.forms import LoginForm, SignUpForm
from app.models import User, Group, Task, Subtask
from app.utils import login_required, get_current_user

@auth_bp.route('/')
def index():
    """Root route - redirect based on authentication status"""
    if 'user_id' in session:
        return redirect(url_for('auth.dashboard'))
    return redirect(url_for('auth.login'))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login route"""
    if 'user_id' in session:
        return redirect(url_for('auth.dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.objects(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            session['user_id'] = str(user.id)
            flash('Login successful!', 'success')
            return redirect(url_for('auth.dashboard'))
        else:
            flash('Invalid email or password.', 'error')
    
    return render_template('auth/login.html', form=form)

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    """Signup route"""
    if 'user_id' in session:
        return redirect(url_for('auth.dashboard'))
    
    form = SignUpForm()
    if form.validate_on_submit():
        user = User(
            firstname=form.firstname.data,
            lastname=form.lastname.data,
            email=form.email.data
        )
        user.set_password(form.password.data)
        user.save()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/signup.html', form=form)

@auth_bp.route('/logout')
def logout():
    """Logout route"""
    session.pop('user_id', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard route - displays groups and progress tracking"""
    user = get_current_user()
    
    groups = Group.objects(members=user)
    
    progress_data = []
    
    for group in groups:
        tasks = Task.objects(group=group)
        
        for task in tasks:
            groupmate = task.assigned_to
            
            subtasks = Subtask.objects(task=task, assigned_to=groupmate)
            
            if task.status == "completed" and subtasks.count() > 0:
                all_done = all(subtask.status == 'done' for subtask in subtasks)
                if not all_done:
                    task.status = 'in_progress'
                    task.save()
                    from app.utils import emit_task_status_update
                    emit_task_status_update(str(task.group.group_id), str(task.id))
            
            if task.status == "completed":
                progress = 100.0
            else:
                total_subtasks = len(subtasks)
                
                if total_subtasks == 0:
                    progress = 0.0
                else:
                    completed_subtasks = sum(1 for st in subtasks if st.status == "done")
                    progress = (completed_subtasks / total_subtasks) * 100.0
            
            progress_data.append({
                'group': group,
                'groupmate': groupmate,
                'task': task,
                'progress': round(progress, 1)
            })
    
    return render_template('dashboard.html', user=user, groups=groups, progress_data=progress_data)

