"""BSG materials checklist, same layout as the paper form. Args: out.xlsx job front return height door_offset door_width (m)."""
import sys, math, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cutplan import plan
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
# Corner jobs: materials.py out.xlsx job.json  (uses the job's "faces")
from layout_gen import compute
out = sys.argv[1]
if sys.argv[2].endswith(".json"):
    import json; _p = json.load(open(sys.argv[2])); job = _p["name"]
    front, ret, H, doff, dw = _p["front"], _p["return"], _p["height"], _p["door_offset"], _p["door_width"]
else:
    job = sys.argv[2]; front, ret, H, doff, dw = map(float, sys.argv[3:8])
    _p = {"front": front, "return": ret, "height": H, "door_offset": doff, "door_width": dw}
_c = compute(_p); L = _c["L"]
from rules import RULES
M, DS = RULES["materials"], RULES["door_set"]
fq = lambda name: M["form_quantities"].get(name, "")   # fixed quantity per job on BSG's paper form, blank if none
SPARE = RULES["sheet"]["spare"]   # always send 2 extra sheets in case of damage (Gus, 2026-10-21)
sheets = _c["sheets"] + SPARE   # layout sheets + spares
tops = _c["tops"]   # one top above every sheet piece, joins aligned (boss, 2026-10-21); was ceil(L/1.2)                                            # 1.2 m wide tops along the whole run
from titan import joins
uprights = joins(_p, _c)   # one at every joint between sheets, incl. both sides of the entry (Gus, 2026-11-01), or set by hand in job.json; was ceil(L/1.2)+1
studs = math.ceil(M["studs"] * L / M["per_length"])   # 14 / 8 / 10 per 8.8 m, inferred from Just Cuts
tape = math.ceil(M["white_tape"] * L / M["per_length"])
tampers = math.ceil(M["anti_tampers"] * L / M["per_length"])
SHT = _p.get("sheet_h", RULES["sheet"]["height"])   # sheet height (2.4 for 2.4 m jobs)
top = round((H - SHT) * 1000)
from titan import for_job, EXTRA
UPJ = uprights
uprights, UPX, SPU, PER, CW = for_job({**_p, "height": H}, UPJ)   # joints + extra for wind + 10% spare uprights; weights by the matrix + 10% spare (Gus, 2026-11-01)
UTXT = "  +  ".join([f"{UPJ} at joins"] + ([f"{UPX} extra (wind)"] if UPX else []) + ([f"{SPU} spare"] if SPU else []))
TR = _p.get("track")   # fire-door jobs: track + timbers section instead of uprights
S = [
 ("Titan", [("Uprights", uprights, UTXT if UPX or SPU else ""), ("Counterweights", CW, f"{PER}   Per Upright  (+{round(EXTRA * 100)}% spare)")]),
 ("Board", [("16mm Melamine", f"{sheets} x", f"{SHT:g}m (+{SPARE} spare) + {tops} x {top} Tops" if top > 0 else f"{SHT:g}m (+{SPARE} spare)"), ("15mm CD Ply", "", "2.4m – 3.0m")]),
 ("Timber/Track", [("70 x 45 MGP 10", f"{studs} x", f"{H:g}"), ("70 x 45 Topplate", "", ""),
                   ("70 x 45 Door Studs", DS["studs_full_height"] + DS["studs_short"], f"{DS['studs_full_height']} x {H:g}  +  {DS['studs_short']} x {DS['studs_short_length']:g}"),
                   ("90mm track", f"{TR['lengths']} x" if TR else "", "3.0m  (ceiling + floor)" if TR else "3.0m"), ("90 x 45 MGP 10", f"{TR['studs']} x" if TR else "", f"{H:g}  (in the track, 600 centres)" if TR else "")]),
 ("Doors & Securities", [("Doors", DS["doors"], str(DS["leaf_mm"])), ("Digi Lock", "", ""), ("Deadbolt", DS["deadbolt"], ""), ("Padlock", "", ""), ("Barrel Bolt", "", ""),
                         ("Hasp & Staple", "", ""), ("Finger Pull", "", ""), ("T Section", "", ""), ("Hinges", DS["hinges"], ""), ("Metal Plates", DS["metal_plates"], "")]),
 ("Tapes", [("Paintable Tape 50mm", fq("Paintable Tape 50mm"), "25m Rolls"), ("White Tape 50mm", tape, f"{RULES['tape']['roll_length']:g}m Rolls"),
            ("Black Skirting Tape 100mm", fq("Black Skirting Tape 100mm"), "25m Rolls"),
            ("Double Sided Tape", fq("Double Sided Tape"), "Rolls"), ("Barrier Tape", fq("Barrier Tape"), "Rolls"), ("Bollards", fq("Bollards"), "")]),
 ("Screws & Stickers", [("40mm Screws", fq("40mm Screws"), "Boxes"), ("Plasterboard Screws", fq("Plasterboard Screws"), "Boxes"), ("White Screw Covers", fq("White Screw Covers"), "Packets"),
                        ("Anti-Tampers", tampers, ""), ("Warning Stickers", fq("Warning Stickers"), ""), ("Installation Certificate", fq("Installation Certificate"), "")]),
 ("Tools", [("Ladder", fq("Ladder"), "3.0m  +  3.6m"), ("Dust Suppression", fq("Dust Suppression"), "Rolls – Black/ White"), ("Paint", fq("Paint"), "Litres   Black + White"),
            ("Roller Kit", fq("Roller Kit"), ""), ("Roller Pole", fq("Roller Pole"), ""), ("Trolleys", fq("Trolleys"), ""), ("Broom", fq("Broom"), ""), ("Dustpan", fq("Dustpan"), ""),
            ("Spray, Wipes & Rags", fq("Spray, Wipes & Rags"), "")]),
]
wb = Workbook(); ws = wb.active; ws.title = "Materials"
t = Side(style="thin", color="000000"); B = Border(left=t, right=t, top=t, bottom=t)
head = PatternFill("solid", fgColor="E9D9B8"); hand = Font(color="1F3FA0", bold=True, size=12)
ws.merge_cells("A1:F1"); ws["A1"] = f"{job}   |   Length {L:g} m   |   Height {H:g} m"; ws["A1"].font = Font(bold=True, size=13)
for col, txt in zip("ABCDEF", ["", "Materials", "Quantities", "Description", "BSG\nCHK", "INST\nCHK"]):
    c = ws[f"{col}2"]; c.value = txt; c.font = Font(bold=True); c.fill = head; c.border = B
    c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
