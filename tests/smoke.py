import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bpy
import proceedural_skin as addon

addon.register()
bpy.ops.mesh.primitive_cube_add()
obj = bpy.context.object
assert bpy.ops.proceedural_skin.apply() == {'FINISHED'}
mat = obj.active_material
assert mat.name == 'skin_Main'
nodes = mat.node_tree.nodes
assert len(nodes) == 6
for name, mode, factor, colors in [
    ('Blood', 'MIX', .5, ('4A080A', '9E0C10')),
    ('Base skin', 'MULTIPLY', .2, ('EAD1C5', None)),
    ('melanin', 'MIX', .4, ('1C1008', 'B26634')),
    ('Final blend', 'MULTIPLY', .5, (None, None)),
]:
    n = nodes[name]
    assert n.data_type == 'RGBA' and n.blend_type == mode
    assert abs(n.inputs[0].default_value - factor) < 1e-6
    for socket, color in zip((6, 7), colors):
        if color:
            assert all(abs(a-b) < 1e-6 for a,b in zip(n.inputs[socket].default_value, addon.hex_color(color)))
shader = next(n for n in nodes if n.type == 'BSDF_PRINCIPLED')
assert shader.subsurface_method == 'RANDOM_WALK_SKIN'
assert shader.inputs['Subsurface Weight'].default_value == 1
actual = {(l.from_node.name,l.from_socket.identifier,l.to_node.name,l.to_socket.identifier) for l in mat.node_tree.links}
expected = [(nodes['Blood'].outputs[2],nodes['Base skin'].inputs[7]),
            (nodes['Base skin'].outputs[2],nodes['Final blend'].inputs[6]),
            (nodes['melanin'].outputs[2],nodes['Final blend'].inputs[7]),
            (nodes['Final blend'].outputs[2],shader.inputs['Base Color']),
            (shader.outputs[0],next(n for n in nodes if n.type=='OUTPUT_MATERIAL').inputs['Surface'])]
assert actual == {(a.node.name,a.identifier,b.node.name,b.identifier) for a,b in expected}
assert all(p.material_index == obj.active_material_index for p in obj.data.polygons)
count = len(bpy.data.materials)
bpy.ops.proceedural_skin.apply()
assert obj.active_material == mat and len(obj.material_slots) == 1
assert len(bpy.data.materials) == count
other = obj.copy()
other.data = obj.data
bpy.context.collection.objects.link(other)
shared = other.data
bpy.ops.proceedural_skin.apply()
assert obj.data != shared and other.data == shared
# Existing user material must not be overwritten.
mat.name = 'Previous skin'
user = bpy.data.materials.new('skin_Main')
user.diffuse_color = (.1,.2,.3,1)
bpy.ops.proceedural_skin.apply()
assert obj.active_material != user
assert tuple(user.diffuse_color)[:3] != (0,0,0)
assert user.get('proceedural_skin_version') is None
bpy.context.view_layer.objects.active = None
assert not addon.PROCEEDURALSKIN_OT_apply.poll(bpy.context)
addon.unregister()
print('PASS: registration, shader values and links, assignment, reuse, shared mesh isolation, name collision, poll, unregister')
