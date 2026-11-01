"""Pacific Fair hoarding quotation generator (BSG rate card 25-26).
Usage: python3 quote_gen.py <job.json> [out.pdf]
Optional job.json keys: quote_no, quote_date, extra_doors, extra_doors_after, passage_sets, kiosk, valid_days, extra_lines [{desc,qty,unit,rate(null=POA)}], price_notes, terms_notes, scope.
"""
import json, sys, os, math, datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                                Image, PageBreak, KeepTogether)

HERE = os.path.dirname(os.path.abspath(__file__))
ORANGE = colors.HexColor("#F39200"); GREY = colors.HexColor("#4D4D4D"); LIGHT = colors.HexColor("#F4F4F4")

BANDS = [(2.4, 220.0, "Up to 2.4 m high"), (3.6, 280.0, "Up to 3.6 m high"),
         (4.2, 320.0, "Up to 4.2 m high"), (4.8, 330.0, "Up to 4.8 m high"),
         (6.0, 450.0, "Up to 6.0 m high")]
KIOSK = (1.2, 115.0, "1.2 m high kiosk")
MIN_LM_KIOSK, MIN_LM = 15.0, 10.0
GST = 0.10
DOORS_DURING, DOORS_AFTER, PASSAGE = 400.0, 800.0, 50.0
RATE_CARD = "BSG Commercial Internal Hoarding Schedule of Rates for GPT - Pacific Fair 25-26"


def money(v): return f"${v:,.2f}"


def faces(job):
    if "faces" in job:
        return [(f["name"].capitalize(), f["len"]) for f in job["faces"]]
    r = job["return"]
    return [("Left return", r), ("Front", job["front"]), ("Right return", job.get("right_return", r))]


def band(job):
    h = job["height"]
    if job.get("kiosk") and h <= KIOSK[0] + 1e-9:
        return KIOSK
    for b in BANDS:
        if h <= b[0] + 1e-9:
            return b
    raise SystemExit(f"Height {h} m is over 6.0 m: price on application (POA), quote by hand.")


def compute(job):
    fs = faces(job)
    run = round(sum(l for _, l in fs), 3)
    top, rate, label = band(job)
    minimum = MIN_LM_KIOSK if label == KIOSK[2] else MIN_LM
    charged = max(run, minimum)
    lines = [(f"Titan hoarding, 16 mm white melamine with taped joints, {label.lower()}",
              charged, "lm", rate, round(charged * rate, 2))]
    for key, price, text in [("extra_doors", DOORS_DURING, "Additional set of double doors (during installation)"),
                             ("extra_doors_after", DOORS_AFTER, "Additional set of double doors (after installation)"),
                             ("passage_sets", PASSAGE, "Passage set in lieu of hasp & staple")]:
        n = job.get(key, 0)
        if n:
            lines.append((text, n, "set", price, round(n * price, 2)))
    for x in job.get("extra_lines", []):
        r = x.get("rate")
        lines.append((x["desc"], x.get("qty", 1), x.get("unit", "item"), r,
                      None if r is None else round(x.get("qty", 1) * r, 2)))
    sub = round(sum(l[4] for l in lines if l[4] is not None), 2)
    gst = round(sub * GST, 2)
    return dict(faces=fs, run=run, band_top=top, rate=rate, label=label, minimum=minimum,
                charged=charged, lines=lines, sub=sub, gst=gst, total=round(sub + gst, 2))