ws.merge_cells("A2:B2"); ws["A2"] = "Materials"
r = 3
for sec, items in S:
    r0 = r
    for name, q, desc in items:
        ws.cell(r, 2, name).font = Font(bold=True)
        cq = ws.cell(r, 3, q); cq.font = hand; cq.alignment = Alignment(horizontal="center")
        cd = ws.cell(r, 4, desc); cd.font = hand if (q != "" and desc) else Font()
        for col in range(1, 7): ws.cell(r, col).border = B
        r += 1
    ws.merge_cells(start_row=r0, start_column=1, end_row=r - 1, end_column=1)
    c = ws.cell(r0, 1, sec); c.alignment = Alignment(text_rotation=90, horizontal="center", vertical="center", wrap_text=True); c.font = Font(bold=True, size=9)
r += 1
ws.merge_cells(start_row=r, start_column=1, end_row=r + 1, end_column=2)
c = ws.cell(r, 1, "Materials\nchecked by:"); c.font = Font(bold=True); c.fill = head; c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
ws.cell(r, 3, "Factory:"); ws.cell(r + 1, 3, "Installers:")
ws.cell(r, 4, "(NAME)"); ws.cell(r + 1, 4, "(NAME)"); ws.cell(r, 5, "(SIGNATURE)"); ws.cell(r + 1, 5, "(SIGNATURE)")
for rr in (r, r + 1):
    for col in range(1, 7): ws.cell(rr, col).border = B
if TR:
    ws.merge_cells(start_row=r + 3, start_column=1, end_row=r + 3, end_column=6)
    ws.cell(r + 3, 1, "Note: track + timbers is a suggestion only; BSG is still learning this method.").font = Font(bold=True, color="CD6E00")
for col, w in zip("ABCDEF", [6, 26, 12, 34, 8, 8]): ws.column_dimensions[col].width = w
ws.row_dimensions[2].height = 30
ws.page_setup.orientation = "portrait"; ws.sheet_properties.pageSetUpPr.fitToPage = True; ws.page_setup.fitToWidth = 1; ws.page_setup.fitToHeight = 1
wb.save(out)
print(f"L={L} sheets={sheets} tops={tops} uprights={uprights} studs={studs} tape={tape} tampers={tampers}")
