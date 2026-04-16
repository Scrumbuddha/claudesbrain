"""
Build Pro Bundle PDFs from Markdown source files using ReportLab.
Run from the pro-bundle/ directory: python build_pdfs.py
"""
import os
import re
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, black, white
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Preformatted,
    HRFlowable, Table, TableStyle, PageBreak, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

FILES = [
    ("01-prompt-library.md",       "Claude's Brain — Prompt Library.pdf"),
    ("02-claude-md-starter-kit.md","Claude's Brain — CLAUDE.md Starter Kit.pdf"),
    ("03-slash-command-library.md","Claude's Brain — Slash Command Library.pdf"),
    ("04-sub-agent-templates.md",  "Claude's Brain — Sub-Agent Templates.pdf"),
    ("chapter1-free.md",           "claude-brain-chapter1.pdf"),
]

# Brand colours
GOLD     = HexColor("#C9A227")
DARK_BG  = HexColor("#080810")
DARK_MID = HexColor("#1a1a2e")
MUTED    = HexColor("#7a7a9a")
LIGHT_BG = HexColor("#f4f4f8")
BORDER   = HexColor("#d8d8e8")
WHITE    = white
CODE_FG  = HexColor("#2a2a4a")


def make_styles():
    styles = getSampleStyleSheet()

    def add(name, **kw):
        styles.add(ParagraphStyle(name=name, **kw))

    add("BrandH1",
        fontName="Helvetica-Bold", fontSize=26, leading=30,
        textColor=DARK_BG, spaceBefore=0, spaceAfter=6,
        borderPadding=(0, 0, 8, 0))

    add("Subtitle",
        fontName="Helvetica", fontSize=11, leading=16,
        textColor=MUTED, spaceAfter=24, fontStyle="italic")

    add("H2",
        fontName="Helvetica-Bold", fontSize=14, leading=18,
        textColor=DARK_BG, spaceBefore=22, spaceAfter=6)

    add("H3",
        fontName="Helvetica-Bold", fontSize=11, leading=14,
        textColor=DARK_MID, spaceBefore=14, spaceAfter=4)

    add("Body",
        fontName="Helvetica", fontSize=10, leading=15,
        textColor=DARK_MID, spaceBefore=0, spaceAfter=6)

    add("BulletItem",
        fontName="Helvetica", fontSize=10, leading=14,
        textColor=DARK_MID, leftIndent=14, firstLineIndent=-10,
        spaceBefore=2, spaceAfter=2)

    add("CodeBlock",
        fontName="Courier", fontSize=8, leading=12,
        textColor=CODE_FG, backColor=LIGHT_BG,
        borderColor=BORDER, borderWidth=0,
        leftIndent=0, spaceBefore=6, spaceAfter=10)

    add("Footer",
        fontName="Helvetica", fontSize=8,
        textColor=MUTED, alignment=TA_CENTER)

    add("HR_label",
        fontName="Helvetica", fontSize=8,
        textColor=MUTED, spaceAfter=4)

    return styles


def header_footer(canvas, doc):
    canvas.saveState()
    w, h = LETTER
    # Top gold bar
    canvas.setFillColor(GOLD)
    canvas.rect(0.75*inch, h - 0.55*inch, w - 1.5*inch, 2, fill=1, stroke=0)
    # Header brand text
    canvas.setFont("Helvetica-Bold", 8)
    canvas.setFillColor(DARK_BG)
    canvas.drawString(0.75*inch, h - 0.48*inch, "BUILDING CLAUDE'S BRAIN")
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawRightString(w - 0.75*inch, h - 0.48*inch, doc.title)
    # Bottom rule
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(0.75*inch, 0.65*inch, w - 0.75*inch, 0.65*inch)
    # Page number
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawCentredString(w / 2, 0.45*inch, f"Page {doc.page}")
    canvas.drawRightString(w - 0.75*inch, 0.45*inch, "claudesbrain.com")
    canvas.restoreState()


