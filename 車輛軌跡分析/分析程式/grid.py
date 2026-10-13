import sys
from PIL import Image, ImageDraw, ImageFont
src,x0,y0,x1,y1,out=sys.argv[1],*map(int,sys.argv[2:6]),sys.argv[6]
step=int(sys.argv[7]) if len(sys.argv)>7 else 100
im=Image.open(src).convert('RGB').crop((x0,y0,x1,y1))
d=ImageDraw.Draw(im)
f=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',18) if True else None
for x in range((x0//step+1)*step,x1,step):
    d.line([(x-x0,0),(x-x0,y1-y0)],fill=(255,0,0) if x%500==0 else (255,170,170),width=1)
    d.text((x-x0+2,2),str(x),fill=(200,0,0),font=f)
for y in range((y0//step+1)*step,y1,step):
    d.line([(0,y-y0),(x1-x0,y-y0)],fill=(255,0,0) if y%500==0 else (255,170,170),width=1)
    d.text((2,y-y0+2),str(y),fill=(200,0,0),font=f)
im.save(out)
