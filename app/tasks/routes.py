from flask import render_template, redirect, url_for, flash, request, jsonify
from app.tasks import tasks_bp
from app.forms import AssignTaskForm, CreateSubtaskForm
from app.models import User, Group, Task, Subtask
from app.utils import login_required, get_current_user, emit_progress_update, emit_task_status_update

@tasks_bp.route('/assign_task/<group_id>', methods=['GET', 'POST'])
@login_required
def assign_task(group_id):
    """Create and assign a task to a group member"""
    user = get_current_user()

    group = Group.objects(group_id=group_id).first()
    if not group:
        flash('Group not found.', 'error')
        return redirect(url_for('groups.groups_list'))
    
    if user not in group.members:
        flash('You do not have access to this group.', 'error')
        return redirect(url_for('groups.groups_list'))
    
    form = AssignTaskForm()
    
    form.assign_to.choices = [(str(member.id), f'{member.firstname} {member.lastname}') for member in group.members]
    
    if form.validate_on_submit():
        assigned_user = User.objects(id=form.assign_to.data).first()
        if not assigned_user:
            flash('Selected user not found.', 'error')
            return render_template('tasks/assign_task.html', form=form, group=group)
        
        # Create task
        task = Task(
            title=form.title.data,
            description=form.description.data if form.description.data else "",
            assigned_to=assigned_user,
            group=group,
            created_by=user,
            due_date=form.due_date.data if form.due_date.data else None
        )
        task.save()
        
        flash(f'Task "{task.title}" assigned to {assigned_user.firstname} {assigned_user.lastname} successfully!', 'success')
        return redirect(url_for('tasks.task_detail', task_id=str(task.id)))
    
    return render_template('tasks/assign_task.html', form=form, group=group)

@tasks_bp.route('/task/<task_id>')
@login_required
def task_detail(task_id):
    """Display task detail page with subtasks"""
    user = get_current_user()

    task = Task.objects(id=task_id).first()
    if not task:
        flash('Task not found.', 'error')
        return redirect(url_for('groups.groups_list'))
    
    if user not in task.group.members:
        flash('You do not have access to this task.', 'error')
        return redirect(url_for('groups.groups_list'))
    
    subtasks = Subtask.objects(task=task).order_by('-created_at')
    
    if task.status == 'completed' and subtasks.count() > 0:
        all_done = all(subtask.status == 'done' for subtask in subtasks)
        if not all_done:
            task.status = 'in_progress'
            task.save()
            emit_task_status_update(str(task.group.group_id), str(task.id))
    
    is_assignee = (task.assigned_to.id == user.id)
    
    return render_template('tasks/task_detail.html', 
                         user=user,
                         task=task, 
                         subtasks=subtasks,
                         is_assignee=is_assignee)

@tasks_bp.route('/create_subtask/<task_id>', methods=['GET', 'POST'])
@login_required
def create_subtask(task_id):
    """Create a subtask for a task (only accessible by task assignee)"""
    user = get_current_user()

    task = Task.objects(id=task_id).first()
    if not task:
        flash('Task not found.', 'error')
        return redirect(url_for('groups.groups_list'))
    
    if user not in task.group.members:
        flash('You do not have access to this task.', 'error')
        return redirect(url_for('groups.groups_list'))
    
    if task.assigned_to.id != user.id:
        flash('Only the task assignee can create subtasks for this task.', 'error')
        return redirect(url_for('tasks.task_detail', task_id=task_id))
    
    form = CreateSubtaskForm()
    
    if form.validate_on_submit():
        subtask = Subtask(
            title=form.title.data,
            description=form.description.data if form.description.data else "",
            task=task,
            assigned_to=task.assigned_to,
        )
        subtask.save()
        
        task = Task.objects(id=task_id).first()
        
        all_subtasks = Subtask.objects(task=task)
        all_done = False
        all_not_started = False
        has_in_progress = False
        
        if all_subtasks.count() > 0:
            all_done = all(all_subtask.status == 'done' for all_subtask in all_subtasks)
            all_not_started = all(all_subtask.status == 'not_started' for all_subtask in all_subtasks)
            has_in_progress = any(all_subtask.status == 'in_progress' for all_subtask in all_subtasks)
        
        if all_done:
            task.status = 'completed'
        elif all_not_started:
            task.status = 'pending'
        elif has_in_progress:
            task.status = 'in_progress'
        else:
            task.status = 'in_progress'
        
        task.save()
        emit_task_status_update(str(task.group.group_id), str(task.id))
        emit_progress_update(str(task.group.group_id), str(task.id))
        
        flash(f'Subtask "{subtask.title}" created successfully!', 'success')
        return redirect(url_for('tasks.task_detail', task_id=task_id))
    
    return render_template('tasks/create_subtask.html', form=form, task=task)

