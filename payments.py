import os
import uuid
import boto3
import requests
from botocore.exceptions import ClientError
from flask import Blueprint, request, redirect, url_for, render_template, abort, current_app
from flask_mail import Message

from models import db, Purchase

S3_BUCKET = os.environ.get('EBOOK_S3_BUCKET', '')
S3_KEYS = {
    'pdf':  'ebooks/building-claudes-brain.pdf',
    'docx': 'ebooks/building-claudes-brain.docx',
}
S3_FILENAMES = {
    'pdf':  'building-claudes-brain.pdf',
    'docx': 'building-claudes-brain.docx',
}


def _presigned_url(fmt):
    s3 = boto3.client('s3', region_name='us-east-1')
    return s3.generate_presigned_url(
        'get_object',
        Params={'Bucket': S3_BUCKET, 'Key': S3_KEYS[fmt],
                'ResponseContentDisposition': f'attachment; filename="{S3_FILENAMES[fmt]}"'},
        ExpiresIn=900  # 15 minutes
    )

payments_bp = Blueprint('payments', __name__)

PAYPAL_VERIFY_URL = 'https://ipnpb.paypal.com/cgi-bin/webscr'
PAYPAL_SANDBOX_VERIFY_URL = 'https://ipnpb.sandbox.paypal.com/cgi-bin/webscr'


@payments_bp.route('/ipn', methods=['POST'])
def ipn():
    """PayPal IPN listener — verifies payment and creates Purchase record."""
    # Read the raw POST data from PayPal
    ipn_data = request.form.to_dict()

    # Post back to PayPal for verification
    verify_payload = 'cmd=_notify-validate&' + request.get_data(as_text=True)
    verify_url = PAYPAL_SANDBOX_VERIFY_URL if current_app.config.get('PAYPAL_SANDBOX') else PAYPAL_VERIFY_URL

    try:
        response = requests.post(verify_url, data=verify_payload,
                                 headers={'Content-Type': 'application/x-www-form-urlencoded'},
                                 timeout=30)
    except requests.RequestException:
        return 'IPN verify failed', 500

    if response.text != 'VERIFIED':
        return 'IPN not verified', 400

    # Extract transaction details
    payment_status = ipn_data.get('payment_status', '')
    txn_id = ipn_data.get('txn_id', '')
    payer_email = ipn_data.get('payer_email', '')
    first_name = ipn_data.get('first_name', '')
    last_name = ipn_data.get('last_name', '')
    mc_gross = ipn_data.get('mc_gross', '0')
    mc_currency = ipn_data.get('mc_currency', 'USD')
    receiver_email = ipn_data.get('receiver_email', '')

    # Validate payment
    if payment_status != 'Completed':
        return 'Payment not completed', 200

    if receiver_email.lower() != 'mark@scrumbuddhism.com':
        return 'Wrong receiver', 200

    try:
        amount = float(mc_gross)
    except (ValueError, TypeError):
        return 'Invalid amount', 200

    if amount < 6.99:
        return 'Amount too low', 200

    # Check for duplicate transaction
    existing = Purchase.query.filter_by(paypal_txn_id=txn_id).first()
    if existing:
        return 'Duplicate txn', 200

    # Create purchase record
    purchase = Purchase(
        email=payer_email,
        name=f'{first_name} {last_name}'.strip(),
        paypal_txn_id=txn_id,
        amount=amount,
        currency=mc_currency,
        status='confirmed',
        download_token=uuid.uuid4().hex,
    )
    db.session.add(purchase)
    db.session.commit()

    # Send email receipt with download link
    try:
        _send_receipt_email(purchase)
    except Exception as e:
        current_app.logger.error(f'Failed to send receipt email: {e}')

    return 'OK', 200


def _send_receipt_email(purchase):
    """Send receipt email with download link."""
    from app import mail

    download_url = url_for('payments.download_page', token=purchase.download_token, _external=True)

    msg = Message(
        subject="Your copy of Building Claude's Brain",
        sender=current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@stpeteai.org'),
        recipients=[purchase.email],
    )
    msg.html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;background:#080810;color:#d4d4e8;padding:40px;border-radius:8px">
        <h1 style="color:#C9A227;font-size:28px;margin-bottom:8px">Thank you for your purchase!</h1>
        <p style="color:#7a7a9a;font-size:16px;margin-bottom:24px">Your copy of <strong style="color:#fff">Building Claude's Brain</strong> is ready to download.</p>
        <p style="margin-bottom:8px"><strong>Name:</strong> {purchase.name}</p>
        <p style="margin-bottom:8px"><strong>Amount:</strong> ${purchase.amount:.2f} {purchase.currency}</p>
        <p style="margin-bottom:8px"><strong>Transaction:</strong> {purchase.paypal_txn_id}</p>
        <div style="margin:32px 0;text-align:center">
            <a href="{download_url}" style="display:inline-block;background:#C9A227;color:#080810;font-weight:700;padding:16px 32px;border-radius:6px;text-decoration:none;font-size:16px">Download Your Ebook</a>
        </div>
        <p style="color:#7a7a9a;font-size:13px">You can download up to {purchase.max_downloads} times. If you need help, email <a href="mailto:mark@scrumbuddhism.com" style="color:#C9A227">mark@scrumbuddhism.com</a></p>
        <hr style="border:none;border-top:1px solid #2a2a3d;margin:24px 0">
        <p style="color:#7a7a9a;font-size:12px">St. Pete AI &middot; stpeteai.org</p>
    </div>
    """
    mail.send(msg)


@payments_bp.route('/thank-you')
def thank_you():
    """Thank-you page after PayPal payment."""
    token = request.args.get('token', '')
    # Try to find purchase by token, or show generic thank-you
    purchase = None
    if token:
        purchase = Purchase.query.filter_by(download_token=token, status='confirmed').first()
    return render_template('thank_you.html', purchase=purchase, token=token)


@payments_bp.route('/download/<token>')
def download_page(token):
    """Download page — shows PDF/DOCX download buttons."""
    purchase = Purchase.query.filter_by(download_token=token).first()
    if not purchase:
        abort(404)
    if purchase.status == 'revoked':
        return render_template('download.html', purchase=purchase, error='Access has been revoked. Contact mark@scrumbuddhism.com for help.'), 403
    if purchase.status != 'confirmed':
        return render_template('download.html', purchase=purchase, error='Payment not confirmed yet.'), 403
    if purchase.download_count >= purchase.max_downloads:
        return render_template('download.html', purchase=purchase, error='Download limit reached. Contact mark@scrumbuddhism.com for help.')
    return render_template('download.html', purchase=purchase, error=None)


@payments_bp.route('/download/<token>/<fmt>')
def download_file(token, fmt):
    """Redirect to S3 pre-signed URL for the ebook file."""
    if fmt not in S3_KEYS:
        abort(400)

    purchase = Purchase.query.filter_by(download_token=token, status='confirmed').first()
    if not purchase:
        abort(404)
    if purchase.download_count >= purchase.max_downloads:
        abort(403)

    try:
        url = _presigned_url(fmt)
    except ClientError:
        abort(500)

    purchase.download_count += 1
    db.session.commit()

    return redirect(url)
