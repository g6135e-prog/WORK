import pymupdf, sys
from PIL import Image, ImageDraw
def render(pdf, pno, layers, dpi=200, mode='all', width=2):
    d=pymupdf.open(pdf); p=d[pno]; M=p.rotation_matrix; z=dpi/72
    W,H=int(round(p.rect.width*z)),int(round(p.rect.height*z))
    if p.rotation in (90,270): W,H=int(round(p.rect.height*z)),int(round(p.rect.width*z))
    im=Image.new('L',(W,H),255); g=ImageDraw.Draw(im)
    for dr in p.get_drawings():
        if dr.get('layer') not in layers: continue
        filled = dr['type'] in ('f','fs')
        if mode=='stroke' and dr['type']=='f': continue
        if mode=='fsonly' and dr['type']!='fs': continue
        if mode=='curb' and (dr['type']=='f' or (dr['type']=='fs' and dr.get('layer')=='01-7')): continue
        polys=[];cur=[]
        for it in dr['items']:
            if it[0]=='l': seg=[it[1],it[2]]
            elif it[0]=='c':
                a,b,c,e=it[1:5]; seg=[a*(1-t)**3+b*3*t*(1-t)**2+c*3*t*t*(1-t)+e*t**3 for t in [i/8 for i in range(9)]]
            elif it[0]=='re': r=it[1]; seg=[r.tl,r.tr,r.br,r.bl,r.tl]
            elif it[0]=='qu': q=it[1]; seg=[q.ul,q.ur,q.lr,q.ll,q.ul]
            else: continue
            seg=[(pt*M)*z for pt in seg]
            if cur and abs(cur[-1].x-seg[0].x)<0.5 and abs(cur[-1].y-seg[0].y)<0.5: cur+=seg[1:]
            else:
                if cur: polys.append(cur)
                cur=list(seg)
        if cur: polys.append(cur)
        for pl in polys:
            xy=[(q.x,q.y) for q in pl]
            if filled and len(xy)>2: g.polygon(xy,fill=0)
            else: g.line(xy,fill=0,width=width)
    return im
if __name__=='__main__':
    pdf,pno,out=sys.argv[1],int(sys.argv[2]),sys.argv[3]; layers=sys.argv[4].split(',')
    render(pdf,pno,layers).save(out)
