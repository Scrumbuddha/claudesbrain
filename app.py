import os

from flask import Flask, render_template, Response
from flask_login import LoginManager
from flask_mail import Mail
from flask_wtf.csrf import CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix

from models import db, AdminUser, Testimonial, EmailCapture

mail = Mail()
login_manager = LoginManager()
csrf = CSRFProtect()


def create_app():
    app = Flask(__name__)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    # --- Config ---
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-change-in-production')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
        'DATABASE_URL', 'sqlite:///claudesbrain.db'
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # PayPal
    app.config['PAYPAL_SANDBOX'] = os.environ.get('PAYPAL_SANDBOX', 'true').lower() == 'true'

    # Mail (AWS SES or any SMTP)
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'email-smtp.us-east-1.amazonaws.com')
    app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', '')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@stpeteai.org')

    # --- Extensions ---
    db.init_app(app)
    mail.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'admin.login'
    csrf.init_app(app)

    # Exempt IPN from CSRF (PayPal posts to it)
    from payments import payments_bp
    csrf.exempt(payments_bp)

    # --- Blueprints ---
    from admin import admin_bp
    from brain_app import brain_app_bp
    app.register_blueprint(payments_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(brain_app_bp)

    # Exempt AJAX endpoints from CSRF (JS fetch from landing page)
    csrf.exempt('app.capture_email')
    csrf.exempt('payments.validate_coupon')

    # --- Routes ---
    @app.route('/')
    def index():
        testimonials = Testimonial.query.filter_by(approved=True).order_by(Testimonial.created_at.desc()).limit(4).all()
        return render_template('index.html',
                               paypal_client_id=os.environ.get('PAYPAL_CLIENT_ID', ''),
                               testimonials=testimonials)

    @app.route('/capture-email', methods=['POST'])
    def capture_email():
        from flask import request, jsonify
        data = request.get_json()
        email = (data.get('email', '') if data else '').strip().lower()
        if not email or '@' not in email:
            return jsonify({'error': 'Invalid email'}), 400
        existing = EmailCapture.query.filter_by(email=email).first()
        if not existing:
            capture = EmailCapture(email=email, source='landing')
            db.session.add(capture)
            db.session.commit()
            try:
                _send_free_chapter_email(email)
                capture.free_chapter_sent = True
                db.session.commit()
            except Exception as e:
                app.logger.error(f'Free chapter email failed: {e}')
        return jsonify({'ok': True})

    def _send_free_chapter_email(email):
        from flask_mail import Message
        import boto3
        S3_BUCKET = os.environ.get('EBOOK_S3_BUCKET', '')
        s3 = boto3.client('s3', region_name='us-east-1')
        url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': S3_BUCKET, 'Key': 'ebooks/chapter1-free.pdf',
                    'ResponseContentDisposition': 'attachment; filename="claude-brain-chapter1.pdf"'},
            ExpiresIn=604800  # 7 days
        )
        msg = Message(
            subject="Your free chapter: Building Claude's Brain — Chapter 1",
            sender=app.config.get('MAIL_DEFAULT_SENDER', 'noreply@claudesbrain.com'),
            recipients=[email],
        )
        msg.html = f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;background:#080810;color:#d4d4e8;padding:40px;border-radius:8px">
            <h1 style="color:#C9A227;font-size:24px;margin-bottom:8px">Chapter 1 is yours.</h1>
            <p style="color:#7a7a9a;margin-bottom:24px">Here's your free preview of <strong style="color:#fff">Building Claude's Brain</strong> — Chapter 1: CLAUDE.md.</p>
            <div style="margin:28px 0;text-align:center">
                <a href="{url}" style="display:inline-block;background:#C9A227;color:#080810;font-weight:700;padding:14px 28px;border-radius:6px;text-decoration:none;font-size:15px">Download Chapter 1 (PDF)</a>
            </div>
            <p style="color:#7a7a9a;font-size:13px">Link expires in 7 days. If you'd like the full ebook, visit <a href="https://www.claudesbrain.com" style="color:#C9A227">claudesbrain.com</a>.</p>
            <hr style="border:none;border-top:1px solid #2a2a3d;margin:24px 0">
            <p style="color:#7a7a9a;font-size:12px">St. Pete AI &middot; stpeteai.org</p>
        </div>
        """
        mail.send(msg)

    @app.route('/stpeteai')
    def stpeteai():
        return render_template('stpeteai_index.html')

    @app.route('/terms')
    def terms():
        return render_template('terms.html')

    @app.route('/robots.txt')
    def robots():
        return Response(
            "User-agent: *\nAllow: /\nDisallow: /admin/\nDisallow: /download/\nDisallow: /thank-you\nSitemap: https://www.claudesbrain.com/sitemap.xml\n",
            mimetype='text/plain'
        )

    @app.route('/sitemap.xml')
    def sitemap():
        return Response(
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            '<url><loc>https://www.claudesbrain.com/</loc><changefreq>monthly</changefreq><priority>1.0</priority></url>'
            '<url><loc>https://www.claudesbrain.com/terms</loc><changefreq>yearly</changefreq><priority>0.3</priority></url>'
            '</urlset>',
            mimetype='application/xml'
        )

    # --- DB setup & seed ---
    with app.app_context():
        db.create_all()
        _seed_admin()

    return app


@login_manager.user_loader
def load_user(user_id):
    return AdminUser.query.get(int(user_id))


def _seed_admin():
    """Create default admin user if none exists. If ADMIN_PASSWORD env var is set, force-reset the password."""
    admin = AdminUser.query.filter_by(email='admin@stpeteai.org').first()
    force_password = os.environ.get('ADMIN_PASSWORD')
    if not admin:
        admin = AdminUser(email='admin@stpeteai.org')
        admin.set_password(force_password or 'admin123')
        db.session.add(admin)
        db.session.commit()
    elif force_password:
        admin.set_password(force_password)
        db.session.commit()


# Create the app instance for gunicorn / `python app.py`
app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5001)