def parse_markdown(md_text, styles):
    """Convert markdown to a list of ReportLab flowables."""
    flowables = []
    lines = md_text.split('\n')
    i = 0
    in_code = False
    code_buffer = []
    code_lang = ""
    first_h1 = True

    def wrap_code_line(line, max_chars=90):
        """Wrap a single code line at max_chars, preserving leading indent."""
        if len(line) <= max_chars:
            return [line]
        indent = len(line) - len(line.lstrip())
        prefix = ' ' * indent + '  '  # continuation indent
        out = []
        while len(line) > max_chars:
            # Try to break at a space near the limit
            break_at = line.rfind(' ', indent, max_chars)
            if break_at <= indent:
                break_at = max_chars
            out.append(line[:break_at])
            line = prefix + line[break_at:].lstrip()
        out.append(line)
        return out

    def flush_code():
        nonlocal code_buffer
        if not code_buffer:
            return
        # Wrap long lines so they don't overflow the page
        wrapped = []
        for line in code_buffer:
            wrapped.extend(wrap_code_line(line))
        # Split large code blocks into ~40-line chunks so they fit on a page
        CHUNK = 40
        chunks = [wrapped[j:j+CHUNK] for j in range(0, len(wrapped), CHUNK)]
        flowables.append(Spacer(1, 4))
        for chunk in chunks:
            text = '\n'.join(chunk)
            code_para = Preformatted(text, styles["CodeBlock"])
            t = Table([[code_para]], colWidths=[6.5*inch])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,-1), LIGHT_BG),
                ("LINECOLOR",  (0,0), (-1,-1), BORDER),
                ("BOX",        (0,0), (-1,-1), 0.5, BORDER),
                ("LINEBEFORE",  (0,0), (0,-1), 3, GOLD),
                ("LEFTPADDING",  (0,0), (-1,-1), 10),
                ("RIGHTPADDING", (0,0), (-1,-1), 10),
                ("TOPPADDING",   (0,0), (-1,-1), 8),
                ("BOTTOMPADDING",(0,0), (-1,-1), 8),
            ]))
            flowables.append(t)
            flowables.append(Spacer(1, 4))
        flowables.append(Spacer(1, 2))
        code_buffer = []

    def clean_inline(text):
        # bold
        text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
        # italic / em — but skip standalone * bullets
        text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<i>\1</i>', text)
        # inline code
        text = re.sub(r'`([^`]+)`', lambda m: f'<font name="Courier" color="#C9A227">{m.group(1)}</font>', text)
        # escape bare & < > that aren't already tags
        text = re.sub(r'&(?!amp;|lt;|gt;|#)', '&amp;', text)
        return text

    while i < len(lines):
        line = lines[i]

        # Fenced code block
        if line.startswith("```"):
            if not in_code:
                in_code = True
                code_lang = line[3:].strip()
            else:
                in_code = False
                flush_code()
            i += 1
            continue

        if in_code:
            code_buffer.append(line)
            i += 1
            continue

        # H1
        if line.startswith("# "):
            text = line[2:].strip()
            if first_h1:
                flowables.append(Spacer(1, 6))
                flowables.append(Paragraph(text, styles["BrandH1"]))
                flowables.append(HRFlowable(width="100%", thickness=3,
                                            color=GOLD, spaceAfter=4))
                first_h1 = False
            else:
                flowables.append(PageBreak())
                flowables.append(Paragraph(text, styles["BrandH1"]))
                flowables.append(HRFlowable(width="100%", thickness=3,
                                            color=GOLD, spaceAfter=4))
            i += 1
            # subtitle (### immediately after h1)
            if i < len(lines) and lines[i].startswith("### "):
                flowables.append(Paragraph(lines[i][4:].strip(), styles["Subtitle"]))
                i += 1
            continue

        # H2
        if line.startswith("## "):
            text = clean_inline(line[3:].strip())
            flowables.append(KeepTogether([
                HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceBefore=16, spaceAfter=0),
                Paragraph(text, styles["H2"]),
            ]))
            i += 1
            continue

        # H3
        if line.startswith("### "):
            text = clean_inline(line[4:].strip())
            flowables.append(Paragraph(text, styles["H3"]))
            i += 1
            continue

        # HR
        if line.strip() == "---":
            flowables.append(HRFlowable(width="100%", thickness=0.5,
                                        color=BORDER, spaceBefore=10, spaceAfter=10))
            i += 1
            continue

        # Bullet list
        if line.startswith("- ") or line.startswith("* "):
            text = clean_inline(line[2:].strip())
            flowables.append(Paragraph(f"&#8226;&nbsp;&nbsp;{text}", styles["BulletItem"]))
            i += 1
            continue

        # Numbered list
        m = re.match(r'^(\d+)\.\s+(.*)', line)
        if m:
            text = clean_inline(m.group(2))
            flowables.append(Paragraph(f"<b>{m.group(1)}.</b>&nbsp;&nbsp;{text}", styles["BulletItem"]))
            i += 1
            continue

        # Table (pipe-delimited)
        if "|" in line and line.strip().startswith("|"):
            table_lines = []
            while i < len(lines) and "|" in lines[i] and lines[i].strip().startswith("|"):
                table_lines.append(lines[i])
                i += 1
            # Parse rows, skip separator rows (---|---)
            rows = []
            is_header = True
            for tl in table_lines:
                cells = [c.strip() for c in tl.strip().strip("|").split("|")]
                if re.match(r'^[\-\s\|]+$', tl):
                    continue
                style_to_use = styles["H3"] if is_header else styles["Body"]
                rows.append([Paragraph(clean_inline(c), style_to_use) for c in cells])
                is_header = False
            if rows:
                col_count = max(len(r) for r in rows)
                col_w = 6.5*inch / col_count
                t = Table(rows, colWidths=[col_w]*col_count)
                ts = TableStyle([
                    ("BACKGROUND",   (0,0), (-1,0), GOLD),
                    ("TEXTCOLOR",    (0,0), (-1,0), DARK_BG),
                    ("FONTNAME",     (0,0), (-1,0), "Helvetica-Bold"),
                    ("FONTSIZE",     (0,0), (-1,-1), 9),
                    ("ROWBACKGROUNDS",(0,1),(-1,-1), [WHITE, LIGHT_BG]),
                    ("GRID",         (0,0), (-1,-1), 0.5, BORDER),
                    ("VALIGN",       (0,0), (-1,-1), "TOP"),
                    ("LEFTPADDING",  (0,0), (-1,-1), 8),
                    ("RIGHTPADDING", (0,0), (-1,-1), 8),
                    ("TOPPADDING",   (0,0), (-1,-1), 5),
                    ("BOTTOMPADDING",(0,0), (-1,-1), 5),
                ])
                t.setStyle(ts)
                flowables.append(Spacer(1, 6))
                flowables.append(t)
                flowables.append(Spacer(1, 8))
            continue

        # Blank line
        if line.strip() == "":
            flowables.append(Spacer(1, 4))
            i += 1
            continue

        # Normal paragraph
        text = clean_inline(line.strip())
        if text:
            flowables.append(Paragraph(text, styles["Body"]))
        i += 1

    if in_code and code_buffer:
        flush_code()

    return flowables


def build_pdf(md_filename, pdf_filename, doc_title):
    md_path = os.path.join(BASE_DIR, md_filename)
    pdf_path = os.path.join(BASE_DIR, pdf_filename)

    with open(md_path, 'r', encoding='utf-8') as f:
        md_text = f.read()

    styles = make_styles()
    flowables = parse_markdown(md_text, styles)

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=LETTER,
        leftMargin=0.75*inch,
        rightMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch,
        title=doc_title,
        author="St. Pete AI",
        subject="Building Claude's Brain Pro Bundle",
    )
    doc.title = doc_title

    doc.build(flowables, onFirstPage=header_footer, onLaterPages=header_footer)
    size_kb = os.path.getsize(pdf_path) // 1024
    print(f"  OK  {pdf_filename} ({size_kb} KB)")


if __name__ == '__main__':
    print("Building Pro Bundle PDFs...\n")
    titles = [
        "Prompt Library",
        "CLAUDE.md Starter Kit",
        "Slash Command Library",
        "Sub-Agent Templates",
        "Chapter 1: CLAUDE.md",
    ]
    for (md_file, pdf_file), title in zip(FILES, titles):
        build_pdf(md_file, pdf_file, title)
    print("\nDone. 5 PDFs in pro-bundle/")
