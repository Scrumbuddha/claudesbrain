import csv
import io
import os
import uuid
from datetime import datetime

import boto3
from botocore.exceptions import ClientError
from flask import Blueprint, render_template, redirect, url_for, request, flash, Response
from flask_login import login_user, logout_user, login_required, current_user

from models import db, AdminUser, Purchase, Testimonial, Coupon, Changelog, EmailCapture, Referral

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
    date_from_str = request.args.get('date_from', '')
    date_to_str   = request.args.get('date_to', '')

    q = Purchase.query
    try:
        if date_from_str:
            q = q.filter(Purchase.created_at >= datetime.strptime(date_from_str, '%Y-%m-%d'))
        if date_to_str:
            q = q.filter(Purchase.created_at <= datetime.strptime(date_to_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59))
    except ValueError:
        pass

    purchases = q.order_by(Purchase.created_at.desc()).all()
    total_revenue = sum(p.amount for p in purchases if p.status == 'confirmed')
    total_purchases = len([p for p in purchases if p.status == 'confirmed'])
    unique_emails = len(set(p.email for p in purchases if p.status == 'confirmed'))
    files = {fmt: _file_info(fmt) for fmt in ('pdf', 'docx')}
    return render_template('admin/dashboard.html',
                           purchases=purchases,
                           total_revenue=total_revenue,
                           total_purchases=total_purchases,
                           unique_emails=unique_emails,
                           files=files,
                           date_from=date_from_str,
                           date_to=date_to_str)


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


@admin_bp.route('/purchase/<int:purchase_id>/set-tier', methods=['POST'])
@login_required
def set_tier(purchase_id):
    p = Purchase.query.get_or_404(purchase_id)
    tier = request.form.get('tier', 'standard')
    if tier not in ('standard', 'pro'):
        tier = 'standard'
    p.tier = tier
    db.session.commit()
    flash(f'Tier for {p.email} set to {tier}.', 'success')
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/purchase/<int:purchase_id>/revoke', methods=['POST'])
@login_required
def revoke_access(purchase_id):
    p = Purchase.query.get_or_404(purchase_id)
    p.status = 'revoked'
    db.session.commit()
    flash(f'Access revoked for {p.email}.', 'success')
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/purchase/<int:purchase_id>/delete', methods=['POST'])
@login_required
def delete_purchase(purchase_id):
    p = Purchase.query.get_or_404(purchase_id)
    email = p.email
    db.session.delete(p)
    db.session.commit()
    flash(f'Purchase record for {email} deleted.', 'success')
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/purchase/bulk', methods=['POST'])
@login_required
def bulk_action():
    action = request.form.get('action')
    ids = request.form.getlist('selected_ids')
    if not ids:
        flash('No records selected.', 'error')
        return redirect(url_for('admin.dashboard'))
    purchases = Purchase.query.filter(Purchase.id.in_([int(i) for i in ids])).all()
    if action == 'delete':
        for p in purchases:
            db.session.delete(p)
        db.session.commit()
        flash(f'Deleted {len(purchases)} record(s).', 'success')
    elif action == 'revoke':
        count = 0
        for p in purchases:
            if p.status != 'revoked':
                p.status = 'revoked'
                count += 1
        db.session.commit()
        flash(f'Revoked access for {count} record(s).', 'success')
    else:
        flash('Unknown action.', 'error')
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/purchase/create', methods=['POST'])
@login_required
def create_purchase():
    email = request.form.get('email', '').strip()
    name = request.form.get('name', '').strip()
    amount = request.form.get('amount', '6.99').strip()
    tier = request.form.get('tier', 'standard').strip()
    if tier not in ('standard', 'pro'):
        tier = 'standard'
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
        tier=tier,
        download_token=uuid.uuid4().hex,
    )
    db.session.add(p)
    db.session.commit()
    download_url = url_for('payments.download_page', token=p.download_token, _external=True)
    try:
        from payments import _send_receipt_email
        _send_receipt_email(p)
        flash(f'Purchase created for {email} and receipt email sent. Download link: {download_url}', 'success')
    except Exception as e:
        flash(f'Purchase created for {email} but email failed: {e}. Download link: {download_url}', 'error')
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/test-email', methods=['POST'])
@login_required
def test_email():
    from app import mail
    from flask_mail import Message
    from flask import current_app
    to = request.form.get('email', '').strip() or current_user.email
    try:
        msg = Message(
            subject="Test email from claudesbrain.com",
            sender=current_app.config.get('MAIL_DEFAULT_SENDER'),
            recipients=[to],
        )
        msg.body = "This is a test email to confirm SES SMTP is working correctly."
        mail.send(msg)
        flash(f'Test email sent to {to}.', 'success')
    except Exception as e:
        flash(f'Test email failed: {e}', 'error')
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/export')
@login_required
def export_csv():
    date_from_str = request.args.get('date_from', '')
    date_to_str   = request.args.get('date_to', '')
    q = Purchase.query
    try:
        if date_from_str:
            q = q.filter(Purchase.created_at >= datetime.strptime(date_from_str, '%Y-%m-%d'))
        if date_to_str:
            q = q.filter(Purchase.created_at <= datetime.strptime(date_to_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59))
    except ValueError:
        pass
    purchases = q.order_by(Purchase.created_at.desc()).all()
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


