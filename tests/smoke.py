import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bpy
import proceedural_skin as addon
addon.register()
bpy.ops.mesh.primitive_cube_add()
obj = bpy.context.object
assert bpy.ops.proceedural_skin.apply() == {'FINISHED'}
mat = obj.proceedural_skin_main
nodes = addon.skin_tree(mat).nodes
assert len(nodes) == 12  # eleven shader nodes plus group output
for name, mode, factor, colors in [
    ('Blood','MIX',.5,('4A080A','9E0C10')),
    ('Base skin','MULTIPLY',.2,('EAD1C5',None)),
    ('melanin','MIX',.4,('1C1008','B26634')),
    ('Final blend','MULTIPLY',.5,(None,None)),
]:
    n = nodes[name]
    assert n.data_type == 'RGBA' and n.blend_type == mode
    assert abs(n.inputs[0].default_value-factor) < 1e-6
    for socket, color in zip((6,7),colors):
        if color:
            assert all(abs(a-b)<1e-6 for a,b in zip(n.inputs[socket].default_value,addon.hex_color(color)))
for name,value in [('Scale',10000),('Detail',1),('Roughness',1),('Lacunarity',2),('Distortion',0)]:
    assert abs(nodes['Pores noise'].inputs[name].default_value-value)<1e-6
for name,value in [('From Min',.5),('From Max',.8),('To Min',1),('To Max',0)]:
    assert abs(nodes['Pores range'].inputs[name].default_value-value)<1e-6
shader = next(n for n in nodes if n.type == 'BSDF_PRINCIPLED')
assert shader.subsurface_method == 'RANDOM_WALK_SKIN'
assert shader.inputs['Subsurface Weight'].default_value == 1
for source,output,target,input_ in [
    ('Pores range','Result','Pores strength',0),
    ('Pores range','Result','Pores strength',3),
    ('melanin',2,'Pores',6), ('Final blend',2,'Pores',7),
    ('Final blend',2,'pores colour',6), ('Pores',2,'pores colour',7),
    ('pores colour',2,shader.name,'Base Color'),
    ('Pores bump','Normal',shader.name,'Normal'),
]:
    link = nodes[target].inputs[input_].links[0]
    assert link.from_node == nodes[source] and link.from_socket == nodes[source].outputs[output]
assert nodes['pores colour'].inputs[0].default_value == 1
assert not nodes['pores colour'].inputs[0].is_linked
assert addon.FACTOR_CONTROLS[-1] == ('pores colour','pores colour')
for i in range(21):
    mat.proceedural_skin_pores_size = i/2
    assert nodes['Pores noise'].inputs['Scale'].default_value == 10000-900*i/2
mat.proceedural_skin_pores_size = 3.3
assert mat.proceedural_skin_pores_size == 3.5
nodes['pores colour'].inputs[0].default_value = .23
count = len(bpy.data.node_groups)
bpy.ops.proceedural_skin.apply()
assert abs(nodes['pores colour'].inputs[0].default_value-.23)<1e-6
assert len(bpy.data.node_groups) == count
assert len([m for m in obj.modifiers if m.type=='NODES']) == 1
# Current migration preserves existing controls and adds the new node once.
addon.skin_tree(mat).nodes.remove(nodes['pores colour'])
mat['proceedural_skin_version'] = 5
bpy.ops.proceedural_skin.apply()
assert mat['proceedural_skin_version'] == 6
assert addon.skin_tree(mat).nodes.get('pores colour')
# Linked mesh data is isolated and an unrelated same-name material is retained.
other = obj.copy(); other.data = obj.data
bpy.context.collection.objects.link(other)
shared = other.data
bpy.ops.proceedural_skin.apply()
assert obj.data != shared
bpy.context.view_layer.objects.active = None
assert not addon.PROCEEDURALSKIN_OT_apply.poll(bpy.context)
addon.unregister()
print('PASS: shader colors and factors, pore links, pores colour control, inverse pore size, migration, idempotence, shared geometry isolation')