@tasks_bp.route('/subtask/<subtask_id>/update_status', methods=['POST'])
@login_required
def update_subtask_status(subtask_id):
    """Update subtask status"""
    user = get_current_user()
    
    subtask = Subtask.objects(id=subtask_id).first()
    if not subtask:
        return jsonify({'error': 'Subtask not found'}), 404
    
    if user not in subtask.task.group.members:
        return jsonify({'error': 'You do not have access to this subtask'}), 403
    
    if subtask.task.assigned_to.id != user.id:
        return jsonify({'error': 'Only the task assignee can update subtask status'}), 403
    
    new_status = request.json.get('status')
    if new_status not in ['not_started', 'in_progress', 'done']:
        return jsonify({'error': 'Invalid status'}), 400
    
    subtask.status = new_status
    subtask.save()
    
    task = Task.objects(id=subtask.task.id).first()
    task_status_changed = False
    
    all_subtasks = Subtask.objects(task=task)
    all_done = False
    all_not_started = False
    has_in_progress = False
    
    if all_subtasks.count() > 0:
        all_done = all(all_subtask.status == 'done' for all_subtask in all_subtasks)
        all_not_started = all(all_subtask.status == 'not_started' for all_subtask in all_subtasks)
        has_in_progress = any(all_subtask.status == 'in_progress' for all_subtask in all_subtasks)
    
    if all_done:
        if task.status != 'completed':
            task.status = 'completed'
            task.save()
            task_status_changed = True
            emit_task_status_update(str(task.group.group_id), str(task.id))
    elif all_not_started:
        if task.status != 'pending':
            task.status = 'pending'
            task.save()
            task_status_changed = True
            emit_task_status_update(str(task.group.group_id), str(task.id))
    elif has_in_progress:
        if task.status != 'in_progress':
            task.status = 'in_progress'
            task.save()
            task_status_changed = True
            emit_task_status_update(str(task.group.group_id), str(task.id))
    else:
        if task.status == 'completed':
            task.status = 'in_progress'
            task.save()
            task_status_changed = True
            emit_task_status_update(str(task.group.group_id), str(task.id))
        elif task.status == 'pending':
            task.status = 'in_progress'
            task.save()
            task_status_changed = True
            emit_task_status_update(str(task.group.group_id), str(task.id))
    
    emit_progress_update(str(task.group.group_id), str(task.id))
    
    return jsonify({
        'success': True,
        'subtask_id': str(subtask.id),
        'status': subtask.status,
        'task_completed': all_done,
        'task_status': task.status,
        'task_status_changed': task_status_changed
    })

@tasks_bp.route('/task/<task_id>/complete', methods=['POST'])
@login_required
def complete_task(task_id):
    """Mark task as completed and update all subtasks to 'done' (only accessible by task assignee)"""
    user = get_current_user()
    
    task = Task.objects(id=task_id).first()
    if not task:
        flash('Task not found.', 'error')
        return redirect(url_for('groups.groups_list'))
    
    if user not in task.group.members:
        flash('You do not have access to this task.', 'error')
        return redirect(url_for('groups.groups_list'))
    
    if task.assigned_to.id != user.id:
        flash('Only the task assignee can complete this task.', 'error')
        return redirect(url_for('tasks.task_detail', task_id=task_id))
    
    task.status = 'completed'
    task.save()
    
    subtasks = Subtask.objects(task=task)
    for subtask in subtasks:
        if subtask.status != 'done':
            subtask.status = 'done'
            subtask.save()
    
    emit_task_status_update(str(task.group.group_id), str(task.id))
    emit_progress_update(str(task.group.group_id), str(task.id))
    
    flash(f'Task "{task.title}" marked as completed! All subtasks have been marked as done.', 'success')
    return redirect(url_for('tasks.task_detail', task_id=task_id))

