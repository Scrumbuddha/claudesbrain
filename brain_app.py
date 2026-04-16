import math
from datetime import datetime, timezone

from flask import Blueprint, render_template, abort
from models import db, Purchase, SectionProgress, Changelog, Referral
from sections import SECTIONS

brain_app_bp = Blueprint('brain_app', __name__, url_prefix='/app')

SECTION_MAP = {s['slug']: s for s in SECTIONS}

CX, CY, R_PETAL = 340, 340, 265


def _petal_positions():
    """Pre-compute (x, y) for each section petal in the SVG."""
    positions = []
    n = len(SECTIONS)
    for i, s in enumerate(SECTIONS):
        angle_deg = (i * 360 / n) - 90
        angle_rad = math.radians(angle_deg)
        px = CX + R_PETAL * math.cos(angle_rad)
        py = CY + R_PETAL * math.sin(angle_rad)
        positions.append({**s, 'px': round(px, 1), 'py': round(py, 1)})
    return positions


def _get_purchase(token):
    p = Purchase.query.filter_by(download_token=token).first()
    if not p or p.status != 'confirmed':
        return None
    return p


def _track_progress(purchase, slug):
    """Record a section visit if not already tracked."""
    existing = SectionProgress.query.filter_by(
        purchase_id=purchase.id, slug=slug
    ).first()
    if not existing:
        sp = SectionProgress(purchase_id=purchase.id, slug=slug)
        db.session.add(sp)
        db.session.commit()


def _visited_slugs(purchase):
    """Return set of visited slugs for a purchase."""
    rows = SectionProgress.query.filter_by(purchase_id=purchase.id).all()
    return {r.slug for r in rows}


def _changelog_badge(purchase):
    """Return newest changelog entry if published after last visit, else None."""
    latest = Changelog.query.order_by(Changelog.published_at.desc()).first()
    if not latest:
        return None
    # Show badge if user hasn't visited any section since the last changelog entry
    last_visit = SectionProgress.query.filter_by(purchase_id=purchase.id)\
        .order_by(SectionProgress.visited_at.desc()).first()
    if not last_visit:
        return latest
    pub = latest.published_at
    if pub.tzinfo is None:
        pub = pub.replace(tzinfo=timezone.utc)
    vis = last_visit.visited_at
    if vis.tzinfo is None:
        vis = vis.replace(tzinfo=timezone.utc)
    return latest if pub > vis else None


@brain_app_bp.route('/demo')
def hub_demo():
    return render_template('app/hub.html', token='demo', purchase=None,
                           sections=SECTIONS, petals=_petal_positions(),
                           cx=CX, cy=CY, visited=set(), changelog_badge=None,
                           progress_pct=0, referral_code=None)


@brain_app_bp.route('/demo/section/<slug>')
def section_demo(slug):
    if slug not in SECTION_MAP:
        abort(404)
    slugs = [s['slug'] for s in SECTIONS]
    idx = slugs.index(slug)
    prev_section = SECTIONS[idx - 1] if idx > 0 else None
    next_section = SECTIONS[idx + 1] if idx < len(SECTIONS) - 1 else None
    return render_template(
        'app/section.html',
        token='demo',
        purchase=None,
        section=SECTION_MAP[slug],
        sections=SECTIONS,
        prev_section=prev_section,
        next_section=next_section,
        current_idx=idx,
    )


@brain_app_bp.route('/<token>')
def hub(token):
    purchase = _get_purchase(token)
    if not purchase:
        abort(404)
    visited = _visited_slugs(purchase)
    progress_pct = round(len(visited) / len(SECTIONS) * 100)
    badge = _changelog_badge(purchase)
    referral = Referral.query.filter_by(purchase_id=purchase.id).first()
    if not referral:
        referral = Referral(purchase_id=purchase.id)
        db.session.add(referral)
        db.session.commit()
    return render_template('app/hub.html', token=token, purchase=purchase,
                           sections=SECTIONS, petals=_petal_positions(),
                           cx=CX, cy=CY, visited=visited,
                           progress_pct=progress_pct,
                           changelog_badge=badge,
                           referral_code=referral.code)


@brain_app_bp.route('/<token>/section/<slug>')
def section(token, slug):
    purchase = _get_purchase(token)
    if not purchase:
        abort(404)
    if slug not in SECTION_MAP:
        abort(404)

    _track_progress(purchase, slug)

    slugs = [s['slug'] for s in SECTIONS]
    idx = slugs.index(slug)
    prev_section = SECTIONS[idx - 1] if idx > 0 else None
    next_section = SECTIONS[idx + 1] if idx < len(SECTIONS) - 1 else None

    return render_template(
        'app/section.html',
        token=token,
        purchase=purchase,
        section=SECTION_MAP[slug],
        sections=SECTIONS,
        prev_section=prev_section,
        next_section=next_section,
        current_idx=idx,
    )
