"""v5f standing-letter header '<NAME> PRs' on the updated (Order-2 Option A) bar.
usage: python3 make_header.py "MILES PRs" OUT_PREFIX   (e.g. OUT_PREFIX = ../ORDER_04_X/00_header_X_PRS)
needs: pip install trimesh manifold3d shapely fonttools uharfbuzz
Letters: Inter ExtraBold Italic, 21 mm cap height (auto-shrinks if too long), right-aligned,
3 speed lines from the left edge into the first letter (dropped if the name fills the width)."""
import sys, os, numpy as np, trimesh, manifold3d as mf, uharfbuzz as hb
import shapely.geometry as sg, shapely.affinity as sa
from shapely.ops import unary_union
from fontTools.ttLib import TTFont
from txt import P, glyph_poly
HERE=os.path.dirname(os.path.abspath(__file__))
FONT=os.path.join(HERE,'Inter-ExtraBoldItalic.otf')
if not os.path.exists(FONT): FONT='/usr/share/fonts/opentype/inter/Inter-ExtraBoldItalic.otf'
XS, TRACK, SPACE = 0.97, -0.03, 1.2
H_MAX, BASE, CLIP_Y, RIGHT, LEFT = 21.0, 7.89, 7.6, 77.0, -77.0
T_PLATE, T_FACE = 4.0, 0.6
STREAKS=[(7.6,12.36,-77.0),(16.42,19.78,-70.98),(24.4,27.76,-64.95)]  # y0,y1,left-x (at H=21)
SLANT=0.2101
MIN_SPEED=12.0   # need at least this much free width at the bottom streak, else no speed lines

f=TTFont(FONT); gset=f.getGlyphSet(); order=f.getGlyphOrder(); cap=f['OS/2'].sCapHeight; upm=f['head'].unitsPerEm
hfont=hb.Font(hb.Face(hb.Blob.from_file_path(FONT)))
def glyphs(s):
    buf=hb.Buffer(); buf.add_str(s); buf.guess_segment_properties(); hb.shape(hfont,buf,{})
    x=0; out=[]
    for i,p in zip(buf.glyph_infos,buf.glyph_positions):
        name=order[i.codepoint]; pen=P(gset); gset[name].draw(pen)
        if pen.c: out.append(sa.translate(glyph_poly(pen.c),x+p.x_offset,0))
        x+=p.x_advance*(SPACE if name=='space' else 1)+TRACK*upm
    return out
def lettering(s):
    gs=glyphs(s); H=H_MAX
    def place(H):
        k=H/cap; g=[sa.scale(q,k*XS,k,origin=(0,0)) for q in gs]
        u=unary_union(g); dx=RIGHT-u.bounds[2]
        return [sa.translate(q,dx,BASE) for q in g]
    g=place(H); w=unary_union(g).bounds
    if w[0]<LEFT:   # too long -> shrink
        H=H*(RIGHT-LEFT)/(w[2]-w[0]); g=place(H)
        g=[sa.translate(q,0,0) for q in g]
    letters=unary_union(g)
    first=sorted(g,key=lambda q:q.bounds[0])[0]
    parts=[letters]; speed=False
    k=H/H_MAX
    if first.bounds[0]-LEFT>=MIN_SPEED:
        speed=True
        st=min(1.0,(first.bounds[0]-LEFT)/30.5)   # shorter names: keep the stagger, shrink it to the free space
        for y0,y1,xl in STREAKS:
            xl=LEFT+(xl-LEFT)*st
            y0s=CLIP_Y+(y0-CLIP_Y)*k if y0>CLIP_Y else y0; y1s=CLIP_Y+(y1-CLIP_Y)*k
            band=first.intersection(sg.box(-200,y0s,200,y1s))
            xr=band.bounds[0]+2.0
            d=SLANT*(y1s-y0s)
            parts.append(sg.Polygon([(xl,y0s),(xr,y0s),(xr+d,y1s),(xl+d,y1s)]))
    L=unary_union(parts).intersection(sg.box(-79,CLIP_Y,79,60)).buffer(0)
    return L,H,speed
def to_manifold(mesh):
    return mf.Manifold(mf.Mesh(vert_properties=np.asarray(mesh.vertices,np.float32),tri_verts=np.asarray(mesh.faces,np.uint32)))
def extrude(poly,z0,z1):
    polys=list(getattr(poly,'geoms',[poly])); out=mf.Manifold()
    for p in polys:
        rings=[np.asarray(p.exterior.coords)[:-1]]+[np.asarray(i.coords)[:-1] for i in p.interiors]
        cs=mf.CrossSection([r.tolist() for r in rings],mf.FillRule.EvenOdd)
        out+=mf.Manifold.extrude(cs,z1-z0).translate([0,0,z0])
    return out
def save(m,path):
    me=m.to_mesh(); t=trimesh.Trimesh(me.vert_properties[:,:3],me.tri_verts,process=True)
    t.update_faces(t.nondegenerate_faces(height=1e-7)); t.remove_unreferenced_vertices(); t.merge_vertices()
    if not t.is_watertight: trimesh.repair.fill_holes(t)
    t.export(path); return t
def rrect_top(y0,y1=9.0,x=79.0,r=1.5):
    b=sg.box(-x,-9,x,y1).buffer(0)
    rr=sg.box(-x+r,-9,x-r,y1-r).buffer(r,resolution=24).union(sg.box(-x,-9,x,y1-r))
    return rr.intersection(sg.box(-x-1,y0,x+1,y1+1))
if __name__=='__main__':
    text,prefix=sys.argv[1],sys.argv[2]
    bar=sys.argv[3] if len(sys.argv)>3 else os.path.join(HERE,'header_bar_base_v5f.stl')
    A0=to_manifold(trimesh.load(bar))
    lower=A0^mf.Manifold.cube([200,200,20]).translate([-100,CLIP_Y-200,-5])   # bar below the letter line
    strip=extrude(rrect_top(CLIP_Y-0.4),0,T_PLATE)
    L,H,speed=lettering(text)
    A=lower+strip+extrude(L,0,T_PLATE)
    B=extrude(L,T_PLATE-0.01,T_PLATE+T_FACE)
    a=save(A,prefix+'_A_black_FACEUP.stl'); b=save(B,prefix+'_B_copper_raised.stl')
    print('letters %.1f mm, speed lines %s'%(H,speed),'A',a.is_watertight,np.round(a.bounds,2).tolist(),'B',b.is_watertight,np.round(b.bounds,2).tolist())
