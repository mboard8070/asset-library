"""
Assign material zones and UV-project label textures for Safeguard pump bottle.

Material zones based on geometry analysis:
  - body_plastic: main cylinder (Y 5%-75%), translucent purple
  - label_front: front-facing body faces (-Z normal), gets front photo
  - label_back: back-facing body faces (+Z normal), gets back photo
  - cap_plastic: neck/pump area (Y 80%+), white plastic
  - bottom: base disc (Y 0-5%), not visible

Label UVs are cylindrical projections that map directly to the reference photos.

Run:
    blender --background --python scripts/bottle_materials.py -- \
        input.obj front.jpg back.jpg output_dir
"""

import bpy
import bmesh
import math
import sys
import os
from pathlib import Path
from mathutils import Vector


def get_args():
    argv = sys.argv
    if "--" in argv:
        args = argv[argv.index("--") + 1:]
    else:
        args = []
    if len(args) < 4:
        print("Usage: blender --background --python bottle_materials.py -- "
              "input.obj front.jpg back.jpg output_dir")
        sys.exit(1)
    return args[0], args[1], args[2], args[3]


def main():
    obj_path, front_path, back_path, output_dir = get_args()
    front_path = str(Path(front_path).resolve())
    back_path = str(Path(back_path).resolve())
    output_dir = str(Path(output_dir).resolve())

    print("=" * 60)
    print("Bottle Material Zone Assignment")
    print("=" * 60)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.obj_import(filepath=obj_path)
    obj = [o for o in bpy.data.objects if o.type == 'MESH'][0]
    mesh = obj.data

    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()

    # Get bounds — Y is height
    min_y = min(v.co.y for v in bm.verts)
    max_y = max(v.co.y for v in bm.verts)
    height = max_y - min_y

    # Zone thresholds (fraction of height)
    BODY_BOTTOM = 0.05   # below this = bottom disc
    BODY_TOP = 0.75      # above this = shoulder/neck
    CAP_START = 0.78     # above this = cap/pump
    # Between BODY_TOP and CAP_START = shoulder transition

    # Label is on the body, front-facing (-Z) or back-facing (+Z)
    # Side faces (X-dominant normal) get body_plastic
    LABEL_NORMAL_THRESHOLD = 0.3  # |normal.z| > this = label zone

    # --- Create materials ---
    materials = {}

    # Body plastic — translucent purple
    mat_body = bpy.data.materials.new("body_plastic")
    mat_body.use_nodes = True
    nodes = mat_body.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (0.58, 0.40, 0.70, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.15
    bsdf.inputs["Alpha"].default_value = 0.7
    mat_body.blend_method = 'BLEND'
    materials["body_plastic"] = 0

    # Label front — textured from front photo
    mat_label_front = bpy.data.materials.new("label_front")
    mat_label_front.use_nodes = True
    nodes = mat_label_front.node_tree.nodes
    links = mat_label_front.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    bsdf.inputs["Roughness"].default_value = 0.35
    tex = nodes.new("ShaderNodeTexImage")
    tex.location = (-400, 300)
    tex.image = bpy.data.images.load(front_path)
    links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    materials["label_front"] = 1

    # Label back — textured from back photo
    mat_label_back = bpy.data.materials.new("label_back")
    mat_label_back.use_nodes = True
    nodes = mat_label_back.node_tree.nodes
    links = mat_label_back.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    bsdf.inputs["Roughness"].default_value = 0.35
    tex = nodes.new("ShaderNodeTexImage")
    tex.location = (-400, 300)
    tex.image = bpy.data.images.load(back_path)
    links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    materials["label_back"] = 2

    # Cap/pump — white plastic
    mat_cap = bpy.data.materials.new("cap_plastic")
    mat_cap.use_nodes = True
    nodes = mat_cap.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (0.95, 0.95, 0.95, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.08
    materials["cap_plastic"] = 3

    # Bottom — dark plastic (not visible)
    mat_bottom = bpy.data.materials.new("bottom")
    mat_bottom.use_nodes = True
    nodes = mat_bottom.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (0.4, 0.3, 0.45, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.5
    materials["bottom"] = 4

    # Assign materials to mesh
    mesh.materials.clear()
    mesh.materials.append(mat_body)
    mesh.materials.append(mat_label_front)
    mesh.materials.append(mat_label_back)
    mesh.materials.append(mat_cap)
    mesh.materials.append(mat_bottom)

    # --- Assign faces to zones ---
    zone_counts = {name: 0 for name in materials}

    for face in bm.faces:
        center_y = face.calc_center_median().y
        y_frac = (center_y - min_y) / height

        if y_frac < BODY_BOTTOM:
            face.material_index = materials["bottom"]
            zone_counts["bottom"] += 1
        elif y_frac > CAP_START:
            face.material_index = materials["cap_plastic"]
            zone_counts["cap_plastic"] += 1
        elif y_frac > BODY_TOP:
            # Shoulder transition — treat as body
            face.material_index = materials["body_plastic"]
            zone_counts["body_plastic"] += 1
        else:
            # Body zone — check if it's a label face
            nz = face.normal.z
            if nz < -LABEL_NORMAL_THRESHOLD:
                face.material_index = materials["label_front"]
                zone_counts["label_front"] += 1
            elif nz > LABEL_NORMAL_THRESHOLD:
                face.material_index = materials["label_back"]
                zone_counts["label_back"] += 1
            else:
                face.material_index = materials["body_plastic"]
                zone_counts["body_plastic"] += 1

    print("Material zones assigned:")
    for name, count in zone_counts.items():
        print(f"  {name}: {count} faces")

    # --- UV project label faces ---
    # Create a UV layer for label projection
    uv_layer = bm.loops.layers.uv.verify()

    # Photo framing — where the bottle sits in the reference image
    # Front photo: bottle body occupies roughly center 52% width, 70% height
    PHOTO_U_MIN = 0.24
    PHOTO_U_MAX = 0.76
    PHOTO_V_MIN = 0.05
    PHOTO_V_MAX = 0.88

    # Get body bounds for normalization
    body_min_x = min(v.co.x for v in bm.verts)
    body_max_x = max(v.co.x for v in bm.verts)
    body_width = body_max_x - body_min_x

    body_min_y_abs = min_y + BODY_BOTTOM * height
    body_max_y_abs = min_y + BODY_TOP * height
    body_height = body_max_y_abs - body_min_y_abs

    for face in bm.faces:
        mat_idx = face.material_index

        if mat_idx == materials["label_front"]:
            # Project from -Z: X → U, Y → V
            for loop in face.loops:
                co = loop.vert.co
                nx = (co.x - body_min_x) / body_width  # 0-1 across width
                ny = (co.y - body_min_y_abs) / body_height  # 0-1 up body

                u = PHOTO_U_MIN + nx * (PHOTO_U_MAX - PHOTO_U_MIN)
                v = PHOTO_V_MIN + ny * (PHOTO_V_MAX - PHOTO_V_MIN)
                loop[uv_layer].uv = (u, v)

        elif mat_idx == materials["label_back"]:
            # Project from +Z: X flipped → U, Y → V
            for loop in face.loops:
                co = loop.vert.co
                nx = (co.x - body_min_x) / body_width
                ny = (co.y - body_min_y_abs) / body_height

                u = PHOTO_U_MAX - nx * (PHOTO_U_MAX - PHOTO_U_MIN)  # Flip X
                v = PHOTO_V_MIN + ny * (PHOTO_V_MAX - PHOTO_V_MIN)
                loop[uv_layer].uv = (u, v)

        else:
            # Non-label faces: simple planar UV (won't be textured anyway)
            for loop in face.loops:
                co = loop.vert.co
                angle = math.atan2(co.z, co.x)
                ny = (co.y - min_y) / height
                u = (angle / (2 * math.pi)) + 0.5
                v = ny
                loop[uv_layer].uv = (u, v)

    bm.to_mesh(mesh)
    bm.free()

    # --- Export ---
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    os.makedirs(output_dir, exist_ok=True)

    # OBJ
    obj_out = os.path.join(output_dir, "base_final.obj")
    bpy.ops.wm.obj_export(
        filepath=obj_out,
        export_selected_objects=True,
        export_uv=True,
        export_normals=True,
        export_materials=True,
    )
    print(f"Exported OBJ: {obj_out}")

    # GLB with textures embedded
    glb_out = os.path.join(output_dir, "base_final.glb")
    bpy.ops.export_scene.gltf(
        filepath=glb_out,
        use_selection=True,
        export_format='GLB',
        export_apply=True,
        export_image_format='AUTO',
    )
    print(f"Exported GLB: {glb_out}")
    print(f"  Size: {os.path.getsize(glb_out)/1024:.0f} KB")

    print("=" * 60)
    print("Done!")
    print("=" * 60)


if __name__ == "__main__":
    main()
