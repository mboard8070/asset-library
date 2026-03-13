"""
Texture projection for Safeguard pump bottle.

Projects front and back product photos onto the 3D mesh UV layout.
Removes white studio backgrounds, preserves label content (including
white areas within the label like the back panel), and fills non-label
areas with the base bottle color.

Run:
    python3 scripts/texture_project.py \
        mesh.obj front.jpg back.jpg output.png [resolution]
"""

import sys
import numpy as np
from pathlib import Path
from PIL import Image, ImageFilter


# Base bottle color (lavender purple plastic) — from manifest material_zones
BASE_COLOR = np.array([148, 112, 168], dtype=np.uint8)  # RGB approximation of [0.42, 0.18, 0.55] + transmission


def create_bottle_mask(img_array):
    """Create a mask that isolates the bottle from the white studio background.

    Returns a float mask [0, 1] where 1 = bottle pixel, 0 = background.
    Uses luminance threshold + edge detection to find the bottle silhouette.
    The white areas INSIDE the bottle (like the back label) are preserved
    because we flood-fill from the edges.
    """
    h, w = img_array.shape[:2]
    gray = np.mean(img_array.astype(np.float32), axis=2)

    # Start with a rough threshold — background is very white (>245)
    is_white = gray > 240

    # Flood fill from the edges to find connected white regions
    # (this preserves white areas inside the bottle)
    from scipy import ndimage

    # Create a seed mask: white pixels touching the image border
    border_seed = np.zeros_like(is_white)
    border_seed[0, :] = is_white[0, :]
    border_seed[-1, :] = is_white[-1, :]
    border_seed[:, 0] = is_white[:, 0]
    border_seed[:, -1] = is_white[:, -1]

    # Label connected white regions
    labeled, num_features = ndimage.label(is_white)

    # Find which labels touch the border
    border_labels = set(labeled[border_seed].flatten()) - {0}

    # Background = white regions connected to the border
    background = np.isin(labeled, list(border_labels))

    # Mask: not background = bottle
    mask = (~background).astype(np.float32)

    # Slight erosion then blur for clean edges
    mask_img = Image.fromarray((mask * 255).astype(np.uint8))
    mask_img = mask_img.filter(ImageFilter.MinFilter(3))   # Erode 1px
    mask_img = mask_img.filter(ImageFilter.GaussianBlur(2)) # Soft edge
    mask = np.array(mask_img).astype(np.float32) / 255.0

    return mask


def parse_obj(filepath):
    """Parse OBJ file → vertices, UVs, normals, faces."""
    vertices = []
    uvs = []
    normals = []
    faces = []

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
                face_v, face_vt, face_vn = [], [], []
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
    edge1 = v1 - v0
    edge2 = v2 - v0
    normal = np.cross(edge1, edge2)
    length = np.linalg.norm(normal)
    if length > 0:
        normal /= length
    return normal


def barycentric(p, a, b, c):
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
    inv = 1.0 / denom
    u = (dot11 * dot02 - dot01 * dot12) * inv
    v = (dot00 * dot12 - dot01 * dot02) * inv
    return 1 - u - v, v, u


def sample_image(img_array, u, v):
    """Bilinear sample from image at UV coords."""
    h, w = img_array.shape[:2]
    x = u * (w - 1)
    y = (1.0 - v) * (h - 1)
    x0 = max(0, min(int(x), w - 2))
    y0 = max(0, min(int(y), h - 2))
    fx = x - x0
    fy = y - y0
    c00 = img_array[y0, x0].astype(np.float32)
    c10 = img_array[y0, x0 + 1].astype(np.float32)
    c01 = img_array[y0 + 1, x0].astype(np.float32)
    c11 = img_array[y0 + 1, x0 + 1].astype(np.float32)
    return c00 * (1-fx)*(1-fy) + c10*fx*(1-fy) + c01*(1-fx)*fy + c11*fx*fy


def sample_mask(mask, u, v):
    """Sample mask value at UV coords."""
    h, w = mask.shape
    x = u * (w - 1)
    y = (1.0 - v) * (h - 1)
    x0 = max(0, min(int(round(x)), w - 1))
    y0 = max(0, min(int(round(y)), h - 1))
    return mask[y0, x0]


