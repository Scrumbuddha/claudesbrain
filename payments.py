import os
import uuid
import boto3
import requests
from botocore.exceptions import ClientError
from flask import Blueprint, request, redirect, url_for, render_template, abort, current_app, jsonify
from flask_mail import Message

from models import db, Purchase, Coupon, Referral

S3_BUCKET = os.environ.get('EBOOK_S3_BUCKET', '')
S3_KEYS = {
    'pdf':  'ebooks/building-claudes-brain.pdf',
    'docx': 'ebooks/building-claudes-brain.docx',
}
S3_FILENAMES = {
    'pdf':  'building-claudes-brain.pdf',
    'docx': 'building-claudes-brain.docx',
}

# Pro Bundle — 4 bonus files (PDF + Markdown)
# 'key_pdf' / 'key_md' are exact S3 keys; 'filename_*' are ASCII-safe download names
PRO_BUNDLE_FILES = [
    {
        'key_pdf':      "ebooks/pro-bundle/Claude's Brain \u2014 Prompt Library.pdf",
        'key_md':       "ebooks/pro-bundle/Claudes-Brain-Prompt-Library.md",
        'filename_pdf': "Claudes-Brain-Prompt-Library.pdf",
        'filename_md':  "Claudes-Brain-Prompt-Library.md",
        'label':        'Prompt Library (55+ prompts)',
    },
    {
        'key_pdf':      "ebooks/pro-bundle/Claude's Brain \u2014 CLAUDE.md Starter Kit.pdf",
        'key_md':       "ebooks/pro-bundle/Claudes-Brain-CLAUDE-md-Starter-Kit.md",
        'filename_pdf': "Claudes-Brain-CLAUDE-md-Starter-Kit.pdf",
        'filename_md':  "Claudes-Brain-CLAUDE-md-Starter-Kit.md",
        'label':        'CLAUDE.md Starter Kit (7 templates)',
    },
    {
        'key_pdf':      "ebooks/pro-bundle/Claude's Brain \u2014 Slash Command Library.pdf",
        'key_md':       "ebooks/pro-bundle/Claudes-Brain-Slash-Command-Library.md",
        'filename_pdf': "Claudes-Brain-Slash-Command-Library.pdf",
        'filename_md':  "Claudes-Brain-Slash-Command-Library.md",
        'label':        'Slash Command Library (10 commands)',
    },
    {
        'key_pdf':      "ebooks/pro-bundle/Claude's Brain \u2014 Sub-Agent Templates.pdf",
        'key_md':       "ebooks/pro-bundle/Claudes-Brain-Sub-Agent-Templates.md",
        'filename_pdf': "Claudes-Brain-Sub-Agent-Templates.pdf",
        'filename_md':  "Claudes-Brain-Sub-Agent-Templates.md",
        'label':        'Sub-Agent Templates (8 agents)',
    },
]

PAYPAL_CLIENT_ID = os.environ.get('PAYPAL_CLIENT_ID', '')
PAYPAL_SECRET = os.environ.get('PAYPAL_SECRET', '')
PAYPAL_RECEIVER_EMAIL = os.environ.get('PAYPAL_RECEIVER_EMAIL', 'mark@scrumbuddhism.com')
PAYPAL_API_LIVE = 'https://api-m.paypal.com'
PAYPAL_API_SANDBOX = 'https://api-m.sandbox.paypal.com'


def _paypal_base():
    from flask import current_app
    return PAYPAL_API_SANDBOX if current_app.config.get('PAYPAL_SANDBOX') else PAYPAL_API_LIVE


