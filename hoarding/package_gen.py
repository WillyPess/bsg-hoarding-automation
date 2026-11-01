from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm as mm_
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame, NextPageTemplate, SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak, ListFlowable, ListItem, KeepTogether
from PIL import Image as PI
from pypdf import PdfWriter, PdfReader
import sys, json, math, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from layout_gen import compute
from rules import RULES
# Usage: package_gen.py job.json  (keys: name, prefix, dir, date, front, return, height, door_offset, door_width, door_height, by, front_ends, entry_note)
J=json.load(open(sys.argv[1])); D=J["dir"].rstrip("/")+"/"; P=J["prefix"]; N=J["name"]
F,R,H,DO,DW,DH=J["front"],J["return"],J["height"],J["door_offset"],J["door_width"],J.get("door_height",RULES["defaults"]["door_height"])
c=compute(J); L=c["L"]; mm=lambda v:f"{round(v*1000)}"; m=lambda v:f"{v:g} m"
SW,SH0,SPARE,DS=RULES["sheet"]["width"],RULES["sheet"]["height"],RULES["sheet"]["spare"],RULES["door_set"]   # sheet width, standard sheet height, spare sheets, door set
from titan import for_job, joins, wind, EXTRA, SPARE as UPSPARE
UPJ=joins(J,c)   # at the joins between sheets (Gus, 2026-11-01), or set by hand in job.json
up,UPX,SPU,PER,CW=for_job(J,UPJ)   # uprights to send = joints + extra for wind + 10% spare; BSG weight matrix by height, +10% spare (Gus, 2026-11-01)
XFRAC,WPU=wind(J); SP=round(EXTRA*100); SUP=round(UPSPARE*100)   # external job: extra uprights fraction, weights per upright; spare weights %, spare uprights %
SPTXT=f" Plus {SPU} spare upright{'' if SPU==1 else 's'} ({SUP}%), not placed on the layout." if SPU else ""
WTXT=f"{PER} counterweights each ({'for wind, external site' if WPU else f'weight matrix for {H:g} m'}; {CW} sent, incl. {SP}% spare)"
XTXT=f" Plus {UPX} extra uprights ({round(XFRAC*100)}% more, for wind on this external site), also with {PER} counterweights each; the supervisor decides where they go." if UPX else ""
# Corner jobs ("faces" in job.json): angled return by the lift, side, corner, front with the entry, right return
UJ=J.get("shape")=="U"   # U-shaped run round three sides of a kiosk (David Jones Lift Area, 2026-11-01)
CN="faces" in J and "track" not in J and not UJ
SHT=J.get("sheet_h",SH0)   # sheet height: 2.4 for 2.4 m jobs
U_INTRO=U_ROWS=U_CHECKS=None
if UJ:
    UF=J["faces"]; ULR,ULS,UFR,URS,URR=[f["len"] for f in UF]; UDO=UF[3]["door_offset"]
    U_INTRO=(f"A {L:g} m U-shaped run of melamine hoarding, {H:g} m high{' (external)' if J.get('external') else ''}, round three sides of the {N}: a {ULR:g} m left return, the {ULS:g} m left side, "
             f"the {UFR:g} m front, the {URS:g} m right side with a {DW:g} m double-door entry, and a {URR:g} m right return. The entry starts {UDO:g} m from the front corner, with one full {mm(SW)} sheet between it and the right return.")
    U_ROWS=[["Item","Size"],["Left return",m(ULR)],["Left side",m(ULS)],["Front",m(UFR)],["Right side",m(URS)],["Right return",m(URR)],
            ["Total hoarding length",f"{L:g} m ("+" + ".join(f"{f['len']:g}" for f in UF)+")"],["Height",m(H)+(" (external)" if J.get("external") else "")],
            ["Hoarding entry",f"{DW:g} m wide x {DH:g} m high, 2 leaves, on the right side"],["Entry position",f"{UDO:g} m from the front corner ({mm(UDO)} to {mm(UDO+DW)} along the right side)"+J.get("entry_note","")],
            ["Uprights",f"{up}: {UPJ} at the joints between sheets"+(f" + {UPX} extra for wind ({round(XFRAC*100)}% more)" if UPX else "")+(f" + {SPU} spare ({SUP}%)" if SPU else "")+f"; {WTXT}"]]
    U_CHECKS=[f"The sides measure {mm(ULS)} and {mm(URS)} and the front {mm(UFR)}, square at both corners.",f"The returns are {mm(ULR)} and {mm(URR)} back to the building.",
              f"The entry starts {mm(UDO)} from the front corner on the right side, in front of the kiosk entry.",
              "The bollards and parking bays leave room for the uprights and counterweights.",
              f"External site: every upright has {PER} counterweights and there are {UPX} extra uprights for wind; place the extras where the site is most exposed." if UPX else "External site: the weight matrix is for internal hoardings, so check the wind exposure with the supervisor."]
