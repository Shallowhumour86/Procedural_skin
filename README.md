# Proceedural skin — 0.4.0

A Blender 4.4.1 add-on with material creation and live skin factor controls.

## Install and use

1. In Blender, open **Edit → Preferences → Add-ons**, open the dropdown menu at the top right, and choose **Install from Disk…**.
2. Select `proceedural_skin-0.4.0.zip` and enable **Proceedural skin** if necessary.
3. Select a mesh in **Object Mode**. In the 3D Viewport press **N** and open the **Proceedural skin** tab.
4. Click **Apply skin_Main**. Switch to **Material Preview** or **Rendered** shading.
5. Adjust **Intensity**, **Tone**, **Flush**, **Perfusion**, and **Pores** in the same sidebar. Each slider runs from 0 to 1 and edits its Mix node factor directly.

| Slider | Node factor | Initial value |
| --- | --- | --- |
| Intensity | Final blend | 0.5 |
| Tone | melanin | 0.4 |
| Flush | Base skin | 0.2 |
| Perfusion | Blood | 0.5 |
| Pores | Pores strength (Float Mix) | 0.5 |

## Pores size

**Pores size** runs from 0 to 10 in steps of 0.5 and controls the Pores noise Scale inversely. New materials start at 0 (Scale 10,000). Scale = 10,000 − 900 × size, so size 5 = Scale 5,500 and size 10 = Scale 1,000. The specified endpoints require a scale change of 900 per unit (450 per half step), rather than 1,000 per unit. Typed values snap to half steps too.

The slider reads the actual noise scale, so Shader Editor changes are reflected in the panel. Existing noise scale is preserved during upgrade. A linked Scale socket disables the slider. To upgrade an existing material, click **Apply skin_Main** once; the pore range becomes inverted without resetting color factors, pore strength or noise scale.

## Pores

The pore Noise Texture uses Scale 10,000, Detail 1, Roughness 1, Lacunarity 2 and Distortion 0. Its factor feeds a Map Range with Value 1 (overridden by the connected noise), From Min 0.5, From Max 0.8, To Min 1 and To Max 0 (inverted).

The map drives input B of the Float Mix **Pores strength**, with A = 0. The **Pores** slider controls its factor, initially 0.5. Its result drives both the factor of the **Pores** color Mix (Final blend / melanin) and bump strength. Map Range also drives bump height; bump normal feeds the Principled normal input. Other new-node settings retain Blender defaults.

After upgrading, select your existing skin object and click **Apply skin_Main** once to add the pore graph. Existing color factors are preserved. Reapplying preserves pore edits too. **Perfusion** is the renamed Blush control; it keeps the existing Blood factor.

Controls follow the active material and also work with skin materials saved by earlier versions. Changes in the Shader Editor appear in the sliders automatically. Objects using the same skin material share these adjustments. A factor driven by a node link is disabled in the panel.

To upgrade, install the new ZIP and restart Blender if the previous version remains loaded. Existing material values are preserved.

The material uses Random Walk (Skin) subsurface scattering with weight 1. The supplied hex colors are converted from sRGB into Blender's linear color values. It applies to all faces of the active mesh and supports Undo. Other material slots are retained. Reapplying reuses the add-on's material and preserves subsequent shader edits. Objects sharing geometry are isolated before assigning skin.

If an unrelated `skin_Main` already exists, Blender gives the new material a suffix (such as `.001`) to preserve your material. Rename the unrelated material first if the exact name is required.

Weight paints, skin regions, vessels, transition controls, and baking are future iterations.

## Validation

Run `blender --background --factory-startup --python-exit-code 1 --python tests/smoke.py` from this repository. This validates registration, exact node settings and connections, assignment, repeated application, shared mesh isolation, existing material preservation, all six slider bindings and value changes, inverse pore size mapping, half-step snapping, version upgrades, and missing-node handling. Checks have passed in Blender 4.3.2; exact Blender 4.4.1 validation is left for manual testing.
