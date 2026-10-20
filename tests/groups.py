"""Integration checks for groups, independent settings, panels and .blend persistence."""
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bpy
import proceedural_skin as addon
addon.register()
bpy.ops.mesh.primitive_cube_add()
obj = bpy.context.object
bpy.ops.proceedural_skin.apply()
main = obj.proceedural_skin_main
vg = obj.vertex_groups['skin_main']
assert all(vg.weight(v.index) == 1 for v in obj.data.vertices)
bpy.ops.proceedural_skin.apply()
assert len(obj.vertex_groups) == 1
main.node_tree.nodes['Blood'].inputs[0].default_value = .73
main.proceedural_skin_pores_size = 4
for i in range(1, 11):
    assert addon.PROCEEDURALSKIN_OT_create_group.poll(bpy.context)
    assert bpy.ops.proceedural_skin.create_group() == {'FINISHED'}
    entry = obj.proceedural_skin_groups[-1]
    assert entry.group_name == f'Skin_group {i}'
    group = obj.vertex_groups[entry.group_name]
    assert not any(g.group == group.index for v in obj.data.vertices for g in v.groups)
    assert entry.material != main and entry.material.node_tree != main.node_tree
    assert entry.material in list(obj.data.materials)
    assert abs(entry.material.node_tree.nodes['Blood'].inputs[0].default_value - .73) < 1e-6
    assert entry.material.proceedural_skin_pores_size == 4
assert not addon.PROCEEDURALSKIN_OT_create_group.poll(bpy.context)
materials = [e.material for e in obj.proceedural_skin_groups]
materials[0].node_tree.nodes['Blood'].inputs[0].default_value = .12
materials[0].proceedural_skin_pores_size = 9
assert main.proceedural_skin_pores_size == 4 and materials[1].proceedural_skin_pores_size == 4
assert abs(materials[1].node_tree.nodes['Blood'].inputs[0].default_value - .73) < 1e-6
# Simulate v0.5 materials; Apply must upgrade the main and all ten group graphs.
for material in [main] + materials:
    material['proceedural_skin_version'] = 4
    tree = material.node_tree
    for link in list(tree.nodes['Pores strength'].inputs[0].links):
        tree.links.remove(link)
# Reapplying with a group material active still targets the main material.
obj.active_material_index = 1
bpy.ops.proceedural_skin.apply()
assert obj.active_material == main and len(obj.proceedural_skin_groups) == 10
assert len(obj.vertex_groups) == 11
for material in [main] + materials:
    tree = material.node_tree
    for socket_index in (0, 3):
        links = tree.nodes['Pores strength'].inputs[socket_index].links
        assert len(links) == 1
        assert links[0].from_node == tree.nodes['Pores range']
        assert links[0].from_socket == tree.nodes['Pores range'].outputs['Result']
    assert material['proceedural_skin_version'] == 5

class Layout:
    def __init__(self):
        self.sliders = []
        self.sections = []
    def box(self): return self
    def row(self): return self
    def column(self, **kwargs): return self
    def label(self, **kwargs): pass
    def operator(self, *args, **kwargs): pass
    def prop(self, data, name, **kwargs):
        if kwargs.get('slider'):
            self.sliders.append(kwargs['text'])
        else:
            self.sections.append(kwargs['text'])
layout = Layout()
addon.PROCEEDURALSKIN_PT_panel.draw(SimpleNamespace(layout=layout), bpy.context)
assert len(layout.sliders) == 66 and len(layout.sections) == 11
obj.proceedural_skin_main_expanded = False
for entry in obj.proceedural_skin_groups:
    entry.expanded = False
layout = Layout()
addon.PROCEEDURALSKIN_PT_panel.draw(SimpleNamespace(layout=layout), bpy.context)
assert len(layout.sliders) == 0 and len(layout.sections) == 11
# Persist group references, collapse state and independent settings.
name = obj.name
with tempfile.TemporaryDirectory() as tmp:
    path = str(Path(tmp) / 'groups.blend')
    bpy.ops.wm.save_as_mainfile(filepath=path)
    bpy.ops.wm.open_mainfile(filepath=path)
    obj = bpy.data.objects[name]
    assert len(obj.proceedural_skin_groups) == 10
    assert obj.proceedural_skin_main.proceedural_skin_pores_size == 4
    assert obj.proceedural_skin_groups[0].material.proceedural_skin_pores_size == 9
    assert not obj.proceedural_skin_main_expanded
    assert all(obj.vertex_groups['skin_main'].weight(v.index) == 1 for v in obj.data.vertices)
addon.unregister()
print('PASS: main weights, 10 empty groups, copied and independent materials, limit, reapply, collapsible controls, save/reopen')
