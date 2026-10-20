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
assert len(nodes) == 11
for name, value in [('Scale',10000),('Detail',1),('Roughness',1),('Lacunarity',2),('Distortion',0)]:
    assert abs(nodes['Pores noise'].inputs[name].default_value-value) < 1e-6
for name, value in [('Value',1),('From Min',.5),('From Max',.8),('To Min',0),('To Max',1)]:
    assert abs(nodes['Pores range'].inputs[name].default_value-value) < 1e-6
assert nodes['Pores strength'].data_type == 'FLOAT'
assert nodes['Pores strength'].inputs[2].default_value == 0
assert nodes['Pores strength'].inputs[0].default_value == .5
assert nodes['Pores'].data_type == 'RGBA' and nodes['Pores'].blend_type == 'MIX'
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
            (nodes['Final blend'].outputs[2],nodes['Pores'].inputs[6]),
            (nodes['melanin'].outputs[2],nodes['Pores'].inputs[7]),
            (nodes['Pores noise'].outputs['Fac'],nodes['Pores range'].inputs['Value']),
            (nodes['Pores range'].outputs['Result'],nodes['Pores strength'].inputs[3]),
            (nodes['Pores strength'].outputs[0],nodes['Pores'].inputs[0]),
            (nodes['Pores'].outputs[2],shader.inputs['Base Color']),
            (nodes['Pores strength'].outputs[0],nodes['Pores bump'].inputs['Strength']),
            (nodes['Pores range'].outputs['Result'],nodes['Pores bump'].inputs['Height']),
            (nodes['Pores bump'].outputs['Normal'],shader.inputs['Normal']),
            (shader.outputs[0],next(n for n in nodes if n.type=='OUTPUT_MATERIAL').inputs['Surface'])]
assert actual == {(a.node.name,a.identifier,b.node.name,b.identifier) for a,b in expected}
assert all(p.material_index == obj.active_material_index for p in obj.data.polygons)
# Capture the panel's actual RNA bindings and edit those Blender sockets.
class CaptureLayout:
    def __init__(self):
        self.bindings = []
    def label(self, **kwargs):
        pass
    def operator(self, *args, **kwargs):
        pass
    def column(self, **kwargs):
        return self
    def row(self):
        return self
    def prop(self, data, property_name, **kwargs):
        assert property_name == 'default_value' and kwargs['slider']
        self.bindings.append((kwargs['text'], data))

from types import SimpleNamespace
layout = CaptureLayout()
addon.PROCEEDURALSKIN_PT_panel.draw(SimpleNamespace(layout=layout), bpy.context)
assert [label for label, socket in layout.bindings] == ['Intensity', 'Tone', 'Flush', 'Perfusion', 'Pores']
for (label, socket), node_name, value in zip(layout.bindings,
        ['Final blend', 'melanin', 'Base skin', 'Blood', 'Pores strength'], [.15, .75, .35, .9, .65]):
    assert socket == nodes[node_name].inputs[0]
    socket.default_value = value
    assert abs(nodes[node_name].inputs[0].default_value - value) < 1e-6
    assert socket.bl_rna.properties['default_value'].hard_min == 0
    assert socket.bl_rna.properties['default_value'].hard_max == 1
# Reapply must preserve all slider edits.
bpy.ops.proceedural_skin.apply()
for node_name, value in zip(['Final blend', 'melanin', 'Base skin', 'Blood', 'Pores strength'], [.15, .75, .35, .9, .65]):
    assert abs(nodes[node_name].inputs[0].default_value - value) < 1e-6

# Simulate upgrading a v0.2 material, preserving the four existing factors.
for name in ['Pores noise','Pores range','Pores strength','Pores','Pores bump']:
    nodes.remove(nodes[name])
mat['proceedural_skin_version'] = 1
mat.node_tree.links.new(nodes['Final blend'].outputs[2], shader.inputs['Base Color'])
bpy.ops.proceedural_skin.apply()
assert mat['proceedural_skin_version'] == 2 and len(nodes) == 11
for name, value in zip(['Final blend','melanin','Base skin','Blood'], [.15,.75,.35,.9]):
    assert abs(nodes[name].inputs[0].default_value-value) < 1e-6
# Zero Pores disables both the color interpolation and bump strength.
nodes['Pores strength'].inputs[0].default_value = 0
assert nodes['Pores strength'].inputs[2].default_value == 0
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
obj.active_material = user
bpy.ops.proceedural_skin.apply()
assert obj.active_material != user
assert tuple(user.diffuse_color)[:3] != (0,0,0)
assert user.get('proceedural_skin_version') is None
bpy.context.view_layer.objects.active = None
assert not addon.PROCEEDURALSKIN_OT_apply.poll(bpy.context)
# Missing/renamed nodes and no active object must draw without exceptions.
current = obj.active_material.node_tree.nodes.get('Blood')
obj.active_material.node_tree.nodes.remove(current)
bpy.context.view_layer.objects.active = obj
addon.PROCEEDURALSKIN_PT_panel.draw(SimpleNamespace(layout=CaptureLayout()), bpy.context)
bpy.context.view_layer.objects.active = None
addon.PROCEEDURALSKIN_PT_panel.draw(SimpleNamespace(layout=CaptureLayout()), bpy.context)
addon.unregister()
print('PASS: registration, shader values and links, assignment, reuse, shared mesh isolation, name collision, five slider bindings and edits, preserved values, missing nodes, poll, unregister')