def build(job, out):
    q = compute(job)
    ss = getSampleStyleSheet()
    body = ParagraphStyle("b", parent=ss["Normal"], fontName="Helvetica", fontSize=9, leading=12)
    small = ParagraphStyle("s", parent=body, fontSize=7.5, leading=9.5, textColor=GREY)
    h2 = ParagraphStyle("h2", parent=body, fontName="Helvetica-Bold", fontSize=11, leading=14,
                        textColor=ORANGE, spaceBefore=8, spaceAfter=4)
    bullet = ParagraphStyle("bl", parent=body, leftIndent=10, bulletIndent=0)
    cell = ParagraphStyle("c", parent=body, fontSize=8.5, leading=10.5)

    today = datetime.date.today()
    qdate = job.get("quote_date") or today.strftime("%d/%m/%Y")
    d = datetime.datetime.strptime(qdate, "%d/%m/%Y").date()
    valid = (d + datetime.timedelta(days=job.get("valid_days", 30))).strftime("%d/%m/%Y")
    qno = job.get("quote_no") or f"PF-{job['prefix'].upper()}-{d.strftime('%y%m%d')}"
    title = job.get("title", job["name"])
    h_mm = int(round(job["height"] * 1000))

    S = []
    head = Table([[Image(os.path.join(HERE, "bsg_logo.png"), width=80*mm, height=80*mm*79/354),
                   Paragraph("QLD: Unit 4, 37 Township Drive, Burleigh Heads QLD 4220<br/>"
                             "NSW: 2 Cente Place, Wetherill Park NSW 2164<br/>"
                             "Phone 1300 734 557 &nbsp; hoardings@bsgcommercial.com.au<br/>"
                             "bsgcommercial.com.au &nbsp; ABN 52 152 840 956",
                             ParagraphStyle("r", parent=small, alignment=2))]],
                 colWidths=[90*mm, 90*mm])
    head.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    S += [head, Spacer(1, 6),
          Table([[""]], colWidths=[180*mm], rowHeights=[2], style=[("BACKGROUND", (0, 0), (-1, -1), ORANGE)]),
          Spacer(1, 8),
          Paragraph("QUOTATION - Titan " + ("External" if job.get("external") else "Internal") + " Hoarding", ParagraphStyle("t", parent=body, fontName="Helvetica-Bold",
                                                                          fontSize=16, leading=20)),
          Spacer(1, 6)]
    info = [[Paragraph("<b>To</b>", cell), Paragraph("GPT - Pacific Fair Shopping Centre<br/>Centre Management", cell),
             Paragraph("<b>Quote no.</b>", cell), Paragraph(qno, cell)],
            [Paragraph("<b>Project</b>", cell), Paragraph(f"{title}<br/>Pacific Fair, Broadbeach QLD", cell),
             Paragraph("<b>Date</b>", cell), Paragraph(qdate, cell)],
            [Paragraph("<b>Scope</b>", cell), Paragraph(job.get("scope", "Supply, install and remove a free-standing hoarding "
                                                         "across the shopfront during the fit-out"), cell),
             Paragraph("<b>Valid until</b>", cell), Paragraph(valid, cell)]]
    t = Table(info, colWidths=[22*mm, 90*mm, 25*mm, 43*mm])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("BACKGROUND", (0, 0), (0, -1), LIGHT),
                           ("BACKGROUND", (2, 0), (2, -1), LIGHT), ("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey)]))
    S += [t]

    # dimensions
    S.append(Paragraph("1. Hoarding size", h2))
    rows = [["Section", "Length (mm)"]] + [[n, f"{int(round(l*1000)):,}"] for n, l in q["faces"]]
    rows += [["Total hoarding run", f"{int(round(q['run']*1000)):,}"], ["Hoarding height", f"{h_mm:,}"]]
    t = Table(rows, colWidths=[90*mm, 40*mm])
    t.setStyle(TableStyle([("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8.5), ("FONT", (0, 1), (-1, -1), "Helvetica", 8.5),
                           ("BACKGROUND", (0, 0), (-1, 0), GREY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                           ("FONT", (0, -2), (-1, -1), "Helvetica-Bold", 8.5), ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                           ("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey)]))
    S.append(t)

    # price
    S.append(Paragraph("2. Price", h2))
    rows = [["Description", "Qty", "Unit", "Rate (ex GST)", "Amount (ex GST)"]]
    for desc, n, u, r, a in q["lines"]:
        rows.append([Paragraph(desc, cell), f"{n:g}", u, "POA" if r is None else money(r),
                     "POA" if a is None else money(a)])
    nl = len(rows)
    rows += [["", "", "", "Subtotal (ex GST)", money(q["sub"])], ["", "", "", "GST 10%", money(q["gst"])],
             ["", "", "", "TOTAL (inc GST)", money(q["total"])]]
    t = Table(rows, colWidths=[88*mm, 14*mm, 12*mm, 32*mm, 34*mm])
    t.setStyle(TableStyle([("FONT", (0, 0), (-1, -1), "Helvetica", 8.5), ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8.5),
                           ("BACKGROUND", (0, 0), (-1, 0), GREY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                           ("ALIGN", (1, 0), (-1, -1), "RIGHT"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                           ("GRID", (0, 0), (-1, nl - 1), 0.4, colors.lightgrey),
                           ("FONT", (3, nl), (-1, -1), "Helvetica-Bold", 8.5),
                           ("BACKGROUND", (3, -1), (-1, -1), ORANGE), ("TEXTCOLOR", (3, -1), (-1, -1), colors.white),
                           ("LINEBELOW", (3, nl), (-1, -2), 0.4, colors.lightgrey)]))
    S.append(t)

    # explanation
    S.append(Paragraph("3. How this price is worked out", h2))
    run_mm = int(round(q["run"] * 1000))
    exp = [f"Pacific Fair hoardings are charged per lineal metre (lm) under the agreed {RATE_CARD}.",
           f"The lineal metres are the <b>full hoarding run</b>, which includes the returns and sides as "
           f"well as the front: {' + '.join(f'{int(round(l*1000)):,}' for _, l in q['faces'])} = {run_mm:,} mm "
           f"= {q['run']:g} lm.",
           f"The hoarding is {h_mm:,} mm high, so it falls in the <b>{q['label'].lower()}</b> band at "
           f"<b>{money(q['rate'])} per lm</b> (ex GST). The rate rises with height because taller hoardings need "
           f"more melamine, more counterweights per upright and more labour to install safely."]
    if q["charged"] > q["run"]:
        exp.append(f"The run is shorter than the {q['minimum']:g} lm minimum charge for this hoarding type, "
                   f"so {q['minimum']:g} lm is charged.")
    else:
        exp.append(f"The run is above the {q['minimum']:g} lm minimum charge, so the actual length is charged.")
    exp += job.get("price_notes", [])
    exp.append(f"{q['charged']:g} lm x {money(q['rate'])} = {money(q['lines'][0][4])} ex GST, plus GST at 10%.")
    S += [Paragraph(e, bullet, bulletText="•") for e in exp]

    S.append(Paragraph("4. What is included", h2))
    inc = ["Supply, delivery, installation and removal of the TITAN free-standing hoarding system.",
           "Structural engineering certification to AS4687 (pre-engineered certified hoarding).",
           "16 mm white melamine boards with white taped joints and black skirting tape along the bottom.",
           "One set of double doors, opening 2340 mm high x 1600 mm wide, with barrel bolt "
           "(deadbolt lock provided by Pacific Fair).",
           "Free-standing installation: nothing is fixed to the centre's finishes, so there is no damage and "
           "no make-good work when the hoarding is removed.",
           "Hoarding drawing for approval (attached).",
           "Hoarding on site for up to 6 months before further charges apply."]
    S += [Paragraph(e, bullet, bulletText="•") for e in inc]

    ex = [["Additional set of double doors, during installation", "$400.00 per set"],
          ["Additional set of double doors, after installation", "$800.00 per set"],
          ["Passage set in lieu of hasp & staple", "$50.00 per set"],
          ["Post-installation modification (2 men x 4 hrs minimum, materials extra)", "$800.00"],
          ["General modification rate (minimum 2 installers x 4 hrs)", "$100.00 per hour"],
          ["Cancellation after 2 pm cut-off", "$200.00"],
          ["Cancellation after 5 pm (hoarding dispatched)", "$900.00"],
          ["Cancellation with the team on site", "Full cost of hoarding"],
          ["Public holiday work, oversized transport, wind-rated hoardings", "POA"]]
    t = Table([[Paragraph(a, cell), b] for a, b in ex], colWidths=[130*mm, 50*mm])
    t.setStyle(TableStyle([("FONT", (0, 0), (-1, -1), "Helvetica", 8.5), ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                           ("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    S.append(KeepTogether([Paragraph("5. Optional extras and other charges (ex GST)", h2), t]))

    notes = ["Installation, modification and removal need final confirmation by 2 pm for work that night "
             "(2 pm Friday for Friday, Saturday or Sunday), and at least 72 hours' notice for installation and lockout.",
             "All modifications must be done by BSG Commercial to keep the hoarding compliant.",
             "Lost or stolen materials will be charged. The hoarding must not be used as a storage room or "
             "temporary wall; rental charges apply.",
             "Measurements on the drawing are for hoarding construction only. Allow 10% waste for any graphics, "
             "which must use low-residue glue only.",
             "A scissor lift is not included for hoardings over 4.2 m; Pacific Fair to supply its in-house EWP, "
             "otherwise hire is charged.",
             "Hoardings are for internal shopfront fit-out works only."] + job.get("terms_notes", [])
    S.append(KeepTogether([Paragraph("6. Terms and important information", h2)] +
                          [Paragraph(e, bullet, bulletText="•") for e in notes]))

    S.append(KeepTogether([Paragraph("7. Acceptance", h2),
        Paragraph("To proceed, please sign and return this quotation with the approved drawing. "
                  "BSG requires drawing sign-off before installation.", body), Spacer(1, 14),
        Table([["Name: ______________________________", "Signature: __________________________"],
               ["Company: GPT - Pacific Fair", "Date: ____ / ____ / ________"]],
              colWidths=[90*mm, 90*mm], rowHeights=[18, 18],
              style=[("FONT", (0, 0), (-1, -1), "Helvetica", 9)])]))

    sheet = os.path.join(job["dir"], f"{job['prefix']}_hoarding_sheet.png")
    if os.path.exists(sheet):
        from PIL import Image as PI
        w, h = PI.open(sheet).size
        W = 180*mm; H = W * h / w
        if H > 230*mm: H = 230*mm; W = H * w / h
        S += [PageBreak(), Paragraph("Attachment: hoarding plan and elevation (sizes in mm)", h2), Image(sheet, W, H)]

    def footer(c, doc):
        c.saveState(); c.setFont("Helvetica", 7); c.setFillColor(GREY)
        c.drawString(15*mm, 10*mm, f"BSG Commercial - Quotation {qno} - {title}")
        c.drawRightString(195*mm, 10*mm, f"Page {doc.page}"); c.restoreState()

    SimpleDocTemplate(out, pagesize=A4, leftMargin=15*mm, rightMargin=15*mm, topMargin=12*mm,
                      bottomMargin=16*mm, title=f"Quotation {qno}").build(S, onFirstPage=footer, onLaterPages=footer)
    return q, qno


if __name__ == "__main__":
    job = json.load(open(sys.argv[1]))
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(job["dir"], f"{job['prefix']}_Quotation.pdf")
    q, qno = build(job, out)
    print(qno, out, q["run"], q["label"], q["rate"], q["sub"], q["gst"], q["total"])
