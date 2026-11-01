from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame, NextPageTemplate, SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak, ListFlowable, ListItem, KeepTogether
from PIL import Image as PI
from pypdf import PdfWriter, PdfReader
D="/mnt/project-files/hoarding/FRED/"
ss=getSampleStyleSheet()
H1=ParagraphStyle("h1",parent=ss["Title"],fontSize=22,spaceAfter=4,alignment=0)
H2=ParagraphStyle("h2",parent=ss["Heading2"],fontSize=14,spaceBefore=10,spaceAfter=6,textColor=colors.HexColor("#b01818"))
B=ParagraphStyle("b",parent=ss["BodyText"],fontSize=10,leading=14)
S=ParagraphStyle("s",parent=B,fontSize=9,textColor=colors.HexColor("#555555"))
W=180*mm
def img(p,maxh=230*mm,maxw=W):
    w,h=PI.open(p).size; r=min(maxw/w,maxh/h); return Image(p,w*r,h*r)
def tbl(rows,widths):
    t=Table(rows,colWidths=widths,repeatRows=1)
    t.setStyle(TableStyle([("FONT",(0,0),(-1,0),"Helvetica-Bold",9),("FONT",(0,1),(-1,-1),"Helvetica",9),
        ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#E9D9B8")),("GRID",(0,0),(-1,-1),0.5,colors.grey),("VALIGN",(0,0),(-1,-1),"TOP")]))
    return t
st=[Paragraph("FRED: Hoarding Package",H1),Paragraph("BSG · 20/10/2026 · Prepared by Gus",S),Spacer(1,6),
 Paragraph("A 14.2 m run of melamine hoarding, 4.5 m high, set 1.6 m out from the FRED shopfront, with a 1.6 m double-door entry starting 4.8 m from the left end of the front.",B),Spacer(1,6),
 tbl([["Item","Size"],["Shopfront (lease line)","11.0 m"],["Returns","1.6 m each side"],["Total hoarding length","14.2 m (1.6 + 11.0 + 1.6)"],["Height","4.5 m"],["Hoarding entry","1.6 m wide x 2.4 m high, 2 leaves"],["Entry position","4.8 m from the left end of the front (1600 wide, 4800 to 6400), set to use full sheets"],["Melamine","12 sheets 1200 x 3600 + 12 tops 1200 x 900"]],[60*mm,120*mm]),
 Paragraph("Contents: 1. Hoarding limit on photo · 2. Plan and elevation · 3. Melamine layout · 4. Build sequence · 5. Site checks · 6. Materials form",S),
 Paragraph("1. Hoarding limit on the photo",H2),
 Paragraph("The red outline is the hoarding limit on the floor; the crossed box is the entry. The entry starts 4.8 m from the left end of the front.",B),Spacer(1,4),img(D+"FRED_hoarding_markup.jpg",110*mm),
 NextPageTemplate("land"),PageBreak(),Paragraph("2. Plan and elevation",H2),Paragraph("All sizes in mm. The dashed red line is the lease line (the shopfront): nothing is fixed to it.",B),Spacer(1,4),img(D+"FRED_hoarding_sheet.png",160*mm,267*mm),
 PageBreak(),Paragraph("3. Melamine layout and cutting plan",H2),Paragraph("Each panel is numbered by the sheet it is cut from. Full sheets S1 to S9 go in whole; the cut pieces sit at the corners. S10 gives the 1000 strip at the right end of the front. S11 gives the two 400 return strips. S12 is turned sideways and cut to one 1600 x 1200 piece above the entry. Tops T1 to T11 go in whole; T12 is cut 400 + 400 + 200.",B),Spacer(1,4),img(D+"FRED_melamine_layout.png",150*mm,267*mm),
 NextPageTemplate("port"),PageBreak(),Paragraph("4. Build sequence",H2),Paragraph("Build left to right as seen from the mall: left return, front, right return.",B)]
steps=[("Before leaving the factory","Check every item against the materials form and tick BSG CHK. Pre-cut S10, S11, S12 and T12 as on the cutting plan and number the back of each piece."),
("Arrive and secure the area","Sign in with centre management. Set up barrier tape and the bollard around the work zone. Lay the dust suppression."),
("Set out the hoarding limit","Mark both ends of the lease line and measure 1600 out from each. Snap the 11000 front line parallel to the shopfront. Both diagonals read about 11115 when square."),
("Mark the entry","Measure 4800 from the left end of the front line and mark a 1600 opening (4800 to 6400)."),
("Stand the Titan uprights","13 uprights at no more than 1200 centres, one at each corner and one each side of the entry, 6 counterweights on each."),
("Frame the walls","Fix the 70 x 45 MGP 10 studs (4.5 m) so every melamine joint lands on a stud. Frame the entry with 2 x 4.5 m and 4 x 2.3 m door studs and a head at 2400."),
("Fix the 3600 sheets","Left return S1 + S11a (400) at the corner; front left S2 to S5, all full; front right S6, S7, S8 full + S10 (1000) at the corner; right return S11b (400) at the corner + S9."),
("Fill above the entry","One 1600 x 1200 piece (S12) between the door head at 2400 and 3600."),
("Fix the tops","900 tops from 3600 to 4500 along the whole run: T1 to T11 whole, T12 cut 400 + 400 + 200."),
("Hang the doors","Two 2340 leaves on 4 hinges, metal plates and deadbolt. Check they close and lock."),
("Finish","White tape on every vertical joint, black skirting tape along the base, screw covers, anti-tampers, 6 warning stickers, paint touch-ups."),
("Hand over","Clean up, remove the barrier, photograph each side, complete the installation certificate and sign INST CHK.")]
st.append(ListFlowable([ListItem(Paragraph(f"<b>{a}.</b> {b}",B)) for a,b in steps],bulletType="1",leftIndent=14))
st+= [Paragraph("5. Site checks",H2),Paragraph("Confirm before fixing anything; update the drawings if any differ.",B),
 ListFlowable([ListItem(Paragraph("[  ]  "+x,B)) for x in ["The front measures 11000 between the mirror column and the Tag Heuer frontage.","The ceiling is above 4500 along the whole run.","The entry starts 4800 from the left end of the front.","The 1600 returns leave the walkway centre management requires.","Nothing is fixed to the shopfront or floor; the Titan counterweights hold the hoarding."]],bulletType="bullet",start="",leftIndent=6),
 Spacer(1,8),Paragraph("6. Materials form follows on the next page.",S)]
doc=BaseDocTemplate("/tmp/claude-0/-home-claude/78a567a2-2bf4-5b78-ade1-690dc0553528/scratchpad/hoarding/body.pdf",pagesize=A4,title="FRED Hoarding Package")
pw,ph=A4; lw,lh=landscape(A4)
doc.addPageTemplates([PageTemplate("port",[Frame(15*mm,15*mm,pw-30*mm,ph-30*mm)],pagesize=A4),PageTemplate("land",[Frame(15*mm,12*mm,lw-30*mm,lh-24*mm)],pagesize=landscape(A4))])
doc.build(st)
w=PdfWriter()
for f in ["/tmp/claude-0/-home-claude/78a567a2-2bf4-5b78-ade1-690dc0553528/scratchpad/hoarding/body.pdf",D+"FRED_materials.pdf"]:
    for p in PdfReader(f).pages: w.add_page(p)
w.add_metadata({"/Title":"FRED Hoarding Package"})
with open(D+"FRED_Hoarding_Package.pdf","wb") as fh: w.write(fh)
print(len(w.pages),"pages")
