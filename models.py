import uuid
from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class Purchase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(255), default='')
    paypal_txn_id = db.Column(db.String(255), unique=True, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default='USD')
    status = db.Column(db.String(20), default='pending')  # pending / confirmed / refunded / revoked
    download_token = db.Column(db.String(64), unique=True, nullable=False,
                               default=lambda: uuid.uuid4().hex)
    download_count = db.Column(db.Integer, default=0)
    max_downloads = db.Column(db.Integer, default=5)
    tier = db.Column(db.String(20), default='standard')  # standard / pro
    coupon_id = db.Column(db.Integer, db.ForeignKey('coupon.id'), nullable=True)
    referral_code_used = db.Column(db.String(32), nullable=True)  # code used at purchase
    gift_recipient_email = db.Column(db.String(255), nullable=True)  # for gift purchases
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    coupon = db.relationship('Coupon', backref='purchases', foreign_keys=[coupon_id])
    progress = db.relationship('SectionProgress', backref='purchase', lazy='dynamic')

    def __repr__(self):
        return f'<Purchase {self.email} – {self.status}>'


class AdminUser(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<AdminUser {self.email}>'


class EmailCapture(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    source = db.Column(db.String(50), default='landing')  # landing / popup
    free_chapter_sent = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<EmailCapture {self.email}>'


class Coupon(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(32), unique=True, nullable=False)
    discount_type = db.Column(db.String(10), nullable=False)  # percent / fixed
    discount_value = db.Column(db.Float, nullable=False)
    max_uses = db.Column(db.Integer, nullable=True)  # None = unlimited
    use_count = db.Column(db.Integer, default=0)
    active = db.Column(db.Boolean, default=True)
    expires_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def is_valid(self):
        if not self.active:
            return False, 'Coupon is inactive.'
        if self.max_uses is not None and self.use_count >= self.max_uses:
            return False, 'Coupon has reached its usage limit.'
        if self.expires_at and datetime.now(timezone.utc) > self.expires_at.replace(tzinfo=timezone.utc):
            return False, 'Coupon has expired.'
        return True, None

    def apply(self, amount):
        if self.discount_type == 'percent':
            return round(max(0, amount * (1 - self.discount_value / 100)), 2)
        else:  # fixed
            return round(max(0, amount - self.discount_value), 2)

    def __repr__(self):
        return f'<Coupon {self.code}>'


class SectionProgress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    purchase_id = db.Column(db.Integer, db.ForeignKey('purchase.id'), nullable=False)
    slug = db.Column(db.String(64), nullable=False)
    visited_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (db.UniqueConstraint('purchase_id', 'slug', name='uq_progress_purchase_slug'),)

    def __repr__(self):
        return f'<SectionProgress {self.purchase_id} – {self.slug}>'


class Changelog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    body = db.Column(db.Text, nullable=False)
    published_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<Changelog {self.title}>'


class Testimonial(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(255), default='')
    body = db.Column(db.Text, nullable=False)
    approved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<Testimonial {self.name}>'


class Referral(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    purchase_id = db.Column(db.Integer, db.ForeignKey('purchase.id'), nullable=False)
    code = db.Column(db.String(32), unique=True, nullable=False,
                     default=lambda: uuid.uuid4().hex[:8].upper())
    conversions = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    referrer = db.relationship('Purchase', backref='referral', foreign_keys=[purchase_id])

    def __repr__(self):
        return f'<Referral {self.code} – {self.conversions} conversions>'
