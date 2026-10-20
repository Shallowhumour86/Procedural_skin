# Proceedural skin — 0.2.0

A Blender 4.4.1 add-on with material creation and live skin factor controls.

## Install and use

1. In Blender, open **Edit → Preferences → Add-ons**, open the dropdown menu at the top right, and choose **Install from Disk…**.
2. Select `proceedural_skin-0.2.0.zip` and enable **Proceedural skin** if necessary.
3. Select a mesh in **Object Mode**. In the 3D Viewport press **N** and open the **Proceedural skin** tab.
4. Click **Apply skin_Main**. Switch to **Material Preview** or **Rendered** shading.
5. Adjust **Intensity**, **Tone**, **Flush**, and **Blush** in the same sidebar. Each slider runs from 0 to 1 and edits its Mix node factor directly.

| Slider | Node factor | Initial value |
| --- | --- | --- |
| Intensity | Final blend | 0.5 |
| Tone | melanin | 0.4 |
| Flush | Base skin | 0.2 |
| Blush | Blood | 0.5 |

Controls follow the active material and also work with skin materials saved by v0.1.0. Changes in the Shader Editor appear in the sliders automatically. Objects using the same skin material share these adjustments. A factor driven by a node link is disabled in the panel.

To upgrade, install the new ZIP and restart Blender if the previous version remains loaded. Existing material values are preserved.

The material uses Random Walk (Skin) subsurface scattering with weight 1. The supplied hex colors are converted from sRGB into Blender's linear color values. It applies to all faces of the active mesh and supports Undo. Other material slots are retained. Reapplying reuses the add-on's material and preserves subsequent shader edits. Objects sharing geometry are isolated before assigning skin.

If an unrelated `skin_Main` already exists, Blender gives the new material a suffix (such as `.001`) to preserve your material. Rename the unrelated material first if the exact name is required.

Weight paints, skin regions, vessels, pores, transition controls, and baking are future iterations.

## Validation

Run `blender --background --factory-startup --python-exit-code 1 --python tests/smoke.py` from this repository. This validates registration, exact node settings and connections, assignment, repeated application, shared mesh isolation, existing material preservation, all four slider bindings and value changes, and missing-node handling. Checks have passed in Blender 4.3.2; exact Blender 4.4.1 validation is left for manual testing.
