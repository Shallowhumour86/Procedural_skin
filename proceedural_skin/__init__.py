bl_info = {
    "name": "Proceedural skin",
    "author": "Proceedural skin contributors",
    "version": (0, 2, 0),
    "blender": (4, 4, 1),
    "location": "View3D > Sidebar > Proceedural skin",
    "description": "Create and apply the initial procedural skin material",
    "category": "Material",
}

import bpy


FACTOR_CONTROLS = (
    ("Intensity", "Final blend"),
    ("Tone", "melanin"),
    ("Flush", "Base skin"),
    ("Blush", "Blood"),
)


def hex_color(value):
    """Convert the requested display (sRGB) hex color into scene linear RGBA."""
    channels = [int(value[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
                 for c in channels) + (1.0,)


def create_skin_material():
    # Reuse only our own material; never erase a user's same-named material.
    material = bpy.data.materials.get("skin_Main")
    if material is not None and material.get("proceedural_skin_version") == 1:
        return material
    material = bpy.data.materials.new("skin_Main")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
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
        material = create_skin_material()
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
        self.report({'INFO'}, f"Applied {material.name} to {obj.name}")
        return {'FINISHED'}


class PROCEEDURALSKIN_PT_panel(bpy.types.Panel):
    bl_label = "Proceedural skin"
    bl_idname = "PROCEEDURALSKIN_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Proceedural skin"

    def draw(self, context):
        layout = self.layout
        layout.label(text="Select a mesh in Object Mode.")
        layout.operator("proceedural_skin.apply", icon='MATERIAL')
        layout.label(text="Applies to all faces of the active mesh.")
        layout.label(text="View in Material Preview or Rendered mode.")
        obj = context.active_object
        material = obj.active_material if obj and obj.type == 'MESH' else None
        if (material is None or material.get("proceedural_skin_version") != 1
                or not material.use_nodes or material.node_tree is None):
            layout.label(text="Apply skin_Main to show skin controls.")
            return
        controls = layout.column(align=True)
        controls.enabled = material.is_editable and material.node_tree.is_editable
        for label, node_name in FACTOR_CONTROLS:
            node = material.node_tree.nodes.get(node_name)
            if node is None or node.bl_idname != 'ShaderNodeMix' or node.data_type != 'RGBA':
                controls.label(text=f"Missing color Mix node: {node_name}", icon='ERROR')
                continue
            row = controls.row()
            row.enabled = not node.inputs[0].is_linked
            row.prop(node.inputs[0], "default_value", text=label, slider=True)


classes = (PROCEEDURALSKIN_OT_apply, PROCEEDURALSKIN_PT_panel)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