def _paypal_token():
    resp = requests.post(
        f'{_paypal_base()}/v1/oauth2/token',
        auth=(PAYPAL_CLIENT_ID, PAYPAL_SECRET),
        data={'grant_type': 'client_credentials'},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()['access_token']


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

PRODUCT_PRICES = {
    'standard': 6.99,
    'pro': 14.99,
}


@payments_bp.route('/validate-coupon', methods=['POST'])
def validate_coupon():
    data = request.get_json()
    code = (data.get('code', '') if data else '').strip().upper()
    tier = (data.get('tier', 'standard') if data else 'standard')
    if not code:
        return jsonify({'error': 'No code provided'}), 400
    coupon = Coupon.query.filter_by(code=code).first()
    if not coupon:
        return jsonify({'valid': False, 'message': 'Coupon not found.'})
    valid, msg = coupon.is_valid()
    if not valid:
        return jsonify({'valid': False, 'message': msg})
    base_price = PRODUCT_PRICES.get(tier, PRODUCT_PRICES['standard'])
    discounted = coupon.apply(base_price)
    savings = round(base_price - discounted, 2)
    return jsonify({
        'valid': True,
        'code': coupon.code,
        'original': base_price,
        'discounted': discounted,
        'savings': savings,
        'message': f'Coupon applied — save ${savings:.2f}!'
    })


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

    if receiver_email.lower() != PAYPAL_RECEIVER_EMAIL.lower():
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


@payments_bp.route('/create-order', methods=['POST'])
def create_order():
    """Create a PayPal order — called by Smart Buttons JS."""
    data = request.get_json() or {}
    tier = data.get('tier', 'standard')
    coupon_code = data.get('coupon', '').strip().upper()
    referral_code = data.get('referral', '').strip().upper()

    base_price = PRODUCT_PRICES.get(tier, PRODUCT_PRICES['standard'])
    final_price = base_price
    coupon = None

    if coupon_code:
        coupon = Coupon.query.filter_by(code=coupon_code).first()
        if coupon:
            valid, _ = coupon.is_valid()
            if valid:
                final_price = coupon.apply(base_price)

    description = "Building Claude's Brain — Pro Bundle (PDF + DOCX + Prompt Library)" if tier == 'pro' else "Building Claude's Brain (PDF + DOCX)"

    try:
        token = _paypal_token()
        resp = requests.post(
            f'{_paypal_base()}/v2/checkout/orders',
            headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
            json={
                'intent': 'CAPTURE',
                'purchase_units': [{
                    'amount': {'currency_code': 'USD', 'value': f'{final_price:.2f}'},
                    'description': description,
                    'custom_id': f'{tier}|{coupon_code}|{referral_code}',
                }],
            },
            timeout=15,
        )
        resp.raise_for_status()
        return jsonify({'id': resp.json()['id'], 'price': final_price})
    except Exception as e:
        current_app.logger.error(f'create-order error: {e}')
        return jsonify({'error': str(e)}), 500


def _get_order(token, order_id):
    """Fetch order details from PayPal."""
    resp = requests.get(
        f'{_paypal_base()}/v2/checkout/orders/{order_id}',
        headers={'Authorization': f'Bearer {token}'},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


@payments_bp.route('/capture-order', methods=['POST'])
def capture_order():
    """Capture a PayPal order after customer approves — creates Purchase and sends email."""
    data = request.get_json() or {}
    order_id = data.get('orderID')
    # Frontend passes tier/coupon/referral directly as a reliable fallback
    client_tier = data.get('tier', '').strip()
    client_coupon = data.get('coupon', '').strip().upper()
    client_referral = data.get('referral', '').strip().upper()
    if not order_id:
        return jsonify({'error': 'Missing orderID'}), 400
    try:
        token = _paypal_token()
        resp = requests.post(
            f'{_paypal_base()}/v2/checkout/orders/{order_id}/capture',
            headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
            timeout=15,
        )
        if resp.status_code == 422:
            # Order already captured — fetch order details to recover the purchase
            current_app.logger.warning(f'capture-order 422 for order {order_id}, fetching order details')
            try:
                order = _get_order(token, order_id)
            except Exception as e:
                current_app.logger.error(f'capture-order 422 recovery failed: {e}')
                return jsonify({'error': 'Payment already processed. Check your email for a download link or contact mark@scrumbuddhism.com'}), 422
        else:
            resp.raise_for_status()
            order = resp.json()
    except Exception as e:
        current_app.logger.error(f'capture-order error: {e}')
        return jsonify({'error': str(e)}), 500

    if order.get('status') != 'COMPLETED':
        return jsonify({'error': f"Payment status: {order.get('status')}"}), 400

    capture = order['purchase_units'][0]['payments']['captures'][0]
    txn_id = capture['id']
    amount = float(capture['amount']['value'])
    currency = capture['amount']['currency_code']
    payer = order.get('payer', {})
    payer_email = payer.get('email_address', '')
    name = payer.get('name', {})
    payer_name = f"{name.get('given_name', '')} {name.get('surname', '')}".strip()

    # Parse custom_id for tier/coupon/referral
    custom_id = order['purchase_units'][0].get('custom_id', '') or ''
    parts = custom_id.split('|')
    tier_from_custom = parts[0] if len(parts) > 0 else ''
    coupon_from_custom = parts[1] if len(parts) > 1 else ''
    referral_from_custom = parts[2] if len(parts) > 2 else ''

    # Prefer client-supplied values (always present); fall back to custom_id
    tier = (client_tier if client_tier in ('standard', 'pro') else None) \
           or (tier_from_custom if tier_from_custom in ('standard', 'pro') else 'standard')
    coupon_code = client_coupon or coupon_from_custom
    referral_code = client_referral or referral_from_custom

    current_app.logger.info(
        f'capture-order: order={order_id} tier={tier} coupon={coupon_code} '
        f'referral={referral_code} custom_id={custom_id!r} amount={amount}'
    )

    coupon = Coupon.query.filter_by(code=coupon_code).first() if coupon_code else None
    coupon_id = coupon.id if coupon else None

    # Deduplicate
    existing = Purchase.query.filter_by(paypal_txn_id=txn_id).first()
    if existing:
        return jsonify({'redirect': url_for('payments.download_page', token=existing.download_token, _external=True)})

    purchase = Purchase(
        email=payer_email,
        name=payer_name,
        paypal_txn_id=txn_id,
        amount=amount,
        currency=currency,
        status='confirmed',
        tier=tier if tier in ('standard', 'pro') else 'standard',
        coupon_id=coupon_id,
        referral_code_used=referral_code or None,
        download_token=uuid.uuid4().hex,
    )
    db.session.add(purchase)
    db.session.flush()  # get purchase.id before commit

    # Increment coupon use count
    if coupon:
        coupon.use_count += 1

    # Credit referral
    if referral_code:
        ref = Referral.query.filter_by(code=referral_code).first()
        if ref:
            ref.conversions += 1

    db.session.commit()

    try:
        _send_receipt_email(purchase)
    except Exception as e:
        current_app.logger.error(f'Receipt email failed: {e}')

    return jsonify({'redirect': url_for('payments.download_page', token=purchase.download_token, _external=True)})


def _send_receipt_email(purchase):
    """Send receipt email with download link."""
    from app import mail

    download_url = url_for('payments.download_page', token=purchase.download_token, _external=True)
    is_pro = getattr(purchase, 'tier', 'standard') == 'pro'

    pro_note = """
        <div style="background:#1a1a10;border:1px solid #C9A227;border-radius:6px;padding:16px 20px;margin:20px 0">
          <div style="color:#C9A227;font-weight:700;font-size:14px;margin-bottom:6px">&#127381; Pro Bundle included</div>
          <div style="color:#d4d4e8;font-size:13px">Your download page includes 4 bonus files — Prompt Library, CLAUDE.md Starter Kit, Slash Command Library, and Sub-Agent Templates — each in Markdown and PDF.</div>
        </div>
    """ if is_pro else ''

    msg = Message(
        subject="Your copy of Building Claude's Brain" + (" — Pro Bundle" if is_pro else ""),
        sender=current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@claudesbrain.com'),
        recipients=[purchase.email],
    )
    msg.html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;background:#080810;color:#d4d4e8;padding:40px;border-radius:8px">
        <h1 style="color:#C9A227;font-size:28px;margin-bottom:8px">Thank you for your purchase!</h1>
        <p style="color:#7a7a9a;font-size:16px;margin-bottom:24px">Your copy of <strong style="color:#fff">Building Claude's Brain</strong> is ready to download.</p>
        {pro_note}
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


@payments_bp.route('/download/<token>/pro/<int:idx>/<fmt>')
def download_pro_file(token, idx, fmt):
    """Redirect to S3 pre-signed URL for a Pro Bundle file (pdf or md)."""
    if fmt not in ('pdf', 'md'):
        abort(400)
    purchase = Purchase.query.filter_by(download_token=token, status='confirmed').first()
    if not purchase:
        abort(404)
    if purchase.tier != 'pro':
        abort(403)
    if idx < 0 or idx >= len(PRO_BUNDLE_FILES):
        abort(400)

    item = PRO_BUNDLE_FILES[idx]
    s3 = boto3.client('s3', region_name='us-east-1')
    try:
        url = s3.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': S3_BUCKET,
                'Key': item[f'key_{fmt}'],
                'ResponseContentDisposition': f'attachment; filename="{item[f"filename_{fmt}"]}"',
            },
            ExpiresIn=900,
        )
    except ClientError:
        abort(500)

    return redirect(url)
