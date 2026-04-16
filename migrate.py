"""
One-shot migration: add new columns to purchase table and create new tables.
Run once: python migrate.py
"""
import os
from app import create_app
from models import db

app = create_app()

with app.app_context():
    with db.engine.connect() as conn:
        # Add new columns to purchase if they don't exist
        migrations = [
            "ALTER TABLE purchase ADD COLUMN IF NOT EXISTS tier VARCHAR(20) DEFAULT 'standard'",
            "ALTER TABLE purchase ADD COLUMN IF NOT EXISTS coupon_id INTEGER REFERENCES coupon(id)",
            "ALTER TABLE purchase ADD COLUMN IF NOT EXISTS referral_code_used VARCHAR(32)",
            "ALTER TABLE purchase ADD COLUMN IF NOT EXISTS gift_recipient_email VARCHAR(255)",
        ]
        for sql in migrations:
            try:
                conn.execute(db.text(sql))
                print(f'OK: {sql[:60]}...')
            except Exception as e:
                print(f'SKIP ({e}): {sql[:60]}...')
        conn.commit()

    # create_all creates any missing tables (new models)
    db.create_all()
    print('All new tables created.')
    print('Migration complete.')
