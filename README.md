# Proceedural skin — 0.7.0

A Blender 4.4.1 add-on for procedural skin with independently adjustable, weight-painted skin regions.

## Install and upgrade

Install `dist/proceedural_skin-0.7.0.zip` through **Edit → Preferences → Add-ons → Install from Disk…**, enable **Proceedural skin**, then restart Blender after upgrading an older version.

Select your mesh in Object Mode, press **N**, open **Proceedural skin**, and click **Apply skin_Main**. This upgrades the main material and every registered skin-group material, adds the weight Geometry Nodes modifier, and installs a combined display material. Existing skin settings and additional vertex-group weights are preserved. The main `skin_main` group is filled with weight 1 only on initial setup; subsequent Apply operations preserve painted main weights too.

## Paint different skin types

1. Click **Create new skin group**. Up to ten empty groups, `Skin_group 1` through `Skin_group 10`, are supported per object.
2. Open its collapsible settings section and change Tone, Intensity or another setting enough to distinguish it from the main skin. New groups initially copy the main settings, so they look identical until adjusted.
3. In **Object Data Properties → Vertex Groups**, select that group.
4. Either select vertices in Edit Mode and click **Assign** with weight 1, or enter Weight Paint mode and paint the group.
5. View the result in **Material Preview** or **Rendered** shading. Weight changes update live; no manual material assignment or Apply operation is needed after painting.

Weight 0 reveals the underlying skin; weight 1 uses the group skin; fractional weights create smooth transitions. Transition detail depends on mesh density and weight interpolation. The main skin is the fallback everywhere additional groups have zero weight, even if `skin_main` is reduced to zero. Additional groups layer in creation order: later groups take precedence in overlapping areas. For two group weights `w1` and `w2`, the contributions are main `(1-w1)(1-w2)`, group 1 `w1(1-w2)`, and group 2 `w2`. This is layered blending, without weight normalization.

## Controls and pores

| Control | Node factor | Initial value |
| --- | --- | --- |
| Intensity | Final blend | 0.5 |
| Tone | melanin | 0.4 |
| Flush | Base skin | 0.2 |
| Perfusion | Blood | 0.5 |
| pores colour | pores colour | 1.0 |

The new Color/Mix node **pores colour** receives **Final blend → A** and **Pores → B**, then feeds Principled Base Color. Its factor is controlled by **pores colour** in each settings section: 0 removes pore color variation, and 1 preserves the previous appearance. This does not change pore bump strength.

The earlier **Pores** Mix still receives **melanin → A** and **Final blend → B**. Noise → Pores range drives both Factor and B of the Float Mix **Pores strength**. That output drives Pores Factor and bump Strength; Pores range also drives bump Height. Bump Normal feeds Principled Normal.

Noise defaults: Scale 10,000, Detail 1, Roughness 1, Lacunarity 2, Distortion 0. Map Range is inverted: From Min 0.5, From Max 0.8, To Min 1, To Max 0. **Pores size** ranges from 0 to 10 in half steps, mapping to Scale `10000 - 900 × size`. Existing scale values are preserved.

## How the weight system works

Each object gets a **Proceedural skin weights** Geometry Nodes modifier. Its graph reads `skin_main` and each `Skin_group #` with a **Named Attribute** node set to Float. Blender exposes vertex-group weights to this field reader. Each reader feeds a **Store Named Attribute** node set to Float / Point domain, writing `ps_weight_0`, `ps_weight_1`, and so on onto the evaluated mesh. The original mesh weights remain editable; the modifier does not apply or bake them.

A final **Set Material** node assigns the object's combined `… skin blend` material to the evaluated geometry. The shader reads each stored weight using an **Attribute** node's Fac output and drives a **Mix Shader** between the preceding layers and the corresponding skin shader. It mixes complete shaders, so both pore color and bump follow the painted regions. Empty or missing groups supply zero influence. No vertex or face material assignment is needed for these layers.

Blender materials cannot directly reference other materials as shader inputs. Therefore each source material's generated graph is placed inside a reusable **Skin shader** node group. Its source material and the combined material reference the same shader group, so sidebar edits update the displayed skin immediately. Each additional skin group's shader node tree is copied independently at creation. To inspect the original nodes in the Shader Editor, open a source material and enter its **Skin shader** group with Tab.

Only Apply and Create new skin group rebuild the generated Geometry Nodes and combined-material graphs. Painting is evaluated directly by Blender: no timer, update handler, baking, or dependency on a Python callback is needed for rendering. Existing source material slots are retained, but the modifier controls the displayed material. Disabling the modifier shows the underlying face assignments.

The modifier is added at the end of the current stack. Later modifiers must preserve the named attributes; topology-changing modifiers may change weight interpolation. Keep vertex-group names unchanged after setup. If you alter group structure, return to Object Mode and click Apply to rebuild. The generated modifier and combined material are managed by the add-on and rebuilt on Apply, so edit the source Skin shader groups rather than those generated graphs.

## Research references

Implementation was checked against Blender's official **v4.4.1** source (the online manual was blocked in the setup environment):

- [Named Attribute geometry node](https://github.com/blender/blender/blob/v4.4.1/source/blender/nodes/geometry/nodes/node_geo_input_named_attribute.cc): reads named float fields.
- [Store Named Attribute geometry node](https://github.com/blender/blender/blob/v4.4.1/source/blender/nodes/geometry/nodes/node_geo_store_named_attribute.cc): stores fields on a selected geometry domain.
- [Attribute shader node](https://github.com/blender/blender/blob/v4.4.1/source/blender/nodes/shader/nodes/node_shader_attribute.cc): retrieves geometry attributes in shading.

## Validation

Run from the repository root:

```sh
blender --background --factory-startup --python-exit-code 1 --python tests/smoke.py
blender --background --factory-startup --python-exit-code 1 --python tests/groups.py
blender --background --factory-startup --python-exit-code 1 --python tests/weights.py
```

Checks cover shader defaults and connections, pores colour, half-step size mapping, migration, repeatability, all ten independent groups, collapsible controls, and save/reopen persistence. Weight checks inspect actual evaluated Point/Float attributes and exercise Edit Mode vertex assignment and CPU-render distinct test shaders at weights 0, 0.5 and 1, plus overlapping groups. Tests run on the available Blender 4.3.2; exact 4.4.1 validation remains for manual testing.

Vessels, additional skin controls, and texture baking remain future iterations.
