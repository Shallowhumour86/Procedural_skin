# Proceedural skin — 0.1.0

A Blender 4.4.1 add-on for the first material-building iteration.

## Install and use

1. In Blender, open **Edit → Preferences → Add-ons**, open the dropdown menu at the top right, and choose **Install from Disk…**.
2. Select `proceedural_skin-0.1.0.zip` and enable **Proceedural skin** if necessary.
3. Select a mesh in **Object Mode**. In the 3D Viewport press **N** and open the **Proceedural skin** tab.
4. Click **Apply skin_Main**. Switch to **Material Preview** or **Rendered** shading.
5. Open the Shader Editor to inspect or adjust the four color Mix nodes.

The material uses Random Walk (Skin) subsurface scattering with weight 1. The supplied hex colors are converted from sRGB into Blender's linear color values. It applies to all faces of the active mesh and supports Undo. Other material slots are retained. Reapplying reuses the add-on's material and preserves subsequent shader edits. Objects sharing geometry are isolated before assigning skin.

If an unrelated `skin_Main` already exists, Blender gives the new material a suffix (such as `.001`) to preserve your material. Rename the unrelated material first if the exact name is required.

Weight paints, skin regions, dedicated sliders, vessels, pores, transition controls, and baking are future iterations.

## Validation

Run `blender --background --factory-startup --python-exit-code 1 --python tests/smoke.py` from this repository. This validates registration, exact node settings and connections, assignment, repeated application, shared mesh isolation, and existing material preservation.
