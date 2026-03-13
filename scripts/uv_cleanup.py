"""
Blender UV cleanup script for Safeguard pump bottle.

Run headless:
    blender --background --python scripts/uv_cleanup.py -- /path/to/mesh.obj /path/to/output.obj

Operations:
    1. Import OBJ
    2. Clean geometry (merge by distance, remove doubles)
    3. Smart UV Project with good island margins
    4. Pack UV islands
    5. Export cleaned OBJ
"""

import bpy
import bmesh
import math
import sys
from pathlib import Path


def get_args():
    """Get arguments after the -- separator."""
    argv = sys.argv
    if "--" in argv:
        args = argv[argv.index("--") + 1:]
    else:
        args = []
    if len(args) < 2:
        print("Usage: blender --background --python uv_cleanup.py -- input.obj output.obj")
        sys.exit(1)
    return args[0], args[1]


def clean_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_obj(filepath):
    bpy.ops.wm.obj_import(filepath=filepath)
    obj = [o for o in bpy.data.objects if o.type == 'MESH'][0]
    print(f"Imported: {obj.name}")
    print(f"  Vertices: {len(obj.data.vertices)}")
    print(f"  Faces: {len(obj.data.polygons)}")
    return obj


def clean_geometry(obj):
    """Merge close vertices and clean up mesh."""
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')

    # Merge by distance — clean up near-duplicate verts
    bpy.ops.mesh.remove_doubles(threshold=0.0001)

    # Recalculate normals
    bpy.ops.mesh.normals_make_consistent(inside=False)

    bpy.ops.object.mode_set(mode='OBJECT')

    print(f"After cleanup:")
    print(f"  Vertices: {len(obj.data.vertices)}")
    print(f"  Faces: {len(obj.data.polygons)}")


def decimate_mesh(obj, target_faces=50000):
    """Decimate to a reasonable poly count if needed."""
    current_faces = len(obj.data.polygons)
    if current_faces <= target_faces:
        print(f"  Faces ({current_faces}) already under target ({target_faces}), skipping decimate")
        return

    ratio = target_faces / current_faces
    mod = obj.modifiers.new(name="Decimate", type='DECIMATE')
    mod.ratio = ratio
    mod.use_collapse_triangulate = False

    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier="Decimate")

    print(f"Decimated: {current_faces} -> {len(obj.data.polygons)} faces (ratio: {ratio:.3f})")


def create_uv_layout(obj):
    """Create proper UV layout using Smart UV Project.

    For a pump bottle, Smart UV Project with a reasonable angle limit
    gives us good island separation between the body cylinder, cap, and pump.
    """
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')

    # Remove existing UV layers and create fresh
    mesh = obj.data
    while mesh.uv_layers:
        mesh.uv_layers.remove(mesh.uv_layers[0])
    mesh.uv_layers.new(name="UVMap")

    # Mark seams by angle — edges with a sharp angle between faces
    # become natural seam lines (good for cylindrical objects)
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.mesh.edges_select_sharp(sharpness=math.radians(40))
    bpy.ops.mesh.mark_seam(clear=False)

    # Now unwrap using the seams
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.unwrap(method='ANGLE_BASED', margin=0.005)

    # Pack islands with margin for clean texture baking
    bpy.ops.uv.pack_islands(margin=0.01)

    bpy.ops.object.mode_set(mode='OBJECT')
    print("UV layout created:")
    print("  Method: Angle-based unwrap with sharp-edge seams")
    print("  Island margin: 0.01")


def create_material_zones(obj):
    """Assign basic material slots for the pump bottle zones.

    Uses face normals and position to roughly separate:
    - body (main cylinder)
    - cap/pump (top section)
    - bottom
    """
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.faces.ensure_lookup_table()

    # Get bounding box
    min_z = min(v.co.z for v in bm.verts)
    max_z = max(v.co.z for v in bm.verts)
    height = max_z - min_z

    # Create materials
    mat_body = bpy.data.materials.new(name="body_plastic")
    mat_cap = bpy.data.materials.new(name="cap_pump")
    mat_bottom = bpy.data.materials.new(name="bottom")

    obj.data.materials.clear()
    obj.data.materials.append(mat_body)
    obj.data.materials.append(mat_cap)
    obj.data.materials.append(mat_bottom)

    # Assign faces by Z position
    cap_threshold = min_z + height * 0.75  # top 25% = cap/pump area
    bottom_threshold = min_z + height * 0.03  # bottom 3%

    for face in bm.faces:
        center_z = face.calc_center_median().z
        if center_z > cap_threshold:
            face.material_index = 1  # cap
        elif center_z < bottom_threshold:
            face.material_index = 2  # bottom
        else:
            face.material_index = 0  # body

    bm.to_mesh(mesh)
    bm.free()

    # Count per zone
    zone_counts = [0, 0, 0]
    for poly in mesh.polygons:
        zone_counts[poly.material_index] += 1
    print(f"Material zones assigned:")
    print(f"  body_plastic: {zone_counts[0]} faces")
    print(f"  cap_pump: {zone_counts[1]} faces")
    print(f"  bottom: {zone_counts[2]} faces")


def report_uv_stats(obj):
    """Print UV statistics."""
    mesh = obj.data
    if not mesh.uv_layers:
        print("No UV layers!")
        return

    uv_layer = mesh.uv_layers[0]
    min_u = min_v = float('inf')
    max_u = max_v = float('-inf')
    for loop in mesh.loops:
        uv = uv_layer.data[loop.index].uv
        min_u = min(min_u, uv[0])
        max_u = max(max_u, uv[0])
        min_v = min(min_v, uv[1])
        max_v = max(max_v, uv[1])

    print(f"Final UV stats:")
    print(f"  UV bounds: U[{min_u:.3f}, {max_u:.3f}] V[{min_v:.3f}, {max_v:.3f}]")
    print(f"  UV coverage: {(max_u - min_u) * (max_v - min_v):.1%}")


def export_obj(obj, filepath):
    """Export as OBJ with UVs and materials."""
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    bpy.ops.wm.obj_export(
        filepath=filepath,
        export_selected_objects=True,
        export_uv=True,
        export_normals=True,
        export_materials=True,
        apply_modifiers=True,
    )
    print(f"Exported: {filepath}")


def export_glb(obj, filepath):
    """Export as GLB for web preview."""
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    bpy.ops.export_scene.gltf(
        filepath=filepath,
        use_selection=True,
        export_format='GLB',
        export_apply=True,
    )
    print(f"Exported: {filepath}")


def main():
    input_path, output_path = get_args()
    output_path = str(Path(output_path).resolve())
    output_glb = str(Path(output_path).with_suffix('.glb'))

    print("=" * 60)
    print("UV Cleanup: Safeguard Pump Bottle")
    print("=" * 60)

    clean_scene()
    obj = import_obj(input_path)
    clean_geometry(obj)
    decimate_mesh(obj, target_faces=50000)
    create_material_zones(obj)
    create_uv_layout(obj)
    report_uv_stats(obj)
    export_obj(obj, output_path)
    export_glb(obj, output_glb)

    print("=" * 60)
    print("Done!")
    print("=" * 60)


if __name__ == "__main__":
    main()
