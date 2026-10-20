"""Live vertex-weight attributes and reusable shader layers."""
import bpy


def skin_tree(material):
    tree = material.node_tree
    node = tree.nodes.get('Skin shader') if tree else None
    return node.node_tree if node and node.bl_idname == 'ShaderNodeGroup' else tree


def shader_group(material):
    """Move the generated shader into a reusable group once, without handlers."""
    tree = material.node_tree
    existing = tree.nodes.get('Skin shader')
    if existing and existing.bl_idname == 'ShaderNodeGroup':
        return existing.node_tree
    group = bpy.data.node_groups.new(material.name + ' shader', 'ShaderNodeTree')
    group.interface.new_socket(name='Shader', in_out='OUTPUT', socket_type='NodeSocketShader')
    copies = {}
    for old in tree.nodes:
        if old.type == 'OUTPUT_MATERIAL':
            continue
        new = group.nodes.new(old.bl_idname)
        # Set dynamic socket modes before copying socket defaults and links.
        for attr in ('data_type', 'blend_type', 'noise_dimensions', 'noise_type',
                     'normalize', 'interpolation_type', 'clamp', 'clamp_factor',
                     'clamp_result', 'subsurface_method', 'distribution', 'invert'):
            if hasattr(old, attr) and hasattr(new, attr):
                setattr(new, attr, getattr(old, attr))
        new.name, new.label = old.name, old.label
        new.location, new.width = old.location, old.width
        new.mute, new.hide = old.mute, old.hide
        for a, b in zip(old.inputs, new.inputs):
            if hasattr(a, 'default_value') and hasattr(b, 'default_value'):
                b.default_value = a.default_value
        copies[old] = new
    output = group.nodes.new('NodeGroupOutput')
    output.location = (700, 260)
    for link in tree.links:
        if link.from_node not in copies:
            continue
        source = copies[link.from_node].outputs[list(link.from_node.outputs).index(link.from_socket)]
        if link.to_node.type == 'OUTPUT_MATERIAL':
            if link.to_socket.name == 'Surface' and link.to_node.is_active_output:
                group.links.new(source, output.inputs['Shader'])
        elif link.to_node in copies:
            target = copies[link.to_node].inputs[list(link.to_node.inputs).index(link.to_socket)]
            group.links.new(source, target)
    tree.nodes.clear()
    node = tree.nodes.new('ShaderNodeGroup')
    node.name = node.label = 'Skin shader'
    node.node_tree = group
    output = tree.nodes.new('ShaderNodeOutputMaterial')
    output.location = (300, 0)
    tree.links.new(node.outputs['Shader'], output.inputs['Surface'])
    return group


def rebuild_blending(obj):
    """Only rebuild on structural changes; painted weights evaluate live."""
    layers = [('skin_main', obj.proceedural_skin_main)]
    layers += [(entry.group_name, entry.material) for entry in obj.proceedural_skin_groups
               if entry.material is not None]
    material = obj.proceedural_skin_blend
    if material and any(other != obj and other.proceedural_skin_blend == material
                        for other in bpy.data.objects):
        material = None
    if material is None:
        material = bpy.data.materials.new(obj.name + ' skin blend')
        material.use_nodes = True
        obj.proceedural_skin_blend = material
    tree = material.node_tree
    tree.nodes.clear()
    base = tree.nodes.new('ShaderNodeGroup')
    base.name = base.label = 'Skin_main'
    base.node_tree = shader_group(layers[0][1])
    shader = base.outputs['Shader']
    for index, (name, source) in enumerate(layers[1:], 1):
        node = tree.nodes.new('ShaderNodeGroup')
        node.name = node.label = name
        node.node_tree = shader_group(source)
        node.location = (index * 260, -200)
        attribute = tree.nodes.new('ShaderNodeAttribute')
        attribute.attribute_name = f'ps_weight_{index}'
        attribute.location = (index * 260, 200)
        mix = tree.nodes.new('ShaderNodeMixShader')
        mix.label = name + ' weight'
        mix.location = (index * 260 + 200, 0)
        tree.links.new(attribute.outputs['Fac'], mix.inputs[0])
        tree.links.new(shader, mix.inputs[1])
        tree.links.new(node.outputs['Shader'], mix.inputs[2])
        shader = mix.outputs[0]
    output = tree.nodes.new('ShaderNodeOutputMaterial')
    output.location = (len(layers) * 260 + 250, 0)
    tree.links.new(shader, output.inputs['Surface'])
    modifier = next((m for m in obj.modifiers if m.type == 'NODES'
                     and m.node_group and m.node_group.get('proceedural_skin_weights')), None)
    if modifier is None:
        modifier = obj.modifiers.new('Proceedural skin weights', 'NODES')
    graph = modifier.node_group
    if graph is None or graph.users > 1:
        graph = bpy.data.node_groups.new(obj.name + ' skin weights', 'GeometryNodeTree')
        graph.interface.new_socket(name='Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
        graph.interface.new_socket(name='Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
        modifier.node_group = graph
    graph['proceedural_skin_weights'] = True
    graph.nodes.clear()
    incoming = graph.nodes.new('NodeGroupInput')
    geometry = incoming.outputs['Geometry']
    for index, (name, _) in enumerate(layers):
        read = graph.nodes.new('GeometryNodeInputNamedAttribute')
        read.data_type = 'FLOAT'
        read.inputs['Name'].default_value = name
        read.label = name + ' vertex weights'
        read.location = (index * 250, -220)
        store = graph.nodes.new('GeometryNodeStoreNamedAttribute')
        store.data_type = 'FLOAT'
        store.domain = 'POINT'
        store.inputs['Name'].default_value = f'ps_weight_{index}'
        store.location = (index * 250 + 200, 100)
        graph.links.new(geometry, store.inputs['Geometry'])
        graph.links.new(read.outputs['Attribute'], store.inputs['Value'])
        geometry = store.outputs['Geometry']
    set_material = graph.nodes.new('GeometryNodeSetMaterial')
    set_material.inputs['Material'].default_value = material
    set_material.location = (len(layers) * 250 + 200, 100)
    graph.links.new(geometry, set_material.inputs['Geometry'])
    output = graph.nodes.new('NodeGroupOutput')
    output.location = (len(layers) * 250 + 450, 100)
    graph.links.new(set_material.outputs['Geometry'], output.inputs['Geometry'])
    modifier.show_in_editmode = True
    obj.update_tag()
