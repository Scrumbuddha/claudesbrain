import os

from flask import Flask, render_template, Response
from flask_login import LoginManager
from flask_mail import Mail
from flask_wtf.csrf import CSRFProtect

from models import db, AdminUser

mail = Mail()
login_manager = LoginManager()
csrf = CSRFProtect()


def create_app():
    app = Flask(__name__)

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
    app.register_blueprint(payments_bp)
    app.register_blueprint(admin_bp)

    # --- Routes ---
    @app.route('/')
    def index():
        return render_template('index.html')

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
