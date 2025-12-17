from flask import render_template, redirect, url_for, flash, request
from app.groups import groups_bp
from app.forms import CreateGroupForm
from app.models import User, Group, Task, Subtask, ChatMessage
from app.utils import login_required, get_current_user
import uuid

@groups_bp.route('/groups')
@login_required
def groups_list():
    """Display list of all user's groups"""
    user = get_current_user()
    groups = Group.objects(members=user).order_by('-created_at')
    
    return render_template('groups/groups.html', user=user, groups=groups)

@groups_bp.route('/create_group', methods=['GET', 'POST'])
@login_required
def create_group():
    """Create a new group"""
    user = get_current_user()
    form = CreateGroupForm()
    
    if form.validate_on_submit():
        group_id = str(uuid.uuid4())
        
        while Group.objects(group_id=group_id).first():
            group_id = str(uuid.uuid4())
        
        group = Group(
            name=form.name.data,
            description=form.description.data if form.description.data else "",
            members=[user],
            created_by=user,
            group_id=group_id
        )
        group.save()
        
        if user.groups is None:
            user.groups = []
        user.groups.append(group)
        user.save()
        
        if form.member_selection.data:
            invite_email = form.member_selection.data.strip()
            invited_user = User.objects(email=invite_email).first()
            
            if invited_user:
                if invited_user in group.members:
                    flash(f'{invited_user.firstname} {invited_user.lastname} is already a member of this group.', 'info')
                else:
                    if invited_user.invite is None:
                        invited_user.invite = []
                    if group_id not in invited_user.invite:
                        invited_user.invite.append(group_id)
                        invited_user.save()
                        flash(f'Invitation sent to {invited_user.firstname} {invited_user.lastname}.', 'success')
            else:
                flash(f'User with email {invite_email} not found.', 'error')
        
        flash('Group created successfully!', 'success')
        return redirect(url_for('groups.group_detail', group_id=group_id))
    
    return render_template('groups/create_group.html', form=form)

@groups_bp.route('/group/<group_id>')
@login_required
def group_detail(group_id):
    """Display group detail page with members, tasks, subtasks, and chat"""
    user = get_current_user()
    
    group = Group.objects(group_id=group_id).first()
    
    if not group:
        flash('Group not found.', 'error')
        return redirect(url_for('groups.groups_list'))
    
    if user not in group.members:
        flash('You do not have access to this group.', 'error')
        return redirect(url_for('groups.groups_list'))
    
    tasks = Task.objects(group=group).order_by('-created_at')
    
    subtasks = []
    for task in tasks:
        task_subtasks = Subtask.objects(task=task).order_by('-created_at')
        subtasks.extend(task_subtasks)
    
    chat_messages = ChatMessage.objects(group=group).order_by('timestamp').limit(100)
    
    is_creator = (group.created_by.id == user.id)
    
    return render_template('groups/group_detail.html', 
                         user=user, 
                         group=group, 
                         tasks=tasks, 
                         subtasks=subtasks,
                         chat_messages=chat_messages,
                         is_creator=is_creator)

@groups_bp.route('/group/<group_id>/delete', methods=['POST'])
@login_required
def delete_group(group_id):
    """Delete a group"""
    user = get_current_user()
    
    group = Group.objects(group_id=group_id).first()
    
    if not group:
        flash('Group not found.', 'error')
        return redirect(url_for('groups.groups_list'))
    
    if group.created_by.id != user.id:
        flash('You do not have permission to delete this group.', 'error')
        return redirect(url_for('groups.group_detail', group_id=group_id))
    
    members = list(group.members)
    
    tasks = Task.objects(group=group)
    for task in tasks:
        Subtask.objects(task=task).delete()
    tasks.delete()
    
    ChatMessage.objects(group=group).delete()
    
    for member in members:
        if member.groups and group in member.groups:
            member.groups.remove(group)
            member.save()
    
    all_users = User.objects()
    for u in all_users:
        if u.invite and group_id in u.invite:
            u.invite.remove(group_id)
            u.save()
    
    group.delete()
    
    flash('Group deleted successfully.', 'success')
    return redirect(url_for('groups.groups_list'))

@groups_bp.route('/group/<group_id>/invite', methods=['POST'])
@login_required
def invite_member(group_id):
    """Invite a user to the group"""
    user = get_current_user()
    
    group = Group.objects(group_id=group_id).first()
    
    if not group:
        flash('Group not found.', 'error')
        return redirect(url_for('groups.groups_list'))
    
    if user not in group.members:
        flash('You do not have access to this group.', 'error')
        return redirect(url_for('groups.groups_list'))
    
    invite_email = request.form.get('email', '').strip()
    
    if not invite_email:
        flash('Please provide an email address.', 'error')
        return redirect(url_for('groups.group_detail', group_id=group_id))
    
    invited_user = User.objects(email=invite_email).first()
    
    if not invited_user:
        flash(f'User with email {invite_email} not found.', 'error')
        return redirect(url_for('groups.group_detail', group_id=group_id))
    
    if invited_user in group.members:
        flash(f'{invited_user.firstname} {invited_user.lastname} is already a member of this group.', 'info')
        return redirect(url_for('groups.group_detail', group_id=group_id))
    
    if invited_user.invite is None:
        invited_user.invite = []
    if group_id not in invited_user.invite:
        invited_user.invite.append(group_id)
        invited_user.save()
        flash(f'Invitation sent to {invited_user.firstname} {invited_user.lastname}.', 'success')
    else:
        flash(f'{invited_user.firstname} {invited_user.lastname} already has a pending invitation.', 'info')
    
    return redirect(url_for('groups.group_detail', group_id=group_id))

@groups_bp.route('/inbox', methods=['GET', 'POST'])
@login_required
def inbox():
    """Display and handle group invitations"""
    user = get_current_user()
    
    if request.method == 'POST':
        action = request.form.get('action')
        group_id = request.form.get('group_id')
        
        if not group_id:
            flash('Invalid invitation.', 'error')
            return redirect(url_for('groups.inbox'))
        
        group = Group.objects(group_id=group_id).first()
        
        if not group:
            flash('Group not found.', 'error')
            if user.invite and group_id in user.invite:
                user.invite.remove(group_id)
                user.save()
            return redirect(url_for('groups.inbox'))
        
        if not user.invite or group_id not in user.invite:
            flash('This invitation is no longer valid.', 'error')
            return redirect(url_for('groups.inbox'))
        
        if action == 'accept':
            if user not in group.members:
                group.members.append(user)
                group.save()
            
            if user.groups is None:
                user.groups = []
            if group not in user.groups:
                user.groups.append(group)
            
            user.invite.remove(group_id)
            user.save()
            
            flash(f'You have joined {group.name}!', 'success')
            return redirect(url_for('groups.group_detail', group_id=group_id))
        
        elif action == 'reject':
            user.invite.remove(group_id)
            user.save()
            
            flash('Invitation rejected.', 'info')
            return redirect(url_for('groups.inbox'))
    
    pending_invitations = []
    
    if user.invite:
        for group_id in user.invite:
            group = Group.objects(group_id=group_id).first()
            if group:
                pending_invitations.append(group)
    
    return render_template('groups/inbox.html', user=user, invitations=pending_invitations)

