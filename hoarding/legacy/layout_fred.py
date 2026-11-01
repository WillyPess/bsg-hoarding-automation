from PIL import Image, ImageDraw, ImageFont
F="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"; FB="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
f=lambda s,b=True: ImageFont.truetype(FB if b else F,s)
INK=(25,28,32); GREY=(120,125,130)
pal=[(186,214,240),(190,230,200),(250,222,170),(222,200,240),(245,200,200),(200,232,232),(214,234,170),(240,210,230),(205,215,250),(255,236,120),(255,190,140),(170,220,200)]
COL={i+1:c for i,c in enumerate(pal)}; COL["T"]=(225,225,225)
W,Hc=2400,1900; im=Image.new("RGB",(W,Hc),"white"); d=ImageDraw.Draw(im)
def t(xy,s,ft,fill=INK,a="mm"): d.text(xy,s,font=ft,fill=fill,anchor=a)
t((80,60),"FRED: MELAMINE LAYOUT (12 sheets 1.2 x 3.6 m + 12 tops 1.2 x 0.9 m)",f(40),INK,"lm")
t((80,110),"Sizes in mm. Same colour and number = cut from the same sheet. Front 11000, returns 1600, height 4500.",f(26,False),GREY,"lm")
s=150; X0=110; Yb=880; y36=Yb-3.6*s; yT=Yb-4.5*s; yD=Yb-2.4*s
t((80,170),"ELEVATION (returns unfolded, seen from the mall)",f(28),GREY,"lm")
def piece(x,w,y0,y1,key,label,fs=None):
    a=(X0+x*s,y0); b=(X0+(x+w)*s,y1)
    d.rectangle([a,b],fill=COL[key],outline=INK,width=3)
    if label: t(((a[0]+b[0])/2,(y0+y1)/2),label,f(fs or (24 if w>0.5 else 18)),INK)
low=[(0,1.2,1,"S1"),(1.2,0.4,11,"S11a"),
     (1.6,1.2,2,"S2"),(2.8,1.2,3,"S3"),(4.0,1.2,4,"S4"),(5.2,1.2,5,"S5"),
     (8.0,1.2,6,"S6"),(9.2,1.2,7,"S7"),(10.4,1.2,8,"S8"),(11.6,1.0,10,"S10"),
     (12.6,0.4,11,"S11b"),(13.0,1.2,9,"S9")]
for x,w,k,l in low: piece(x,w,y36,Yb,k,l)
# door top: one piece 1600 x 1200 from S12 (Gus, 2026-10-20)
piece(6.4,1.6,y36,yD,12,"S12  1600 x 1200",20)
d.rectangle([X0+6.4*s,yD,X0+8.0*s,Yb],fill="white",outline=INK,width=4)
d.line([(X0+6.4*s,yD),(X0+8.0*s,Yb)],fill=INK,width=3); d.line([(X0+8.0*s,yD),(X0+6.4*s,Yb)],fill=INK,width=3)
t((X0+7.2*s,yD+30),"ENTRY 1600 x 2400",f(20),INK)
tops=[(0,1.2,"T1"),(1.2,0.4,"T12")]+[(1.6+1.2*i,1.2,f"T{i+2}") for i in range(9)]+[(12.4,0.2,""),(12.6,0.4,"T12"),(13.0,1.2,"T11")]
for x,w,l in tops: piece(x,w,yT,y36,"T",l,18 if w<0.5 else 22)
for x in (1.6,12.6): d.line([(X0+x*s,yT-10),(X0+x*s,Yb+10)],fill=INK,width=7)
d.rectangle([X0,yT,X0+14.2*s,Yb],outline=INK,width=6)
def hd(xa,xb,y,lab):
    a,b=X0+xa*s,X0+xb*s; d.line([(a,y),(b,y)],fill=INK,width=2)
    for xx in (a,b): d.line([(xx,y-12),(xx,y+12)],fill=INK,width=2)
    t(((a+b)/2,y+22),lab,f(22),INK)
y=Yb+70
for a,b,l in [(0,1.6,"1600 return"),(1.6,6.4,"4800"),(6.4,8.0,"1600 entry"),(8.0,12.6,"4600"),(12.6,14.2,"1600 return")]: hd(a,b,y,l)
hd(0,14.2,y+70,"14200")
xr=X0+14.2*s+25
for ya,yb,l in [(yT,y36,"900"),(y36,Yb,"3600")]:
    d.line([(xr,ya),(xr,yb)],fill=INK,width=2); [d.line([(xr-12,yy),(xr+12,yy)],fill=INK,width=2) for yy in (ya,yb)]
    t((xr+12,(ya+yb)/2),l,f(22),INK,"lm")
# cutting plan
Y0=1180; cs=120
t((80,Y0-60),"CUTTING PLAN: the 12 sheets",f(28),GREY,"lm")
def sheet(i,cuts,note):
    x0=90+(i-1)*190; h=3.6*cs; w=1.2*cs
    d.rectangle([x0,Y0,x0+w,Y0+h],fill=(245,245,245),outline=INK,width=3)
    for cx,cw,cy,ch,key,l in cuts:
        a=(x0+cx*cs,Y0+cy*cs); b=(x0+(cx+cw)*cs,Y0+(cy+ch)*cs)
        d.rectangle([a,b],fill=COL[key] if key else (245,245,245),outline=INK,width=2)
        if l: t(((a[0]+b[0])/2,(a[1]+b[1])/2),l,f(16),INK)
    t((x0+w/2,Y0-20),f"S{i}",f(24),INK)
    for k,line in enumerate(note): t((x0+w/2,Y0+h+24+k*24),line,f(17,False),INK)
where=["L. return","front left","front left","front left","front left","front right","front right","front right","R. return"]
for i in range(1,10): sheet(i,[(0,1.2,0,3.6,i,"full")],["full",where[i-1]])
sheet(10,[(0,1.0,0,3.6,10,"1000"),(1.0,0.2,0,3.6,None,"")],["1000 front R","(200 spare)"])
sheet(11,[(0,0.4,0,3.6,11,"a"),(0.4,0.4,0,3.6,11,"b"),(0.8,0.4,0,3.6,None,"")],["a,b: returns","(400 spare)"])
sheet(12,[(0,1.2,2.0,1.6,12,"door"),(0,1.2,0,2.0,None,"")],["1600 x 1200","door top (turned)","(2000 spare)"])
t((80,Hc-40),"Tops T1 to T11 are full 1200 x 900. T12 is cut into 400 + 400 + 200 for the corners and the end of the front.",f(22,False),GREY,"lm")
im.save("/mnt/project-files/hoarding/FRED/FRED_melamine_layout.png")
