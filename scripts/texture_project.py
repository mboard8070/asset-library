"""
Texture projection for Safeguard pump bottle.

Projects front and back product photos onto the 3D mesh UV layout
by rasterizing triangles in UV space and sampling the source images
via orthographic projection. No Cycles baking required.

Run:
    python3 scripts/texture_project.py \
        mesh.obj front.jpg back.jpg UVMap output.png [resolution]

Dependencies: Pillow, numpy
"""

import sys
import math
import numpy as np
from pathlib import Path
from PIL import Image


def parse_obj(filepath):
    """Parse an OBJ file, returning vertices, UVs, normals, and face data."""
    vertices = []
    uvs = []
    normals = []
    faces = []  # list of (vert_indices, uv_indices, normal_indices)

    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if line.startswith('v '):
                parts = line.split()
                vertices.append((float(parts[1]), float(parts[2]), float(parts[3])))
            elif line.startswith('vt '):
                parts = line.split()
                uvs.append((float(parts[1]), float(parts[2])))
            elif line.startswith('vn '):
                parts = line.split()
                normals.append((float(parts[1]), float(parts[2]), float(parts[3])))
            elif line.startswith('f '):
                parts = line.split()[1:]
                face_v = []
                face_vt = []
                face_vn = []
                for p in parts:
                    indices = p.split('/')
                    face_v.append(int(indices[0]) - 1)
                    if len(indices) > 1 and indices[1]:
                        face_vt.append(int(indices[1]) - 1)
                    if len(indices) > 2 and indices[2]:
                        face_vn.append(int(indices[2]) - 1)
                faces.append((face_v, face_vt, face_vn))

    return (np.array(vertices, dtype=np.float64),
            np.array(uvs, dtype=np.float64),
            np.array(normals, dtype=np.float64),
            faces)


def compute_face_normal(v0, v1, v2):
    """Compute face normal from three vertices."""
    edge1 = v1 - v0
    edge2 = v2 - v0
    normal = np.cross(edge1, edge2)
    length = np.linalg.norm(normal)
    if length > 0:
        normal /= length
    return normal


def barycentric(p, a, b, c):
    """Compute barycentric coordinates of point p in triangle abc (2D)."""
    v0 = c - a
    v1 = b - a
    v2 = p - a

    dot00 = np.dot(v0, v0)
    dot01 = np.dot(v0, v1)
    dot02 = np.dot(v0, v2)
    dot11 = np.dot(v1, v1)
    dot12 = np.dot(v1, v2)

    denom = dot00 * dot11 - dot01 * dot01
    if abs(denom) < 1e-10:
        return -1, -1, -1

    inv_denom = 1.0 / denom
    u = (dot11 * dot02 - dot01 * dot12) * inv_denom
    v = (dot00 * dot12 - dot01 * dot02) * inv_denom

    return 1 - u - v, v, u


def sample_image(img_array, u, v):
    """Sample an image at UV coordinates with bilinear interpolation."""
    h, w = img_array.shape[:2]
    x = u * (w - 1)
    y = (1.0 - v) * (h - 1)  # Flip V (image origin is top-left)

    x0 = max(0, min(int(x), w - 2))
    y0 = max(0, min(int(y), h - 2))
    x1 = x0 + 1
    y1 = y0 + 1

    fx = x - x0
    fy = y - y0

    c00 = img_array[y0, x0].astype(np.float32)
    c10 = img_array[y0, x1].astype(np.float32)
    c01 = img_array[y1, x0].astype(np.float32)
    c11 = img_array[y1, x1].astype(np.float32)

    return (c00 * (1 - fx) * (1 - fy) +
            c10 * fx * (1 - fy) +
            c01 * (1 - fx) * fy +
            c11 * fx * fy)


def rasterize_triangle(output, uv0, uv1, uv2, color_func, resolution):
    """Rasterize a triangle in UV space, calling color_func for each pixel."""
    # Convert UV to pixel coordinates
    px = np.array([uv0[0], uv1[0], uv2[0]]) * (resolution - 1)
    py = np.array([uv0[1], uv1[1], uv2[1]]) * (resolution - 1)

    # Bounding box
    min_x = max(0, int(min(px)))
    max_x = min(resolution - 1, int(max(px)) + 1)
    min_y = max(0, int(min(py)))
    max_y = min(resolution - 1, int(max(py)) + 1)

    a = np.array([px[0], py[0]])
    b = np.array([px[1], py[1]])
    c = np.array([px[2], py[2]])

    for y in range(min_y, max_y + 1):
        for x in range(min_x, max_x + 1):
            p = np.array([float(x), float(y)])
            w0, w1, w2 = barycentric(p, a, b, c)

            if w0 >= -0.001 and w1 >= -0.001 and w2 >= -0.001:
                color = color_func(w0, w1, w2)
                # UV origin is bottom-left, image origin is top-left
                img_y = resolution - 1 - y
                if 0 <= img_y < resolution:
                    output[img_y, x] = np.clip(color, 0, 255).astype(np.uint8)


