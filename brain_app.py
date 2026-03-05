import math
from flask import Blueprint, render_template, abort
from models import Purchase
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


@brain_app_bp.route('/demo')
def hub_demo():
    return render_template('app/hub.html', token='demo', purchase=None,
                           sections=SECTIONS, petals=_petal_positions(),
                           cx=CX, cy=CY)


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
    return render_template('app/hub.html', token=token, purchase=purchase,
                           sections=SECTIONS, petals=_petal_positions(),
                           cx=CX, cy=CY)


@brain_app_bp.route('/<token>/section/<slug>')
def section(token, slug):
    purchase = _get_purchase(token)
    if not purchase:
        abort(404)
    if slug not in SECTION_MAP:
        abort(404)

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
