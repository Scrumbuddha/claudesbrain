import csv
import io
import os
import uuid

import boto3
from botocore.exceptions import ClientError
from flask import Blueprint, render_template, redirect, url_for, request, flash, Response
from flask_login import login_user, logout_user, login_required, current_user

from models import db, AdminUser, Purchase

S3_BUCKET = os.environ.get('EBOOK_S3_BUCKET', '')
S3_PREFIX = 'ebooks/'
EBOOK_KEYS = {
    'pdf':  S3_PREFIX + 'building-claudes-brain.pdf',
    'docx': S3_PREFIX + 'building-claudes-brain.docx',
}
ALLOWED_MIMETYPES = {
    'pdf':  'application/pdf',
    'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
}


def _s3():
    return boto3.client('s3', region_name='us-east-1')


def _file_info(fmt):
    """Return {'size': int, 'last_modified': datetime} or None if missing."""
    try:
        resp = _s3().head_object(Bucket=S3_BUCKET, Key=EBOOK_KEYS[fmt])
        return {'size': resp['ContentLength'], 'last_modified': resp['LastModified']}
    except ClientError:
        return None

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
    files = {fmt: _file_info(fmt) for fmt in ('pdf', 'docx')}
    return render_template('admin/dashboard.html',
                           purchases=purchases,
                           total_revenue=total_revenue,
                           total_purchases=total_purchases,
                           unique_emails=unique_emails,
                           files=files)


@admin_bp.route('/upload/<fmt>', methods=['POST'])
@login_required
def upload_file(fmt):
    if fmt not in EBOOK_KEYS:
        flash('Invalid file type.', 'error')
        return redirect(url_for('admin.dashboard'))
    f = request.files.get('file')
    if not f or f.filename == '':
        flash('No file selected.', 'error')
        return redirect(url_for('admin.dashboard'))
    if f.mimetype not in (ALLOWED_MIMETYPES[fmt], 'application/octet-stream'):
        flash(f'Wrong file type for {fmt.upper()}. Expected {ALLOWED_MIMETYPES[fmt]}.', 'error')
        return redirect(url_for('admin.dashboard'))
    try:
        _s3().upload_fileobj(f, S3_BUCKET, EBOOK_KEYS[fmt],
                             ExtraArgs={'ContentType': ALLOWED_MIMETYPES[fmt]})
        flash(f'{fmt.upper()} uploaded successfully.', 'success')
    except ClientError as e:
        flash(f'Upload failed: {e}', 'error')
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/purchase/<int:purchase_id>/grant', methods=['POST'])
@login_required
def grant_downloads(purchase_id):
    p = Purchase.query.get_or_404(purchase_id)
    p.max_downloads += 5
    db.session.commit()
    flash(f'Granted 5 extra downloads to {p.email}.', 'success')
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/purchase/<int:purchase_id>/revoke', methods=['POST'])
@login_required
def revoke_access(purchase_id):
    p = Purchase.query.get_or_404(purchase_id)
    p.status = 'revoked'
    db.session.commit()
    flash(f'Access revoked for {p.email}.', 'success')
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/purchase/create', methods=['POST'])
@login_required
def create_purchase():
    email = request.form.get('email', '').strip()
    name = request.form.get('name', '').strip()
    amount = request.form.get('amount', '6.99').strip()
    if not email:
        flash('Email is required.', 'error')
        return redirect(url_for('admin.dashboard'))
    try:
        amount = float(amount)
    except ValueError:
        amount = 6.99
    p = Purchase(
        email=email,
        name=name,
        paypal_txn_id=f'MANUAL-{uuid.uuid4().hex[:12].upper()}',
        amount=amount,
        currency='USD',
        status='confirmed',
        download_token=uuid.uuid4().hex,
    )
    db.session.add(p)
    db.session.commit()
    download_url = url_for('payments.download_page', token=p.download_token, _external=True)
    flash(f'Purchase created for {email}. Download link: {download_url}', 'success')
    return redirect(url_for('admin.dashboard'))


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
