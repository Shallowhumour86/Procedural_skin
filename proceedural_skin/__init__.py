bl_info = {
    "name": "Proceedural skin",
    "author": "Proceedural skin contributors",
    "version": (0, 7, 0),
    "blender": (4, 4, 1),
    "location": "View3D > Sidebar > Proceedural skin",
    "description": "Create procedural skin and blend skin regions using vertex weights",
    "category": "Material",
}

import bpy
from .blending import skin_tree, shader_group, rebuild_blending
import math
from bpy.props import FloatProperty, BoolProperty, PointerProperty, CollectionProperty, StringProperty


FACTOR_CONTROLS = (
    ("Intensity", "Final blend"),
    ("Tone", "melanin"),
    ("Flush", "Base skin"),
    ("Perfusion", "Blood"),
    ("pores colour", "pores colour"),
)


def hex_color(value):
    """Convert the requested display (sRGB) hex color into scene linear RGBA."""
    channels = [int(value[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
                 for c in channels) + (1.0,)


def pore_size_get(material):
    node = skin_tree(material).nodes.get('Pores noise') if skin_tree(material) else None
    if node is None or node.bl_idname != 'ShaderNodeTexNoise':
        return 0.0
    return max(0.0, min(10.0, (10000.0 - node.inputs['Scale'].default_value) / 900.0))


def pore_size_set(material, value):
    node = skin_tree(material).nodes.get('Pores noise') if skin_tree(material) else None
    if node is not None and node.bl_idname == 'ShaderNodeTexNoise':
        # Snap typed values as well as mouse edits to half-unit steps.
        value = math.floor(max(0.0, min(10.0, value)) * 2 + 0.5) / 2
        node.inputs['Scale'].default_value = 10000.0 - 900.0 * value


def upgrade_pore_range(material):
    version = material.get('proceedural_skin_version', 1)
    if version >= 6:
        return
    nodes = skin_tree(material).nodes
    mapping = nodes.get('Pores range')
    pores = nodes.get('Pores')
    melanin = nodes.get('melanin')
    final = nodes.get('Final blend')
    strength = nodes.get('Pores strength')
    if (mapping is None or mapping.bl_idname != 'ShaderNodeMapRange'
            or pores is None or pores.bl_idname != 'ShaderNodeMix'
            or melanin is None or final is None
            or strength is None or strength.bl_idname != 'ShaderNodeMix'
            or strength.data_type != 'FLOAT'):
        raise ValueError('Cannot upgrade pores: required pore or color nodes are missing')
    if version < 3:
        mapping.inputs['To Min'].default_value = 1.0
        mapping.inputs['To Max'].default_value = 0.0
    if version < 4:
        skin_tree(material).links.new(melanin.outputs[2], pores.inputs[6])
        skin_tree(material).links.new(final.outputs[2], pores.inputs[7])
    skin_tree(material).links.new(mapping.outputs['Result'], strength.inputs[0])
    colour = nodes.get('pores colour')
    if colour is None:
        colour = nodes.new('ShaderNodeMix')
        colour.inputs[0].default_value = 1.0
    colour.name = colour.label = 'pores colour'
    colour.data_type = 'RGBA'
    colour.blend_type = 'MIX'
    colour.location = (180, 460)
    shader = next(n for n in nodes if n.type == 'BSDF_PRINCIPLED')
    skin_tree(material).links.new(final.outputs[2], colour.inputs[6])
    skin_tree(material).links.new(pores.outputs[2], colour.inputs[7])
    skin_tree(material).links.new(colour.outputs[2], shader.inputs['Base Color'])
    material['proceedural_skin_version'] = 6


def add_pore_nodes(material):
    """Upgrade our original graph once, preserving existing color factors."""
    if material.get("proceedural_skin_version") in (2, 3, 4, 5, 6):
        upgrade_pore_range(material)
        return
    nodes = skin_tree(material).nodes
    links = skin_tree(material).links
    final = nodes.get("Final blend")
    melanin = nodes.get("melanin")
    shader = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if final is None or melanin is None or shader is None:
        raise ValueError("Cannot add pores: Final blend, melanin or Principled BSDF is missing")
    noise = nodes.new('ShaderNodeTexNoise')
    noise.name = noise.label = 'Pores noise'
    noise.location = (-900, -500)
    for name, value in [('Scale', 10000), ('Detail', 1), ('Roughness', 1),
                        ('Lacunarity', 2), ('Distortion', 0)]:
        noise.inputs[name].default_value = value
    mapping = nodes.new('ShaderNodeMapRange')
    mapping.name = mapping.label = 'Pores range'
    mapping.location = (-650, -500)
    for name, value in [('Value', 1), ('From Min', .5), ('From Max', .8),
                        ('To Min', 0), ('To Max', 1)]:
        mapping.inputs[name].default_value = value
    strength = nodes.new('ShaderNodeMix')
    strength.name = strength.label = 'Pores strength'
    strength.data_type = 'FLOAT'
    strength.inputs[0].default_value = .5
    strength.inputs[2].default_value = 0
    strength.location = (-400, -400)
    pores = nodes.new('ShaderNodeMix')
    pores.name = pores.label = 'Pores'
    pores.data_type = 'RGBA'
    pores.blend_type = 'MIX'
    pores.location = (-100, 260)
    bump = nodes.new('ShaderNodeBump')
    bump.name = bump.label = 'Pores bump'
    bump.location = (-100, -250)
    shader.location = (200, 260)
    for n in nodes:
        if n.type == 'OUTPUT_MATERIAL':
            n.location = (560, 260)
    links.new(noise.outputs['Fac'], mapping.inputs['Value'])
    links.new(mapping.outputs['Result'], strength.inputs[3])
    links.new(final.outputs[2], pores.inputs[7])
    links.new(melanin.outputs[2], pores.inputs[6])
    links.new(strength.outputs[0], pores.inputs[0])
    links.new(pores.outputs[2], shader.inputs['Base Color'])
    links.new(strength.outputs[0], bump.inputs['Strength'])
    links.new(mapping.outputs['Result'], bump.inputs['Height'])
    links.new(bump.outputs['Normal'], shader.inputs['Normal'])
    material['proceedural_skin_version'] = 2
    upgrade_pore_range(material)


def create_skin_material(material=None):
    # Reuse only our own material; never erase a user's same-named material.
    if material is None or material.get("proceedural_skin_version") not in (1, 2, 3, 4, 5, 6):
        material = bpy.data.materials.get("skin_Main")
    if material is not None and material.get("proceedural_skin_version") in (1, 2, 3, 4, 5, 6):
        add_pore_nodes(material)
        return material
    material = bpy.data.materials.new("skin_Main")
    material.use_nodes = True
    nodes = skin_tree(material).nodes
    links = skin_tree(material).links
    nodes.clear()

    def mix(name, mode, factor, color_a=None, color_b=None, location=(0, 0)):
        node = nodes.new("ShaderNodeMix")
        node.name = name
        node.label = name
        node.data_type = 'RGBA'
        node.blend_type = mode
        node.inputs[0].default_value = factor
        # ShaderNodeMix's RGBA sockets are indices 6 and 7 in Blender 4.4.
        if color_a:
            node.inputs[6].default_value = hex_color(color_a)
        if color_b:
            node.inputs[7].default_value = hex_color(color_b)
        node.location = location
        node.width = 200
        return node

    blood = mix("Blood", 'MIX', 0.5, "4A080A", "9E0C10", (-900, 260))
    base = mix("Base skin", 'MULTIPLY', 0.2, "EAD1C5", location=(-620, 260))
    melanin = mix("melanin", 'MIX', 0.4, "1C1008", "B26634", (-620, -100))
    final = mix("Final blend", 'MULTIPLY', 0.5, location=(-330, 260))
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    shader.location = (0, 260)
    shader.subsurface_method = 'RANDOM_WALK_SKIN'
    shader.inputs['Subsurface Weight'].default_value = 1.0
    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (360, 260)
    output.is_active_output = True
    links.new(blood.outputs[2], base.inputs[7])
    links.new(base.outputs[2], final.inputs[6])
    links.new(melanin.outputs[2], final.inputs[7])
    links.new(final.outputs[2], shader.inputs['Base Color'])
    links.new(shader.outputs['BSDF'], output.inputs['Surface'])
    material['proceedural_skin_version'] = 1
    add_pore_nodes(material)
    return material


class PROCEEDURALSKIN_OT_apply(bpy.types.Operator):
    bl_idname = "proceedural_skin.apply"
    bl_label = "Apply skin_Main"
    bl_description = "Apply skin to every face of the active mesh; retain other material slots"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj is not None and obj.type == 'MESH' and context.mode == 'OBJECT'
                and obj.is_editable and obj.data.is_editable)

    def execute(self, context):
        obj = context.active_object
        try:
            material = create_skin_material(obj.proceedural_skin_main or obj.active_material)
            for entry in obj.proceedural_skin_groups:
                if entry.material is not None:
                    add_pore_nodes(entry.material)
        except ValueError as error:
            self.report({'ERROR'}, str(error))
            return {'CANCELLED'}
        # Isolate shared geometry so other objects keep their material assignments.
        if obj.data.users > 1:
            obj.data = obj.data.copy()
        index = next((i for i, slot in enumerate(obj.material_slots)
                      if slot.material == material), None)
        if index is None:
            obj.data.materials.append(material)
            index = len(obj.material_slots) - 1
        for face in obj.data.polygons:
            face.material_index = index
        obj.active_material_index = index
        obj.proceedural_skin_main = material
        group = obj.vertex_groups.get('skin_main')
        if group is None:
            group = obj.vertex_groups.new(name='skin_main')
        if obj.data.vertices and not obj.get("proceedural_skin_initialized"):
            group.add([v.index for v in obj.data.vertices], 1.0, 'REPLACE')
        obj['proceedural_skin_initialized'] = True
        rebuild_blending(obj)
        self.report({'INFO'}, f"Applied {material.name} to {obj.name}")
        return {'FINISHED'}


class PROCEEDURALSKIN_PG_group(bpy.types.PropertyGroup):
    group_name: StringProperty()
    material: PointerProperty(type=bpy.types.Material)
    expanded: BoolProperty(default=True)


class PROCEEDURALSKIN_OT_create_group(bpy.types.Operator):
    bl_idname = 'proceedural_skin.create_group'
    bl_label = 'Create new skin group'
    bl_description = 'Copy main skin settings into a new material and empty vertex group (maximum 10)'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (PROCEEDURALSKIN_OT_apply.poll(context)
                and obj.proceedural_skin_main is not None
                and len(obj.proceedural_skin_groups) < 10)

    def execute(self, context):
        obj = context.active_object
        number = next((i for i in range(1, 11)
                       if obj.vertex_groups.get(f'Skin_group {i}') is None
                       and all(g.group_name != f'Skin_group {i}' for g in obj.proceedural_skin_groups)), None)
        if number is None:
            self.report({'WARNING'}, 'All ten skin group names are already in use')
            return {'CANCELLED'}
        main = obj.proceedural_skin_main
        if not main.use_nodes or not main.node_tree:
            self.report({'ERROR'}, 'Main skin material has no shader nodes')
            return {'CANCELLED'}
        try:
            add_pore_nodes(main)
        except ValueError as error:
            self.report({'ERROR'}, str(error))
            return {'CANCELLED'}
        # Material.copy duplicates the node tree, keeping every group independent.
        shader_group(main)
        material = main.copy()
        material.node_tree.nodes['Skin shader'].node_tree = skin_tree(main).copy()
        material.name = f'Skin_group {number}'
        if obj.data.users > 1:
            obj.data = obj.data.copy()
        group = obj.vertex_groups.new(name=f'Skin_group {number}')
        obj.data.materials.append(material)
        entry = obj.proceedural_skin_groups.add()
        entry.group_name = group.name
        entry.material = material
        obj.vertex_groups.active_index = group.index
        rebuild_blending(obj)
        self.report({'INFO'}, f'Created {group.name}; vertices are unassigned')
        return {'FINISHED'}


def draw_material_controls(layout, material):
    if (material is None or material.get('proceedural_skin_version') not in (1, 2, 3, 4, 5, 6)
            or not material.use_nodes or skin_tree(material) is None):
        layout.label(text='Apply skin_Main to show skin controls.')
        return
    controls = layout.column(align=True)
    controls.enabled = material.is_editable and skin_tree(material).is_editable
    for label, node_name in FACTOR_CONTROLS:
        node = skin_tree(material).nodes.get(node_name)
        if node is None or node.bl_idname != 'ShaderNodeMix' or node.data_type != ('FLOAT' if node_name == 'Pores strength' else 'RGBA'):
            controls.label(text=f'Missing Mix node: {node_name}', icon='ERROR')
            continue
        row = controls.row()
        row.enabled = not node.inputs[0].is_linked
        row.prop(node.inputs[0], 'default_value', text=label, slider=True)
    noise = skin_tree(material).nodes.get('Pores noise')
    if noise is not None and noise.bl_idname == 'ShaderNodeTexNoise':
        row = controls.row()
        row.enabled = not noise.inputs['Scale'].is_linked
        row.prop(material, 'proceedural_skin_pores_size', text='Pores size', slider=True)
    else:
        controls.label(text='Missing Pores noise node', icon='ERROR')


def draw_section(layout, owner, property_name, title, material):
    box = layout.box()
    expanded = getattr(owner, property_name)
    box.prop(owner, property_name, text=title,
             icon='TRIA_DOWN' if expanded else 'TRIA_RIGHT', emboss=False)
    if expanded:
        draw_material_controls(box, material)


class PROCEEDURALSKIN_PT_panel(bpy.types.Panel):
    bl_label = 'Proceedural skin'
    bl_idname = 'PROCEEDURALSKIN_PT_panel'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Proceedural skin'

    def draw(self, context):
        layout = self.layout
        layout.label(text='Select a mesh in Object Mode.')
        layout.operator('proceedural_skin.apply', icon='MATERIAL')
        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            return
        material = obj.proceedural_skin_main or obj.active_material
        draw_section(layout, obj, 'proceedural_skin_main_expanded', 'Skin_main', material)
        row = layout.row()
        row.operator('proceedural_skin.create_group', icon='ADD')
        layout.label(text=f'{len(obj.proceedural_skin_groups)} / 10 skin groups')
        for entry in obj.proceedural_skin_groups:
            draw_section(layout, entry, 'expanded', entry.group_name, entry.material)



classes = (PROCEEDURALSKIN_PG_group, PROCEEDURALSKIN_OT_apply,
           PROCEEDURALSKIN_OT_create_group, PROCEEDURALSKIN_PT_panel)


def register():
    bpy.types.Material.proceedural_skin_pores_size = FloatProperty(
        name='Pores size', description='Larger pores: 0 = scale 10000, 10 = scale 1000',
        min=0.0, max=10.0, step=50, precision=1,
        get=pore_size_get, set=pore_size_set,
    )
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Object.proceedural_skin_blend = PointerProperty(type=bpy.types.Material)
    bpy.types.Object.proceedural_skin_main = PointerProperty(type=bpy.types.Material)
    bpy.types.Object.proceedural_skin_main_expanded = BoolProperty(default=True)
    bpy.types.Object.proceedural_skin_groups = CollectionProperty(type=PROCEEDURALSKIN_PG_group)


def unregister():
    del bpy.types.Object.proceedural_skin_blend
    del bpy.types.Object.proceedural_skin_groups
    del bpy.types.Object.proceedural_skin_main_expanded
    del bpy.types.Object.proceedural_skin_main
    del bpy.types.Material.proceedural_skin_pores_size
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