# Fire-door jobs ("track" in job.json): track + timbers beside the fire door instead of uprights, no uprights in the corners (Gus, 2026-10-28)
FD="track" in J; FD_INTRO=FD_ROWS=FD_CHECKS=None
if FD:
    TRK=J["track"]; RR=J["right_return"]; SF=J["shopfront"]; STP=J["step"]; PU=J["push"]
    NOTE="<b>Note:</b> track + timbers is a suggestion only; BSG is still learning this method."
    FD_INTRO=(f"A {L:g} m run of melamine hoarding, {H:g} m high, around the {N} shopfront next to a fire door: a {R:g} m left return beside the fire door, "
              f"the {F:g} m front with a {DW:g} m double-door entry, and a {RR:g} m right return. The first {TRK['len']:g} m of the left return, beside the fire door, "
              f"is held by steel tracks (ceiling + floor) and timbers instead of uprights. "+NOTE)
    FD_ROWS=[["Item","Size"],["Shopfront (lease line)",f"{SF:g} m, {STP:g} m in front of the fire door wall"],
             ["Left return",f"{R:g} m from the fire door wall, {mm(PU)} mm left of the shop's side"],["Front",f"{F:g} m, parallel to the shopfront"],
             ["Right return",f"{RR:g} m from the lease line"],["Total hoarding length",f"{L:g} m ({R:g} + {F:g} + {RR:g})"],["Height",m(H)],
             ["Hoarding entry",f"{DW:g} m wide x {DH:g} m high, 2 leaves"],["Entry position",f"{DO:g} m from the left corner ({mm(DO)} to {mm(DO+DW)}), {F-DO-DW:g} m from the right end"],
             ["Track section",f"First {mm(TRK['len'])} of the left return from the fire door wall: 90 mm track on the ceiling and floor, {TRK['studs']} x 90x45 MGP10 at 600 centres. Suggestion only."],
             ["Uprights",f"{up}: {UPJ} at the joints between sheets, none in the corners (no room there)"+(f", plus {SPU} spare ({SUP}%)" if SPU else "")],["Melamine",None]]
    FD_CHECKS=[f"The front measures {mm(F)} and runs parallel to the shopfront.",f"The ceiling is at {mm(H)} along the run and is sound for fixing the track beside the fire door (the old fixing marks show where it went before).",
               f"The entry starts {mm(DO)} from the left corner ({mm(F-DO-DW)} from the right end).",f"The {mm(RR)} right return leaves the walkway centre management requires.",
               "Nothing is fixed to the shopfront; outside the track section the Titan counterweights hold the hoarding."]
if CN:
    FA=J["faces"]
    AN,SD,RR=FA[0]["len"],FA[1]["len"],FA[3]["len"]
ss=getSampleStyleSheet()
H1=ParagraphStyle("h1",parent=ss["Title"],fontSize=22,spaceAfter=4,alignment=0)
H2=ParagraphStyle("h2",parent=ss["Heading2"],fontSize=14,spaceBefore=10,spaceAfter=6,textColor=colors.HexColor("#b01818"))
B=ParagraphStyle("b",parent=ss["BodyText"],fontSize=10,leading=14)
S=ParagraphStyle("s",parent=B,fontSize=9,textColor=colors.HexColor("#555555"))
W=180*mm_
def img(p,maxh=230*mm_,maxw=W):
    w,h=PI.open(p).size; r=min(maxw/w,maxh/h); return Image(p,w*r,h*r)