# ── Testimonials ──────────────────────────────────────────────────────────────

@admin_bp.route('/testimonials')
@login_required
def testimonials():
    items = Testimonial.query.order_by(Testimonial.created_at.desc()).all()
    return render_template('admin/testimonials.html', testimonials=items)


@admin_bp.route('/testimonials/add', methods=['POST'])
@login_required
def add_testimonial():
    name = request.form.get('name', '').strip()
    role = request.form.get('role', '').strip()
    body = request.form.get('body', '').strip()
    approved = request.form.get('approved') == '1'
    if not name or not body:
        flash('Name and quote are required.', 'error')
        return redirect(url_for('admin.testimonials'))
    t = Testimonial(name=name, role=role, body=body, approved=approved)
    db.session.add(t)
    db.session.commit()
    flash(f'Testimonial from {name} added.', 'success')
    return redirect(url_for('admin.testimonials'))


@admin_bp.route('/testimonials/<int:tid>/toggle', methods=['POST'])
@login_required
def toggle_testimonial(tid):
    t = Testimonial.query.get_or_404(tid)
    t.approved = not t.approved
    db.session.commit()
    status = 'approved' if t.approved else 'hidden'
    flash(f'Testimonial by {t.name} {status}.', 'success')
    return redirect(url_for('admin.testimonials'))


@admin_bp.route('/testimonials/<int:tid>/delete', methods=['POST'])
@login_required
def delete_testimonial(tid):
    t = Testimonial.query.get_or_404(tid)
    db.session.delete(t)
    db.session.commit()
    flash('Testimonial deleted.', 'success')
    return redirect(url_for('admin.testimonials'))


# ── Coupons ───────────────────────────────────────────────────────────────────

@admin_bp.route('/coupons')
@login_required
def coupons():
    items = Coupon.query.order_by(Coupon.created_at.desc()).all()
    return render_template('admin/coupons.html', coupons=items)


@admin_bp.route('/coupons/add', methods=['POST'])
@login_required
def add_coupon():
    code = request.form.get('code', '').strip().upper()
    discount_type = request.form.get('discount_type', 'percent')
    discount_value = request.form.get('discount_value', '0')
    max_uses = request.form.get('max_uses', '').strip()
    expires_at_str = request.form.get('expires_at', '').strip()
    if not code:
        flash('Code is required.', 'error')
        return redirect(url_for('admin.coupons'))
    if Coupon.query.filter_by(code=code).first():
        flash(f'Code {code} already exists.', 'error')
        return redirect(url_for('admin.coupons'))
    try:
        discount_value = float(discount_value)
    except ValueError:
        flash('Invalid discount value.', 'error')
        return redirect(url_for('admin.coupons'))
    expires_at = None
    if expires_at_str:
        try:
            expires_at = datetime.strptime(expires_at_str, '%Y-%m-%d')
        except ValueError:
            pass
    c = Coupon(
        code=code,
        discount_type=discount_type,
        discount_value=discount_value,
        max_uses=int(max_uses) if max_uses else None,
        expires_at=expires_at,
    )
    db.session.add(c)
    db.session.commit()
    flash(f'Coupon {code} created.', 'success')
    return redirect(url_for('admin.coupons'))


