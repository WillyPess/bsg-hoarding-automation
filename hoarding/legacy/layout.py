from PIL import Image, ImageDraw, ImageFont
F="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"; FB="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
f=lambda s,b=True: ImageFont.truetype(FB if b else F,s)
INK=(25,28,32); GREY=(120,125,130)
COL={1:(186,214,240),2:(190,230,200),3:(250,222,170),4:(222,200,240),5:(245,200,200),6:(200,232,232),7:(255,236,120),8:(255,190,140),"T":(225,225,225)}
W,Hc=2300,2350; im=Image.new("RGB",(W,Hc),"white"); d=ImageDraw.Draw(im)
def t(xy,s,ft,fill=INK,a="mm"): d.text(xy,s,font=ft,fill=fill,anchor=a)
t((80,70),"DE ONES: MELAMINE LAYOUT (8 sheets 1.2 x 3.6 m + 9 tops 1.2 x 0.9 m)",f(42),INK,"lm")
t((80,125),"Sizes in mm. Same colour and number = cut from the same sheet. Draft: based on estimated 7000 front.",f(28,False),GREY,"lm")
# ---- elevation ----
s=190; X0=160; Yb=1130; y36=Yb-3.6*s; yT=Yb-4.5*s; yD=Yb-2.4*s
t((80,215),"ELEVATION (returns unfolded, seen from the mall)",f(30),GREY,"lm")
def piece(x,w,y0,y1,key,label):
    a=(X0+x*s,y0); b=(X0+(x+w)*s,y1)
    d.rectangle([a,b],fill=COL[key],outline=INK,width=3)
    t(((a[0]+b[0])/2,(y0+y1)/2),label,f(26 if w>0.3 else 20),INK)
# lower 3.6 m pieces: (x, width, sheet, label)
low=[(0,1.2,1,"S1"),(1.2,0.4,7,"S7a"),          # left return 1600
     (1.6,1.2,2,"S2"),(2.8,0.4,7,"S7b"),        # front, left of door 1600
     (4.8,1.2,3,"S3"),(6.0,1.2,4,"S4"),(7.2,1.2,5,"S5"),(8.4,0.2,8,""),  # right of door 3800
     (8.6,0.4,7,"S7c"),(9.0,1.2,6,"S6")]        # right return 1600
for x,w,k,l in low: piece(x,w,y36,Yb,k,l)
t((X0+8.5*s,Yb+30),"S8a",f(20),INK)
# door + door top
piece(3.2,1.0,y36,yD,8,"S8b"); piece(4.2,0.6,y36,yD,8,"S8c")
d.rectangle([X0+3.2*s,yD,X0+4.8*s,Yb],fill="white",outline=INK,width=4)
d.line([(X0+3.2*s,yD),(X0+4.8*s,Yb)],fill=INK,width=3); d.line([(X0+4.8*s,yD),(X0+3.2*s,Yb)],fill=INK,width=3)
t((X0+4.0*s,yD+40),"ENTRY 1600 x 2400",f(22),INK)
# tops
# tops split at the corners; offcuts reused (T8 = 2 x 400, T9 = 1000)
for x,w,l in [(0,1.2,"T1"),(1.2,0.4,"T8a"),(1.6,1.2,"T2"),(2.8,1.2,"T3"),(4.0,1.2,"T4"),(5.2,1.2,"T5"),(6.4,1.2,"T6"),(7.6,1.0,"T9"),(8.6,0.4,"T8b"),(9.0,1.2,"T7")]:
    piece(x,w,yT,y36,"T",l)
# section boundaries + dims
for xb,lab in [(1.6,"RETURN 1600"),(5.0,""),(8.6,""),(10.2,"")]: pass
for x in (1.6,8.6): d.line([(X0+x*s,yT-10),(X0+x*s,Yb+10)],fill=INK,width=7)
d.rectangle([X0,yT,X0+10.2*s,Yb],outline=INK,width=6)
def hd(xa,xb,y,lab):
    a,b=X0+xa*s,X0+xb*s; d.line([(a,y),(b,y)],fill=INK,width=2)
    for xx in (a,b): d.line([(xx,y-12),(xx,y+12)],fill=INK,width=2)
    t(((a+b)/2,y+24),lab,f(24),INK)
y=Yb+75
for a,b,l in [(0,1.6,"1600 return"),(1.6,3.2,"1600"),(3.2,4.8,"1600 entry"),(4.8,8.6,"3800"),(8.6,10.2,"1600 return")]: hd(a,b,y,l)
hd(0,10.2,y+80,"10200")
xr=X0+10.2*s+30
for ya,yb,l in [(yT,y36,"900"),(y36,Yb,"3600")]:
    d.line([(xr,ya),(xr,yb)],fill=INK,width=2); [d.line([(xr-12,yy),(xr+12,yy)],fill=INK,width=2) for yy in (ya,yb)]
    t((xr+14,(ya+yb)/2),l,f(24),INK,"lm")
# ---- cutting diagram ----
Y0=1440; cs=150
t((80,Y0-60),"CUTTING PLAN: the 8 sheets",f(30),GREY,"lm")
def sheet(i,cuts,note):
    x0=110+(i-1)*265; h=3.6*cs; w=1.2*cs
    d.rectangle([x0,Y0,x0+w,Y0+h],fill=(245,245,245),outline=INK,width=3)
    for cx,cw,cy,ch,key,l in cuts:
        a=(x0+cx*cs,Y0+cy*cs); b=(x0+(cx+cw)*cs,Y0+(cy+ch)*cs)
        d.rectangle([a,b],fill=COL[key] if key else (245,245,245),outline=INK,width=2)
        if l: t(((a[0]+b[0])/2,(a[1]+b[1])/2),l,f(20),INK)
    t((x0+w/2,Y0-22),f"S{i}",f(28),INK)
    for k,line in enumerate(note): t((x0+w/2,Y0+h+30+k*28),line,f(20,False),INK)
for i in range(1,7): sheet(i,[(0,1.2,0,3.6,i,"full")],["full sheet",["L. return","front left","right","right","right","R. return"][i-1]])
sheet(7,[(0,0.4,0,3.6,7,"a"),(0.4,0.4,0,3.6,7,"b"),(0.8,0.4,0,3.6,7,"c")],["3 x 400","returns +","front left"])
sheet(8,[(0,0.2,0,3.6,8,"a"),(0.2,1.0,0,1.2,8,"b"),(0.2,0.6,1.2,1.2,8,"c"),(0.8,0.4,1.2,1.2,None,"spare"),(0.2,1.0,2.4,1.2,None,"spare")],["a: 200 strip","b+c: door top","1200 high"])
t((80,Hc-50),"Tops: 9 pieces 1200 x 900. T8 is cut into 2 x 400 for the corners, T9 cut to 1000. Uprights and studs not shown.",f(26,False),GREY,"lm")
im.save("/mnt/project-files/hoarding/DeOnes_melamine_layout_DRAFT.png")
