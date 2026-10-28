from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.basePen import BasePen
import shapely.geometry as sg, shapely.affinity as sa
from shapely.ops import unary_union
import numpy as np
class P(BasePen):
    def __init__(s,gs): super().__init__(gs); s.c=[]; s.cur=[]
    def _moveTo(s,p): s.cur=[p]
    def _lineTo(s,p): s.cur.append(p)
    def _curveToOne(s,a,b,c):
        p0=np.array(s.cur[-1]);A,B,C=map(np.array,(a,b,c))
        for t in np.linspace(0,1,12)[1:]:
            s.cur.append(tuple((1-t)**3*p0+3*(1-t)**2*t*A+3*(1-t)*t*t*B+t**3*C))
    def _qCurveToOne(s,a,b):
        p0=np.array(s.cur[-1]);A,B=map(np.array,(a,b))
        for t in np.linspace(0,1,10)[1:]:
            s.cur.append(tuple((1-t)**2*p0+2*(1-t)*t*A+t*t*B))
    def _closePath(s):
        if len(s.cur)>2: s.c.append(s.cur)
        s.cur=[]
    _endPath=_closePath
def glyph_poly(rings):
    # even-odd assembly
    polys=[sg.Polygon(r).buffer(0) for r in rings]
    res=sg.Polygon()
    for p in sorted(polys,key=lambda p:-p.area):
        res=res.symmetric_difference(p)
    return res
_cache={}
def text(s,font,kern=True,track=0.0):
    if font not in _cache: _cache[font]=TTFont(font)
    f=_cache[font]; gs=f.getGlyphSet(); cmap=f.getBestCmap(); hm=f['hmtx']
    x=0; out=[]; upm=f['head'].unitsPerEm
    for ch in s:
        g=cmap[ord(ch)]
        pen=P(gs); gs[g].draw(pen)
        if pen.c: out.append(sa.translate(glyph_poly(pen.c),x,0))
        x+=hm[g][0]+track*upm
    return unary_union(out), f['OS/2'].sCapHeight, upm
