#!/usr/bin/env python3
"""Render the daily emerging-tech briefing JSON into a 2-3 page PDF.

Usage:  python3 build_pdf.py briefing.json OUT.pdf
Prints the page count; exits 2 if the result is outside 2-3 pages so the
caller can trim or expand the content and re-run.

Input schema (all strings plain text; keep them tight):
{
  "date": "Sunday, 15 November 2026",
  "headline": "One-line thesis for the day",
  "summary": "3-5 sentence executive summary",
  "key_numbers": [{"value": "23/36", "label": "YC launches tagged AI"}, ...],   # 3-4 items
  "signals": [                                                                # 4-6 items
    {"title": "...", "momentum": "Accelerating|Emerging|Watch|Cooling",
     "what": "what is happening", "why": "why it matters / so-what",
     "evidence": [{"label": "HN 1295 pts", "text": "Starship caught", "url": "https://..."}]}
  ],
  "yc_watch": [{"company": "...", "batch": "F26", "pitch": "...", "take": "..."}],  # 5-8 rows
  "hn_pulse": [{"title": "...", "points": 1295, "comments": 871, "url": "...", "note": "..."}],  # 6-10 rows
  "watch_next": ["...", "..."],                                               # 3-5 bullets
  "sources_note": "Hacker News (Algolia API) ..., YC Launches ..."
}
"""
import json
import sys
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (BaseDocTemplate, Frame, KeepTogether, PageTemplate,
                                Paragraph, Spacer, Table, TableStyle)

INK = colors.HexColor("#1B1F24")
MUTED = colors.HexColor("#5B6470")
ACCENT = colors.HexColor("#E8590C")       # HN / YC orange
ACCENT_SOFT = colors.HexColor("#FFF1E8")
RULE = colors.HexColor("#E3E6EA")
BAND = colors.HexColor("#14171C")
MOMENTUM = {
    "accelerating": colors.HexColor("#C2410C"),
    "emerging": colors.HexColor("#1D4ED8"),
    "watch": colors.HexColor("#6D28D9"),
    "cooling": colors.HexColor("#64748B"),
}

PAGE_W, PAGE_H = A4
MARGIN = 16 * mm


def S(name, **kw):
    base = dict(fontName="Helvetica", fontSize=9.2, leading=12.6, textColor=INK, alignment=TA_LEFT)
    base.update(kw)
    return ParagraphStyle(name, **base)


ST = {
    "headline": S("headline", fontName="Helvetica-Bold", fontSize=17, leading=21),
    "summary": S("summary", fontSize=10, leading=14.2),
    "h2": S("h2", fontName="Helvetica-Bold", fontSize=11.5, leading=14, textColor=ACCENT,
            spaceBefore=8, spaceAfter=4),
    "sig_title": S("sig_title", fontName="Helvetica-Bold", fontSize=10.6, leading=13.5),
    "body": S("body"),
    "small": S("small", fontSize=8, leading=10.4, textColor=MUTED),
    "cell": S("cell", fontSize=8.4, leading=10.8),
    "cell_b": S("cell_b", fontName="Helvetica-Bold", fontSize=8.4, leading=10.8),
    "th": S("th", fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=colors.white),
    "kv": S("kv", fontName="Helvetica-Bold", fontSize=16, leading=18, textColor=ACCENT),
    "kl": S("kl", fontSize=7.8, leading=9.6, textColor=MUTED),
    "bullet": S("bullet", leftIndent=10, bulletIndent=0),
}


def t(s):
    return escape(str(s or ""))


def link(text, url):
    if not url:
        return t(text)
    return f'<link href="{escape(url, {chr(34): "&quot;"})}" color="#1D4ED8">{t(text)}</link>'


