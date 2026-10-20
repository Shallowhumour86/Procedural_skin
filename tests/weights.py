"""Evaluate actual modifier attributes and render the weighted shader on CPU."""
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bpy
import proceedural_skin as addon
addon.register()
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.mesh.primitive_plane_add(size=2)
obj = bpy.context.object
bpy.ops.proceedural_skin.apply()
bpy.ops.proceedural_skin.create_group()
entry = obj.proceedural_skin_groups[0]
vg = obj.vertex_groups[entry.group_name]

def evaluated_weights():
    obj.data.update()
    obj.update_tag(refresh={'DATA'})
    bpy.context.view_layer.update()
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    try:
        assert mesh.attributes['ps_weight_1'].domain == 'POINT'
        assert mesh.attributes['ps_weight_1'].data_type == 'FLOAT'
        assert all(mesh.materials[p.material_index].original == obj.proceedural_skin_blend for p in mesh.polygons)
        return [v.value for v in mesh.attributes['ps_weight_1'].data]
    finally:
        evaluated.to_mesh_clear()

assert evaluated_weights() == [0]*4
for index, value in enumerate((0,.25,.5,1)):
    vg.add([index], value, 'REPLACE')
assert evaluated_weights() == [0,.25,.5,1]
# Updating weights alone must update evaluated geometry (no rebuild/operator).
vg.add([0,1,2,3], .75, 'REPLACE')
assert evaluated_weights() == [.75]*4
# A removed vertex group safely becomes zero influence.
obj.vertex_groups.remove(vg)
assert evaluated_weights() == [0]*4
vg = obj.vertex_groups.new(name=entry.group_name)
# Exercise Blender's Edit Mode Assign operation, not only direct weight API writes.
obj.vertex_groups.active_index = vg.index
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.context.scene.tool_settings.vertex_group_weight = .35
bpy.ops.object.vertex_group_assign()
bpy.ops.object.mode_set(mode='OBJECT')
assert all(abs(v-.35)<1e-6 for v in evaluated_weights())
# Replace the test shader bodies with flat emission colors to measure mixing.
for mat,color in [(obj.proceedural_skin_main,(1,0,0,1)), (entry.material,(0,0,1,1))]:
    tree = addon.skin_tree(mat)
    tree.nodes.clear()
    emission = tree.nodes.new('ShaderNodeEmission')
    emission.inputs['Color'].default_value = color
    output = tree.nodes.new('NodeGroupOutput')
    tree.links.new(emission.outputs[0],output.inputs['Shader'])
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 128
scene.cycles.use_denoising = False
scene.render.resolution_x = scene.render.resolution_y = 16
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'OPEN_EXR'
bpy.ops.object.camera_add(location=(0,0,3))
scene.camera = bpy.context.object
scene.camera.data.type = 'ORTHO'
scene.camera.data.ortho_scale = 1
with tempfile.TemporaryDirectory() as tmp:
    for weight in (0,.5,1):
        vg.add([0,1,2,3],weight,'REPLACE')
        assert all(abs(v-weight)<1e-6 for v in evaluated_weights())
        scene.render.filepath = str(Path(tmp)/f'{weight}.exr')
        bpy.ops.render.render(write_still=True)
        image = bpy.data.images.load(scene.render.filepath,check_existing=False)
        pixels = list(image.pixels)
        red = sum(pixels[i] for i in range(0,len(pixels),4))/(len(pixels)/4)
        blue = sum(pixels[i+2] for i in range(0,len(pixels),4))/(len(pixels)/4)
        bpy.data.images.remove(image)
        assert abs(red-(1-weight))<.08 and abs(blue-weight)<.08,(weight,red,blue)
        print(f'RENDER PASS: weight={weight}, red={red:.3f}, blue={blue:.3f}')
# Overlapping groups layer in order: main .25, first .25, second .5.
bpy.context.view_layer.objects.active = obj
obj.select_set(True)
bpy.ops.proceedural_skin.create_group()
second = obj.proceedural_skin_groups[1]
second_group = obj.vertex_groups[second.group_name]
vg.add([0,1,2,3], .5, 'REPLACE')
second_group.add([0,1,2,3], .5, 'REPLACE')
tree = addon.skin_tree(second.material)
tree.nodes.clear()
emission = tree.nodes.new('ShaderNodeEmission')
emission.inputs['Color'].default_value = (0,1,0,1)
output = tree.nodes.new('NodeGroupOutput')
tree.links.new(emission.outputs[0],output.inputs['Shader'])
obj.update_tag(refresh={'DATA'})
bpy.context.view_layer.update()
with tempfile.TemporaryDirectory() as tmp:
    scene.render.filepath = str(Path(tmp)/'overlap.exr')
    bpy.ops.render.render(write_still=True)
    image = bpy.data.images.load(scene.render.filepath,check_existing=False)
    pixels = list(image.pixels)
    means = [sum(pixels[i+c] for i in range(0,len(pixels),4))/(len(pixels)/4) for c in range(3)]
    assert all(abs(a-b)<.08 for a,b in zip(means,(.25,.5,.25))), means
    bpy.data.images.remove(image)
    print('RENDER PASS: overlapping layers', means)
addon.unregister()
print('PASS: live named attributes, absent/deleted weights, automatic material, actual shader blending at 0/0.5/1')
