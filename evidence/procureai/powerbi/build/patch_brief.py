import sys
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import os
F=os.environ.get('PROCUREAI_FONTS', os.path.join(os.path.dirname(__file__), 'fonts'))+'/'
MAN=F+'gfonts/ofl/manrope/Manrope[wght].ttf'; JBM=F+'JetBrainsMono/fonts/ttf/JetBrainsMono-Bold.ttf'
src,out=sys.argv[1],sys.argv[2]
img=Image.open(src).convert('RGBA'); a=np.array(img)
def tight(x0,y0,x1,y1,thr):
    sub=a[y0:y1,x0:x1,:3].astype(int); bg=sub[0,0]
    m=np.abs(sub-bg).sum(2)>thr; ys,xs=np.where(m)
    return x0+xs.min(),y0+ys.min(),x0+xs.max(),y0+ys.max()
def brightest(b):
    sub=a[b[1]:b[3]+1,b[0]:b[2]+1,:3].astype(int); i=sub.sum(2).argmax(); return tuple(sub.reshape(-1,3)[i])
def font(path,cap,text,weight=None):
    for s in np.arange(10,120,0.25):
        f=ImageFont.truetype(path,int(round(s*4))/4 if False else int(s)) if False else ImageFont.truetype(path,s)
        if weight: f.set_variation_by_axes([weight])
        bb=f.getbbox(text)
        if bb[3]-bb[1]>=cap: return f
def patch(region,new,path,weight=None,thr=60):
    b=tight(*region,thr); col=brightest(b); bgc=tuple(a[region[1],region[0],:3])
    print(region,'->bbox',b,'col',col,'bg',bgc)
    d=ImageDraw.Draw(img)
    d.rectangle([b[0]-2,b[1]-2,b[2]+2,b[3]+2],fill=bgc+(255,))
    f=font(path,b[3]-b[1]+1,new,weight); bb=f.getbbox(new)
    d.text((b[0]-bb[0],b[1]-bb[1]),new,font=f,fill=col+(255,))
patch((1900,1015,2030,1070),'29',MAN,800)
patch((2110,1015,2240,1070),'60',MAN,800)
patch((1700,1282,1730,1303),'49',JBM,None,40)
img.save(out)