def on_page(date_str):
    def draw(c, doc):
        c.saveState()
        if doc.page == 1:
            c.setFillColor(BAND)
            c.rect(0, PAGE_H - 30 * mm, PAGE_W, 30 * mm, fill=1, stroke=0)
            c.setFillColor(ACCENT)
            c.rect(0, PAGE_H - 30 * mm, PAGE_W, 1.4 * mm, fill=1, stroke=0)
            c.setFillColor(colors.white)
            c.setFont("Helvetica-Bold", 19)
            c.drawString(MARGIN, PAGE_H - 15 * mm, "Emerging Tech Daily")
            c.setFont("Helvetica", 9.5)
            c.setFillColor(colors.HexColor("#C9CED6"))
            c.drawString(MARGIN, PAGE_H - 22 * mm, "Signals from Hacker News and Y Combinator")
            c.setFont("Helvetica-Bold", 9.5)
            c.setFillColor(colors.white)
            c.drawRightString(PAGE_W - MARGIN, PAGE_H - 15 * mm, date_str)
            c.setFont("Helvetica", 8.5)
            c.setFillColor(colors.HexColor("#C9CED6"))
            c.drawRightString(PAGE_W - MARGIN, PAGE_H - 22 * mm, "Morning briefing, 10:00 IST")
        else:
            c.setStrokeColor(RULE)
            c.setLineWidth(0.6)
            c.line(MARGIN, PAGE_H - 11 * mm, PAGE_W - MARGIN, PAGE_H - 11 * mm)
            c.setFont("Helvetica-Bold", 8)
            c.setFillColor(ACCENT)
            c.drawString(MARGIN, PAGE_H - 9 * mm, "EMERGING TECH DAILY")
            c.setFont("Helvetica", 8)
            c.setFillColor(MUTED)
            c.drawRightString(PAGE_W - MARGIN, PAGE_H - 9 * mm, date_str)
        c.setFont("Helvetica", 7.5)
        c.setFillColor(MUTED)
        c.drawRightString(PAGE_W - MARGIN, 9 * mm, f"Page {doc.page}")
        c.restoreState()
    return draw


def key_numbers(items):
    if not items:
        return []
    items = items[:4]
    cells = [[Paragraph(t(i["value"]), ST["kv"]), Paragraph(t(i["label"]), ST["kl"])] for i in items]
    inner = [Table([[c[0]], [c[1]]], colWidths=None,
                   style=[("LEFTPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                          ("TOPPADDING", (0, 0), (-1, -1), 0)]) for c in cells]
    w = (PAGE_W - 2 * MARGIN) / len(items)
    tbl = Table([inner], colWidths=[w] * len(items))
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), ACCENT_SOFT),
        ("LINEAFTER", (0, 0), (-2, -1), 0.6, colors.white),
        ("LEFTPADDING", (0, 0), (-1, -1), 9), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return [tbl, Spacer(1, 6)]


def signal_block(i, s):
    mom = (s.get("momentum") or "Emerging").strip()
    col = MOMENTUM.get(mom.lower(), MOMENTUM["emerging"])
    title = (f'<font color="{ACCENT.hexval().replace("0x", "#")}">{i}.</font> {t(s["title"])} '
             f'&nbsp;<font size="7.5" color="{col.hexval().replace("0x", "#")}">'
             f'<b>{t(mom.upper())}</b></font>')
    parts = [Paragraph(title, ST["sig_title"]), Spacer(1, 2),
             Paragraph(f"<b>What:</b> {t(s.get('what'))}", ST["body"]), Spacer(1, 1.5),
             Paragraph(f"<b>Why it matters:</b> {t(s.get('why'))}", ST["body"])]
    ev = s.get("evidence") or []
    if ev:
        evs = " &nbsp;·&nbsp; ".join(
            f'<b>{t(e.get("label"))}</b> {link(e.get("text"), e.get("url"))}' for e in ev)
        parts += [Spacer(1, 2), Paragraph(f"Evidence: {evs}", ST["small"])]
    # one row per paragraph so a signal can break across pages between rows
    rows = [[p] for p in parts if not isinstance(p, Spacer)]
    inner = Table(rows, colWidths=[PAGE_W - 2 * MARGIN - 3 * mm])
    inner.setStyle(TableStyle([
        ("LINEBEFORE", (0, 0), (0, -1), 2.2, col),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
        ("NOSPLIT", (0, 0), (0, 1)),
    ]))
    return [inner, Spacer(1, 7)]


def table(header, rows, widths):
    data = [[Paragraph(h, ST["th"]) for h in header]] + rows
    tbl = Table(data, colWidths=widths, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), BAND),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ("LINEBELOW", (0, 1), (-1, -1), 0.4, RULE),
    ]
    for r in range(2, len(data), 2):
        style.append(("BACKGROUND", (0, r), (-1, r), colors.HexColor("#F7F8FA")))
    tbl.setStyle(TableStyle(style))
    return tbl