def rasterize_triangle(output, uv0, uv1, uv2, color_func, resolution):
    px = np.array([uv0[0], uv1[0], uv2[0]]) * (resolution - 1)
    py = np.array([uv0[1], uv1[1], uv2[1]]) * (resolution - 1)
    min_x = max(0, int(min(px)))
    max_x = min(resolution - 1, int(max(px)) + 1)
    min_y = max(0, int(min(py)))
    max_y = min(resolution - 1, int(max(py)) + 1)
    a = np.array([px[0], py[0]])
    b = np.array([px[1], py[1]])
    c = np.array([px[2], py[2]])

    for y in range(min_y, max_y + 1):
        for x in range(min_x, max_x + 1):
            w0, w1, w2 = barycentric(np.array([float(x), float(y)]), a, b, c)
            if w0 >= -0.001 and w1 >= -0.001 and w2 >= -0.001:
                color = color_func(w0, w1, w2)
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

    # Load and mask reference images
    print("Loading and masking reference images...")
    front_img = np.array(Image.open(front_path).convert('RGB'))
    back_img = np.array(Image.open(back_path).convert('RGB'))
    print(f"  Front: {front_img.shape}, Back: {back_img.shape}")

    print("  Creating bottle masks (flood-fill from edges)...")
    front_mask = create_bottle_mask(front_img)
    back_mask = create_bottle_mask(back_img)

    front_coverage = np.mean(front_mask > 0.5)
    back_coverage = np.mean(back_mask > 0.5)
    print(f"  Front mask coverage: {front_coverage:.1%}")
    print(f"  Back mask coverage: {back_coverage:.1%}")

    # Save masks for debugging
    Image.fromarray((front_mask * 255).astype(np.uint8)).save(
        str(Path(output_path).parent / "debug_front_mask.png"))
    Image.fromarray((back_mask * 255).astype(np.uint8)).save(
        str(Path(output_path).parent / "debug_back_mask.png"))
    print("  Saved debug masks")

    # Mesh bounds
    min_x, max_x = vertices[:, 0].min(), vertices[:, 0].max()
    min_z, max_z = vertices[:, 2].min(), vertices[:, 2].max()
    width = max_x - min_x
    height = max_z - min_z
    print(f"  Mesh width: {width:.4f}, height: {height:.4f}")

    # Photo framing — where the bottle sits in the image
    bottle_u_min = 0.24
    bottle_u_max = 0.76
    bottle_v_min = 0.02
    bottle_v_max = 0.98

    # Fill output with base bottle color
    output = np.full((resolution, resolution, 3), BASE_COLOR, dtype=np.uint8)

    # Rasterize
    print("Rasterizing triangles...")
    total = len(faces)

    for fi, (fv, fvt, fvn) in enumerate(faces):
        if fi % 20000 == 0:
            print(f"  {fi}/{total} ({100*fi//total}%)")

        if len(fv) < 3 or len(fvt) < 3:
            continue

        for i in range(1, len(fv) - 1):
            i0, i1, i2 = 0, i, i + 1
            vi0, vi1, vi2 = fv[i0], fv[i1], fv[i2]
            ti0, ti1, ti2 = fvt[i0], fvt[i1], fvt[i2]

            v0, v1, v2 = vertices[vi0], vertices[vi1], vertices[vi2]
            uv0, uv1, uv2 = uvs[ti0], uvs[ti1], uvs[ti2]

            face_normal = compute_face_normal(v0, v1, v2)
            normal_y = face_normal[1]

            # Blend: 0 = front, 1 = back
            blend = np.clip((normal_y + 0.2) / 0.4, 0.0, 1.0)

            def make_color_func(v0=v0, v1=v1, v2=v2, blend=blend):
                def color_func(w0, w1, w2):
                    pos = w0 * v0 + w1 * v1 + w2 * v2
                    nx = (pos[0] - min_x) / width
                    nz = (pos[2] - min_z) / height

                    # Image UV for front
                    fu = bottle_u_min + nx * (bottle_u_max - bottle_u_min)
                    fv = bottle_v_min + nz * (bottle_v_max - bottle_v_min)

                    # Image UV for back (X flipped)
                    bu = bottle_u_max - nx * (bottle_u_max - bottle_u_min)
                    bv = fv

                    # Sample colors and masks
                    front_color = sample_image(front_img, fu, fv)
                    back_color = sample_image(back_img, bu, bv)
                    front_alpha = sample_mask(front_mask, fu, fv)
                    back_alpha = sample_mask(back_mask, bu, bv)

                    # Blended photo color
                    photo_color = front_color * (1 - blend) + back_color * blend

                    # Blended mask (how much of this pixel is actual bottle vs background)
                    photo_alpha = front_alpha * (1 - blend) + back_alpha * blend

                    # Mix: photo where mask says bottle, base color where background
                    base = BASE_COLOR.astype(np.float32)
                    return photo_color * photo_alpha + base * (1 - photo_alpha)

                return color_func

            rasterize_triangle(output, uv0, uv1, uv2, make_color_func(), resolution)

    print(f"  {total}/{total} (100%)")

    # Save
    Image.fromarray(output).save(output_path)
    file_size = Path(output_path).stat().st_size
    print(f"Saved: {output_path} ({file_size / 1024:.0f} KB)")

    non_base = np.any(output != BASE_COLOR, axis=2).sum()
    total_px = resolution * resolution
    print(f"Label coverage: {non_base}/{total_px} pixels ({100*non_base/total_px:.1f}%)")

    print("=" * 60)
    print("Done!")
    print("=" * 60)


if __name__ == "__main__":
    main()
