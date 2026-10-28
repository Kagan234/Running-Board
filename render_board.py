import bpy, math, sys, os, mathutils
W=os.path.dirname(os.path.abspath(__file__))
argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
# usage: python3 render_board.py -- <header prefix> <rows folder> <out prefix> front,angle,close 96  (pip install bpy)
# env HDR_BOTTOM / HDR_TOP = header plate bottom / top edge in mm (bar header: -9 / 29.17, plate header: -19 / 19)
HDR=argv[0]; ROWDIR=argv[1]; OUTP=argv[2]; VIEWS=argv[3].split(',') if len(argv)>3 else ['front','angle','close']
SAMPLES=int(argv[4]) if len(argv)>4 else 96
ROWS=[('01_face_MARATHON','03:24:51'),('02_face_HALF_MARATHON','01:36:08'),('03_face_10_KM','00:43:27'),('04_face_5_KM_BOTTOM_ROW','00:20:54')]
HB=float(os.environ.get('HDR_BOTTOM','-9')); HT=float(os.environ.get('HDR_TOP','29.17'))
ROW_OFF=[HB-28.18-56.18*i for i in range(4)]
S=0.001
bpy.ops.wm.read_factory_settings(use_empty=True)
sc=bpy.context.scene
def mat(name,col,metal=0.0,rough=0.5,spec=0.5):
    m=bpy.data.materials.new(name); m.use_nodes=True; b=m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value=(*col,1); b.inputs['Metallic'].default_value=metal; b.inputs['Roughness'].default_value=rough
    try: b.inputs['Specular IOR Level'].default_value=spec
    except: pass
    return m
BLACK=mat('PLA_black',(0.011,0.011,0.012),0,0.55,0.4)
COPPER=mat('SilkCopper',(0.56,0.22,0.075),0.7,0.34)
WALL=mat('Wall',(0.50,0.49,0.47),0,0.85,0.3)
def imp(path,m,dy=0,name=None):
    bpy.ops.wm.stl_import(filepath=path)
    o=bpy.context.selected_objects[0]; o.data.materials.clear(); o.data.materials.append(m)
    o.scale=(S,S,S); o.location=(0,dy*S,0)
    if name: o.name=name
    return o
imp(HDR+'_A_black_FACEUP.stl',BLACK); imp(HDR+'_B_copper_raised.stl',COPPER)
SEG=None; DOT=None
def inst(src_path,m,x,y,rot,cache={}):
    if src_path not in cache:
        bpy.ops.wm.stl_import(filepath=src_path); o=bpy.context.selected_objects[0]
        o.data.materials.clear(); o.data.materials.append(m); cache[src_path]=o.data
        bpy.data.objects.remove(o)
    o=bpy.data.objects.new('p',cache[src_path]); sc.collection.objects.link(o)
    o.scale=(S,S,S); o.location=(x*S,y*S,0.5*S); o.rotation_euler=(0,0,rot); return o
DIG={'0':'abcdef','1':'bc','2':'abged','3':'abgcd','4':'fgbc','5':'afgcd','6':'afgedc','7':'abc','8':'abcdefg','9':'abcdfg'}
POS={'a':(0,10.4,'H'),'g':(0,-4.0,'H'),'d':(0,-18.4,'H'),'f':(-7.2,3.2,'V'),'b':(7.2,3.2,'V'),'e':(-7.2,-11.2,'V'),'c':(7.2,-11.2,'V')}
CX=[-61.8,-40.2,-10.8,10.8,40.2,61.8]
for (rn,t),dy in zip(ROWS,ROW_OFF):
    imp(f'{ROWDIR}/{rn}_A_black_FACEUP.stl',BLACK,dy); imp(f'{ROWDIR}/{rn}_B_copper_raised.stl',COPPER,dy)
    digits=t.replace(':','')
    for cx,dch in zip(CX,digits):
        for sname in DIG[dch]:
            px,py,o=POS[sname]
            inst(W+'/seg.stl',COPPER,cx+px,dy+py,0 if o=='V' else math.pi/2)
    for x in (-25.5,25.5):
        for y in (3.18,-11.18): inst(W+'/dot.stl',COPPER,x,dy+y,0)
# wall
bpy.ops.mesh.primitive_plane_add(size=2.0,location=(0,-0.1,-0.006)); wall=bpy.context.object; wall.data.materials.append(WALL)
# world
wd=bpy.data.worlds.new('w'); sc.world=wd; wd.use_nodes=True; wd.node_tree.nodes['Background'].inputs[0].default_value=(0.52,0.51,0.49,1); wd.node_tree.nodes['Background'].inputs[1].default_value=0.10
def area(loc,size,energy,rot_target=(0,-0.1,0)):
    l=bpy.data.lights.new('a','AREA'); l.size=size; l.energy=energy
    o=bpy.data.objects.new('a',l); sc.collection.objects.link(o); o.location=loc
    d=mathutils.Vector(rot_target)-mathutils.Vector(loc); o.rotation_euler=d.to_track_quat('-Z','Y').to_euler()
area((-0.35,0.35,0.55),0.45,6.5)
area((0.45,-0.1,0.5),0.6,2)
cam_d=bpy.data.cameras.new('c'); cam=bpy.data.objects.new('c',cam_d); sc.collection.objects.link(cam); sc.camera=cam
sc.render.engine='CYCLES'; sc.cycles.samples=SAMPLES; sc.cycles.use_denoising=True
try: sc.cycles.denoiser='OPENIMAGEDENOISE'
except: pass
sc.cycles.use_adaptive_sampling=True; sc.cycles.max_bounces=6
sc.view_settings.view_transform='AgX' if 'AgX' in [i.identifier for i in sc.view_settings.bl_rna.properties['view_transform'].enum_items] else 'Filmic'
sc.view_settings.look='None'
sc.render.image_settings.file_format='JPEG'; sc.render.image_settings.quality=92
CY=(HT+ROW_OFF[-1]-28.18)/2*S
def look(loc,target,lens):
    cam.location=loc; f=(mathutils.Vector(target)-mathutils.Vector(loc)).normalized()
    r=f.cross(mathutils.Vector((0,1,0))).normalized(); u=r.cross(f)
    M=mathutils.Matrix((r,u,-f)).transposed(); cam.rotation_euler=M.to_euler(); cam_d.lens=lens
views={'front':((0,CY,0.6),(0,CY,0),62,1200,1600),
       'angle':((-0.34,CY+0.04,0.58),(0.0,CY-0.004,0),60,1280,1600),
       'close':((-0.16,0.06,0.24),(0.004,-0.012,0),50,1600,1040)}
for v in VIEWS:
    loc,tg,lens,rx,ry=views[v]; look(loc,tg,lens); sc.render.resolution_x=rx; sc.render.resolution_y=ry; sc.render.resolution_percentage=100
    sc.render.filepath=f'{OUTP}_{v}.jpg'; bpy.ops.render.render(write_still=True); print('wrote',sc.render.filepath)
