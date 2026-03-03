import csv
import io
from functools import wraps

from flask import Blueprint, render_template, redirect, url_for, request, flash, Response
from flask_login import login_user, logout_user, login_required, current_user

from models import db, AdminUser, Purchase

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin.dashboard'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        user = AdminUser.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('admin.dashboard'))
        flash('Invalid email or password.', 'error')
    return render_template('admin/login.html')


@admin_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('admin.login'))


@admin_bp.route('/')
@login_required
def dashboard():
    purchases = Purchase.query.order_by(Purchase.created_at.desc()).all()
    total_revenue = sum(p.amount for p in purchases if p.status == 'confirmed')
    total_purchases = len([p for p in purchases if p.status == 'confirmed'])
    unique_emails = len(set(p.email for p in purchases if p.status == 'confirmed'))
    return render_template('admin/dashboard.html',
                           purchases=purchases,
                           total_revenue=total_revenue,
                           total_purchases=total_purchases,
                           unique_emails=unique_emails)


@admin_bp.route('/export')
@login_required
def export_csv():
    purchases = Purchase.query.order_by(Purchase.created_at.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Date', 'Email', 'Name', 'PayPal Txn ID', 'Amount', 'Currency',
                     'Status', 'Downloads', 'Token'])
    for p in purchases:
        writer.writerow([
            p.created_at.strftime('%Y-%m-%d %H:%M') if p.created_at else '',
            p.email, p.name, p.paypal_txn_id, f'{p.amount:.2f}', p.currency,
            p.status, p.download_count, p.download_token
        ])
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=purchases.csv'}
    )