def build(spec, out):
    doc = BaseDocTemplate(out, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN,
                          topMargin=16 * mm, bottomMargin=15 * mm,
                          title=f"Emerging Tech Daily - {spec.get('date', '')}",
                          author="Emerging Tech Daily")
    first = Frame(MARGIN, 15 * mm, PAGE_W - 2 * MARGIN, PAGE_H - 30 * mm - 6 * mm - 15 * mm, id="f1")
    rest = Frame(MARGIN, 15 * mm, PAGE_W - 2 * MARGIN, PAGE_H - 16 * mm - 15 * mm, id="f2")
    draw = on_page(spec.get("date", ""))
    doc.addPageTemplates([PageTemplate("first", [first], onPage=draw, autoNextPageTemplate="rest"),
                          PageTemplate("rest", [rest], onPage=draw)])
    W = PAGE_W - 2 * MARGIN
    f = [Paragraph(t(spec["headline"]), ST["headline"]), Spacer(1, 5),
         Paragraph(t(spec["summary"]), ST["summary"]), Spacer(1, 8)]
    f += key_numbers(spec.get("key_numbers"))

    f.append(Paragraph("TODAY'S EMERGING SIGNALS", ST["h2"]))
    for i, s in enumerate(spec.get("signals", []), 1):
        f.extend(signal_block(i, s))

    if spec.get("yc_watch"):
        head = Paragraph("Y COMBINATOR LAUNCH WATCH", ST["h2"])
        rows = [[Paragraph(f"<b>{link(r['company'], r.get('url'))}</b><br/>"
                           f"<font color='#5B6470' size='7.5'>{t(r.get('batch'))}</font>", ST["cell"]),
                 Paragraph(t(r.get("pitch")), ST["cell"]),
                 Paragraph(t(r.get("take")), ST["cell"])] for r in spec["yc_watch"]]
        # keep heading + table together so no orphaned rows dangle at a page foot
        f.append(KeepTogether([head, table(["Company", "What they're building", "Why it's a signal"],
                                           rows, [W * 0.2, W * 0.38, W * 0.42])]))
        f.append(Spacer(1, 6))

    if spec.get("hn_pulse"):
        head = Paragraph("HACKER NEWS PULSE (LAST 24H)", ST["h2"])
        rows = [[Paragraph(f"<b>{t(r.get('points'))}</b><br/>"
                           f"<font color='#5B6470' size='7.5'>{t(r.get('comments'))} cmts</font>", ST["cell"]),
                 Paragraph(link(r["title"], r.get("url")), ST["cell_b"]),
                 Paragraph(t(r.get("note")), ST["cell"])] for r in spec["hn_pulse"]]
        f.append(KeepTogether([head, table(["Pts", "Story", "Read-through"], rows,
                                           [W * 0.09, W * 0.40, W * 0.51])]))
        f.append(Spacer(1, 6))

    if spec.get("watch_next"):
        block = [Paragraph("WHAT TO WATCH NEXT", ST["h2"])]
        block += [Paragraph(t(b), ST["bullet"], bulletText="•") for b in spec["watch_next"]]
        f.append(KeepTogether(block))
        f.append(Spacer(1, 8))

    if spec.get("sources_note"):
        f.append(Paragraph(t(spec["sources_note"]), ST["small"]))

    doc.build(f)
    return doc.page


def main():
    if len(sys.argv) != 3:
        sys.exit("usage: build_pdf.py briefing.json OUT.pdf")
    spec = json.load(open(sys.argv[1]))
    pages = build(spec, sys.argv[2])
    print(f"wrote {sys.argv[2]}: {pages} pages")
    if not 2 <= pages <= 3:
        print("PAGE COUNT OUT OF RANGE (target 2-3): "
              + ("trim content" if pages > 3 else "add depth"), file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