def main():
    if len(sys.argv) < 5:
        print("Usage: python3 texture_project.py mesh.obj front.jpg back.jpg output.png [resolution]")
        sys.exit(1)

    mesh_path = sys.argv[1]
    front_path = sys.argv[2]
    back_path = sys.argv[3]
    output_path = sys.argv[4]
    resolution = int(sys.argv[5]) if len(sys.argv) > 5 else 2048

    print("=" * 60)
    print("Texture Projection: Safeguard Pump Bottle")
    print(f"  Resolution: {resolution}x{resolution}")
    print("=" * 60)

    # Load mesh
    print("Loading mesh...")
    vertices, uvs, normals, faces = parse_obj(mesh_path)
    print(f"  Vertices: {len(vertices)}, UVs: {len(uvs)}, Faces: {len(faces)}")

    # Load reference images
    print("Loading reference images...")
    front_img = np.array(Image.open(front_path).convert('RGB'))
    back_img = np.array(Image.open(back_path).convert('RGB'))
    print(f"  Front: {front_img.shape}, Back: {back_img.shape}")

    # Mesh bounds (X=width, Y=depth, Z=height)
    min_x, max_x = vertices[:, 0].min(), vertices[:, 0].max()
    min_z, max_z = vertices[:, 2].min(), vertices[:, 2].max()
    width = max_x - min_x
    height = max_z - min_z
    print(f"  Mesh width (X): {width:.4f}, height (Z): {height:.4f}")

    # Photo framing parameters — how much of the photo the bottle occupies
    # These are estimated from the reference photos
    bottle_u_min = 0.24   # bottle starts at ~24% from left
    bottle_u_max = 0.76   # bottle ends at ~76% from left
    bottle_v_min = 0.02   # bottom of bottle at ~2% from bottom
    bottle_v_max = 0.98   # top of pump at ~98% from bottom

    # Create output image
    output = np.zeros((resolution, resolution, 3), dtype=np.uint8)

    # Process each face
    print("Rasterizing triangles...")
    total_faces = len(faces)

    for fi, (fv, fvt, fvn) in enumerate(faces):
        if fi % 20000 == 0:
            print(f"  {fi}/{total_faces} ({100*fi//total_faces}%)")

        if len(fv) < 3 or len(fvt) < 3:
            continue

        # Triangulate quads
        triangles = []
        for i in range(1, len(fv) - 1):
            triangles.append((0, i, i + 1))

        for i0, i1, i2 in triangles:
            vi0, vi1, vi2 = fv[i0], fv[i1], fv[i2]
            ti0, ti1, ti2 = fvt[i0], fvt[i1], fvt[i2]

            v0, v1, v2 = vertices[vi0], vertices[vi1], vertices[vi2]
            uv0, uv1, uv2 = uvs[ti0], uvs[ti1], uvs[ti2]

            # Face normal for front/back blending
            face_normal = compute_face_normal(v0, v1, v2)
            normal_y = face_normal[1]  # Y component: negative=front, positive=back

            # Blend factor: 0=front, 1=back
            blend = np.clip((normal_y + 0.2) / 0.4, 0.0, 1.0)

            def make_color_func(v0=v0, v1=v1, v2=v2, blend=blend):
                def color_func(w0, w1, w2):
                    # Interpolate 3D position
                    pos = w0 * v0 + w1 * v1 + w2 * v2

                    # Map vertex position to image UV
                    nx = (pos[0] - min_x) / width  # 0-1 across bottle width
                    nz = (pos[2] - min_z) / height  # 0-1 from bottom to top

                    # Front image UV
                    fu = bottle_u_min + nx * (bottle_u_max - bottle_u_min)
                    fv = bottle_v_min + nz * (bottle_v_max - bottle_v_min)

                    # Back image UV (X flipped)
                    bu = bottle_u_max - nx * (bottle_u_max - bottle_u_min)
                    bv = fv

                    front_color = sample_image(front_img, fu, fv)
                    back_color = sample_image(back_img, bu, bv)

                    return front_color * (1 - blend) + back_color * blend

                return color_func

            rasterize_triangle(output, uv0, uv1, uv2, make_color_func(), resolution)

    print(f"  {total_faces}/{total_faces} (100%)")

    # Save
    Image.fromarray(output).save(output_path)
    file_size = Path(output_path).stat().st_size
    print(f"Saved: {output_path} ({file_size / 1024:.0f} KB)")

    # Check how much is non-black
    non_black = np.any(output > 0, axis=2).sum()
    total = resolution * resolution
    print(f"Coverage: {non_black}/{total} pixels ({100*non_black/total:.1f}%)")

    print("=" * 60)
    print("Done!")
    print("=" * 60)


if __name__ == "__main__":
    main()