def tbl(rows,widths):
    rows=[r if i==0 else [Paragraph(str(x),ParagraphStyle('tc',parent=B,fontSize=9,leading=11)) for x in r] for i,r in enumerate(rows)]
    t=Table(rows,colWidths=widths,repeatRows=1)
    t.setStyle(TableStyle([("FONT",(0,0),(-1,0),"Helvetica-Bold",9),("FONT",(0,1),(-1,-1),"Helvetica",9),
        ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#E9D9B8")),("GRID",(0,0),(-1,-1),0.5,colors.grey),("VALIGN",(0,0),(-1,-1),"TOP")]))
    return t

cuts_txt=" ".join(f"S{b['sheet']} gives "+" and ".join(f"the {mm(cu['w'])} strip for the {cu['where']}" for cu in b["cuts"])+"." for b in c["bins"])
door_txt=(f" S{c['door']['sheet']} is turned sideways and cut to one {mm(DW)} x {mm(c['door']['h'])} piece above the entry."+(f" <b>Note:</b> instead of cutting S{c['door']['sheet']}, the door-top pieces can be cut in the factory from a spare sheet and sent to the job." )) if c["door"] else ""
nt=len(c["tfull"]); tcut=" ".join(f"T{nt+i+1} is cut "+" + ".join(mm(cu['w']) for cu in b["cuts"])+"." for i,b in enumerate(c["tbins"]))
tops_txt=(f"Each top is the same width as the sheet below it, so every join is one straight line from floor to top. Tops T1 to T{nt} go in whole. {tcut}"+(f" Above the entry goes one {mm(DW)} x {mm(H-SH0)} piece cut from S{c['door']['top_sheet']}." if c["door"] and c["door"].get("top_h") else "")) if c["tops"] else ""
precut=", ".join([f"S{b['sheet']}" for b in c["bins"]]+([f"S{c['door']['sheet']}"] if c["door"] else [])+[f"T{nt+i+1}" for i in range(len(c["tbins"]))])
def sec_txt(name):
    fs=[f"S{x['sheet']}" for x in c["full"] if x["where"]==name]
    cs=[f"{cu['label']} ({mm(cu['w'])}, at the corner)" for b in c["bins"] for cu in b["cuts"] if cu["where"]==name]
    return name+" "+(", ".join(fs+cs) if fs or cs else "none")
mel=f"{c['sheets']+SPARE} sheets {mm(SW)} x {mm(SHT)} ({c['sheets']} in the layout + {SPARE} spare in case of damage)"+(f" + {c['tops']} tops {mm(SW)} x {mm(H-SH0)}" if c["tops"] else "")
st=[Paragraph(f"{N}: Hoarding Package",H1),Paragraph(f"BSG · {J['date']} · Prepared by {J.get('by','Gus')}",S),Spacer(1,6),
 Paragraph(f"A {L:g} m L-shaped run of melamine hoarding, {H:g} m high, around the {N} corner shop: a {AN:g} m angled return by the lift, the {SD:g} m side, the corner, the {F:g} m front with a {DW:g} m double-door entry, and a {RR:g} m return. The entry starts {DO:g} m from the corner ({F-DO-DW:g} m from the right end)." if CN else FD_INTRO if FD else U_INTRO if UJ else f"A {L:g} m run of melamine hoarding, {H:g} m high, set {R:g} m out from the {N} shopfront, with a {DW:g} m double-door entry starting {DO:g} m from the left end of the front.",B),Spacer(1,6),
 tbl([["Item","Size"],["Angled return (by the lift)",f"{AN:g} m, angle to suit, keep clear of the lift"],["Side",m(SD)],["Front",m(F)],["Right return",m(RR)],["Total hoarding length",f"{L:g} m ("+" + ".join(f"{f['len']:g}" for f in FA)+")"],["Height",m(H)],["Hoarding entry",f"{DW:g} m wide x {DH:g} m high, 2 leaves"],["Entry position",f"{DO:g} m from the corner ({mm(DO)} to {mm(DO+DW)} along the front)"+J.get("entry_note","")],["Melamine",mel]] if CN else FD_ROWS[:-1]+[["Melamine",mel]] if FD else U_ROWS+[["Melamine",mel]] if UJ else [["Item","Size"],["Shopfront (lease line)",m(F)],["Returns",f"{R:g} m each side"],["Total hoarding length",f"{L:g} m ({R:g} + {F:g} + {R:g})"],["Height",m(H)],["Hoarding entry",f"{DW:g} m wide x {DH:g} m high, 2 leaves"],["Entry position",f"{DO:g} m from the left end of the front ({mm(DO)} to {mm(DO+DW)})"+J.get("entry_note","")],["Melamine",mel]],[60*mm_,120*mm_]),
 Paragraph("Contents: 1. Hoarding limit on photo · 2. Plan and elevation · 3. Melamine layout · 4. Suggested Build Sequence · 5. Site checks · 6. Materials form",S),
 Paragraph("1. Hoarding limit on the photo",H2),
 Paragraph(f"The red outline is the hoarding limit on the floor; the crossed box is the entry. The entry starts {DO:g} m from the {'corner' if CN else 'left end of the front'}."+(" The short angled return by the lift only has to keep clear of the lift; its angle is not critical." if CN else "")+(" The green part of the left return is the track + timber section beside the fire door." if FD else "")+(" "+J["photo_note"] if J.get("photo_note") else "") if not J.get("photo_text") else J["photo_text"],B),Spacer(1,4),img(D+P+"_hoarding_markup.jpg",J.get("photo_h",115)*mm_),
 NextPageTemplate("land"),PageBreak(),Paragraph("2. Plan and elevation",H2),Paragraph("All sizes in mm. The dashed red line is the lease line (the shopfront): nothing is fixed to it.",B),Spacer(1,4),img(D+P+"_hoarding_sheet.png",160*mm_,267*mm_),
 PageBreak(),Paragraph("3. Melamine layout and cutting plan",H2),Paragraph(f"Each panel is numbered by the sheet it is cut from. Full sheets S1 to S{len(c['full'])} go in whole; the cut pieces sit at the corners. {cuts_txt}{door_txt} {tops_txt}",B),Spacer(1,4),img(D+P+"_melamine_layout.png",150*mm_,267*mm_),
 NextPageTemplate("port"),PageBreak(),Paragraph("4. Suggested Build Sequence",H2),Paragraph("Build left to right as seen from the mall: angled return by the lift, side, corner, front, right return." if CN else "Build left to right, facing the front: left return, left side, front, right side (with the entry), right return." if UJ else "Build left to right as seen from the mall: left return (track section first), front, right return." if FD else "Build left to right as seen from the mall: left return, front, right return.",B)]
steps=[("Check the truck",f"Before leaving, check the truck against the materials form to make sure all the material was loaded, including the {SPARE} spare sheets."),
("Arrive and secure the area","Sign in with centre management. Set up barrier tape and the bollard around the work zone. Lay the dust suppression."),
("Set out the hoarding limit",f"Measure {mm(RR)} out from the shop front and snap the {mm(F)} front line parallel to it, ending at the outer corner. From the corner snap the {mm(SD)} side line at 90 degrees, parallel to the shop side. Finish with the {mm(AN)} angled return back to the shop, kept well clear of the lift (the angle can suit the site).") if CN else
("Set out the hoarding limit",f"Mark both ends of the lease line and measure {mm(R)} out from each. Snap the {mm(F)} front line parallel to the shopfront."),
("Mark the entry",f"Measure {mm(DO)} from the corner along the front line and mark a {mm(DW)} opening ({mm(DO)} to {mm(DO+DW)}); it ends {mm(F-DO-DW)} from the right end.") if CN else
("Mark the entry",f"Measure {mm(DO)} from the left end of the front line and mark a {mm(DW)} opening ({mm(DO)} to {mm(DO+DW)})."),
("Stand the Titan uprights",f"{UPJ} uprights, each one at a joint between two sheets (never in the middle of a sheet), including one each side of the entry, {PER} counterweights on each (weight matrix for {H:g} m; {CW} sent, incl. {SP}% spare). They are marked on the melamine layout.{SPTXT}" if not UPX else f"{UPJ} uprights, each one at a joint between two sheets (never in the middle of a sheet), including one each side of the entry; they are marked on the melamine layout.{XTXT}{SPTXT} {CW} counterweights are sent, incl. {SP}% spare."),
("Frame the walls",f"Fix the 70 x 45 MGP 10 studs ({H:g} m) so every melamine joint lands on a stud. Frame the entry with {DS['studs_full_height']} x {H:g} m and {DS['studs_short']} x {DS['studs_short_length']:g} m door studs and a head at {mm(DH)}."),
(f"Fix the {mm(SHT)} sheets",(lambda x: x[0].upper()+x[1:])("; ".join(sec_txt(n) for n in (["angled return","side","front left","front right","right return"] if CN else ["left return","left side","front","right side left","right side right","right return"] if UJ else ["left return","front left","front right","right return"])))+"."),
]+([("Fill above the entry",f"One {mm(DW)} x {mm(c['door']['h'])} piece (S{c['door']['sheet']}) between the door head at {mm(DH)} and {mm(SH0)}.")] if c["door"] else [])+([
("Fix the tops",f"{mm(H-SH0)} tops from {mm(SH0)} to {mm(H)} along the whole run. {tops_txt}")] if c["tops"] else [])+[
("Hang the doors",f"{('One','Two','Three','Four')[DS['doors']-1]} {DS['leaf_mm']} leaves on {DS['hinges']} hinges, metal plates and deadbolt. Check they close and lock."),
("Finish",f"White tape on every vertical joint, black skirting tape along the base, screw covers, anti-tampers, {RULES['materials']['form_quantities']['Warning Stickers']} warning stickers, paint touch-ups."),
("Hand over","Clean up, remove the barrier, photograph each side, complete the installation certificate and sign INST CHK.")]
if UJ:
    u={"Set out the hoarding limit":f"From the building, mark the {mm(ULR)} left return and the {mm(URR)} right return. Snap the {mm(ULS)} left side and the {mm(URS)} right side at 90 degrees to them, then the {mm(UFR)} front joining the two corners.",
       "Mark the entry":f"On the right side, measure {mm(UDO)} from the front corner and mark a {mm(DW)} opening ({mm(UDO)} to {mm(UDO+DW)}); one full {mm(SW)} sheet follows it before the right return."}
    steps=[(a,u.get(a,b)) for a,b in steps]
if FD:
    from layout_gen import faces as _faces
    UPS,x0=[],0
    for k_,f_ in enumerate(_faces(J)):
        u_=[mm(u-x0) for u in c["uprights"] if x0-1e-6<=u<=x0+f_["len"]+1e-6]
        ref={0:"from the fire door wall",len(_faces(J))-1:"from the front corner"}.get(k_,"from the left corner")
        if u_: UPS.append(f"{f_['name']} at "+", ".join(u_)+" "+ref)
        x0+=f_["len"]
    fd={"Set out the hoarding limit":f"From the fire door wall, mark the left return {mm(R)} long, {mm(PU)} left of the shop's side wall. Snap the {mm(F)} front line parallel to the shopfront, {mm(RR)} out from the lease line. The right return runs {mm(RR)} back to the lease line.",
        "Mark the entry":f"Measure {mm(DO)} from the left corner along the front line and mark a {mm(DW)} opening ({mm(DO)} to {mm(DO+DW)}); it ends {mm(F-DO-DW)} from the right end.",
        "Stand the Titan uprights":f"{UPJ} uprights with {PER} counterweights each (weight matrix for {H:g} m; {CW} sent, incl. {SP}% spare), each one at a joint between two sheets, never in the middle of a sheet, and none in the corners (no room there): "+"; ".join(UPS)+f". They are marked on the melamine layout.{SPTXT}"}
    steps=[(a,fd.get(a,b)) for a,b in steps]
    steps.insert([a for a,b in steps].index("Stand the Titan uprights"),("Fix the tracks and timbers",f"Along the first {mm(TRK['len'])} of the left return from the fire door wall, fix 90 mm track to the ceiling and to the floor. Stand {TRK['studs']} x 90x45 MGP10 timbers ({H:g} m) in the tracks at 600 centres; the melamine is screwed to them. Suggestion only: BSG is still learning this method."))
st.append(ListFlowable([ListItem(Paragraph(f"<b>{a}.</b> {b}",B)) for a,b in steps],bulletType="1",leftIndent=14))
st+= [Paragraph("5. Site checks",H2),Paragraph("Confirm before fixing anything; update the drawings if any differ.",B),
 ListFlowable([ListItem(Paragraph("[  ]  "+x,B)) for x in ([f"The side measures {mm(SD)} and the front {mm(F)}, square at the corner.",f"The ceiling is above {mm(H)} along the whole run.",f"The entry starts {mm(DO)} from the corner ({mm(F-DO-DW)} from the right end).","The angled return keeps the lift doors and landing clear.",f"The {mm(RR)} return leaves the walkway centre management requires.","Nothing is fixed to the shopfront or floor; the Titan counterweights hold the hoarding."] if CN else FD_CHECKS if FD else U_CHECKS if UJ else [f"The front measures {mm(F)}"+(f" between {J['front_ends']}." if J.get("front_ends") else "."),f"The ceiling is above {mm(H)} along the whole run.",f"The entry starts {mm(DO)} from the left end of the front.",f"The {mm(R)} returns leave the walkway centre management requires.","Nothing is fixed to the shopfront or floor; the Titan counterweights hold the hoarding."])],bulletType="bullet",start="",leftIndent=6),
 Spacer(1,8),Paragraph("6. Materials form follows on the next page.",S)]
TMP=D+".body.pdf"
doc=BaseDocTemplate(TMP,pagesize=A4,title=f"{N} Hoarding Package")
pw,ph=A4; lw,lh=landscape(A4)
doc.addPageTemplates([PageTemplate("port",[Frame(15*mm_,15*mm_,pw-30*mm_,ph-30*mm_)],pagesize=A4),PageTemplate("land",[Frame(15*mm_,12*mm_,lw-30*mm_,lh-24*mm_)],pagesize=landscape(A4))])
doc.build(st)
w=PdfWriter()
for f in [TMP,D+P+"_materials.pdf"]:
    for p in PdfReader(f).pages: w.add_page(p)
w.add_metadata({"/Title":f"{N} Hoarding Package"})
with open(D+P+"_Hoarding_Package.pdf","wb") as fh: w.write(fh)
os.remove(TMP)
print(len(w.pages),"pages")