@admin_bp.route('/coupons/<int:cid>/toggle', methods=['POST'])
@login_required
def toggle_coupon(cid):
    c = Coupon.query.get_or_404(cid)
    c.active = not c.active
    db.session.commit()
    flash(f'Coupon {c.code} {"activated" if c.active else "deactivated"}.', 'success')
    return redirect(url_for('admin.coupons'))


@admin_bp.route('/coupons/<int:cid>/delete', methods=['POST'])
@login_required
def delete_coupon(cid):
    c = Coupon.query.get_or_404(cid)
    db.session.delete(c)
    db.session.commit()
    flash('Coupon deleted.', 'success')
    return redirect(url_for('admin.coupons'))


# ── Changelog ─────────────────────────────────────────────────────────────────

@admin_bp.route('/changelog')
@login_required
def changelog():
    items = Changelog.query.order_by(Changelog.published_at.desc()).all()
    return render_template('admin/changelog.html', entries=items)


@admin_bp.route('/changelog/add', methods=['POST'])
@login_required
def add_changelog():
    title = request.form.get('title', '').strip()
    body = request.form.get('body', '').strip()
    if not title or not body:
        flash('Title and body are required.', 'error')
        return redirect(url_for('admin.changelog'))
    entry = Changelog(title=title, body=body)
    db.session.add(entry)
    db.session.commit()
    flash(f'Changelog entry "{title}" published.', 'success')
    return redirect(url_for('admin.changelog'))


@admin_bp.route('/changelog/<int:eid>/delete', methods=['POST'])
@login_required
def delete_changelog(eid):
    entry = Changelog.query.get_or_404(eid)
    db.session.delete(entry)
    db.session.commit()
    flash('Changelog entry deleted.', 'success')
    return redirect(url_for('admin.changelog'))


# ── Email Broadcast ───────────────────────────────────────────────────────────

@admin_bp.route('/broadcast', methods=['GET', 'POST'])
@login_required
def broadcast():
    email_captures = EmailCapture.query.order_by(EmailCapture.created_at.desc()).all()
    confirmed_purchases = Purchase.query.filter_by(status='confirmed').order_by(Purchase.created_at.desc()).all()
    if request.method == 'POST':
        subject = request.form.get('subject', '').strip()
        body_html = request.form.get('body_html', '').strip()
        audience = request.form.get('audience', 'purchases')  # purchases / captures / all
        if not subject or not body_html:
            flash('Subject and body are required.', 'error')
            return redirect(url_for('admin.broadcast'))
        recipients = set()
        if audience in ('purchases', 'all'):
            for p in confirmed_purchases:
                recipients.add(p.email)
        if audience in ('captures', 'all'):
            for c in email_captures:
                recipients.add(c.email)
        from app import mail
        from flask_mail import Message
        from flask import current_app
        sent = 0
        failed = 0
        for email in recipients:
            try:
                msg = Message(
                    subject=subject,
                    sender=current_app.config.get('MAIL_DEFAULT_SENDER'),
                    recipients=[email],
                )
                msg.html = body_html
                mail.send(msg)
                sent += 1
            except Exception as e:
                current_app.logger.error(f'Broadcast failed for {email}: {e}')
                failed += 1
        flash(f'Broadcast sent to {sent} recipients. {failed} failed.', 'success' if not failed else 'error')
        return redirect(url_for('admin.broadcast'))
    return render_template('admin/broadcast.html',
                           purchase_count=len(confirmed_purchases),
                           capture_count=len(email_captures))


# ── Referrals ─────────────────────────────────────────────────────────────────

@admin_bp.route('/referrals')
@login_required
def referrals():
    items = Referral.query.order_by(Referral.conversions.desc()).all()
    return render_template('admin/referrals.html', referrals=items)
