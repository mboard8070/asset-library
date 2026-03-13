"""MaterialX (.mtlx) generator from manifest material zone definitions."""

from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, ElementTree, indent


# Maps our YAML param names to MaterialX standard_surface input names
PARAM_MAP = {
    "base_color": ("color3", None),
    "base_color_map": ("filename", "base_color"),
    "metalness": ("float", None),
    "specular": ("float", None),
    "specular_color": ("color3", None),
    "specular_roughness": ("float", None),
    "specular_roughness_map": ("filename", "specular_roughness"),
    "normal_map": ("filename", "normal"),
    "transmission": ("float", None),
    "transmission_color": ("color3", None),
    "coat": ("float", None),
    "coat_roughness": ("float", None),
    "subsurface": ("float", None),
    "subsurface_color": ("color3", None),
    "subsurface_radius": ("color3", None),
    "opacity": ("color3", None),
    "emission": ("float", None),
    "emission_color": ("color3", None),
}


def _format_value(value) -> str:
    """Format a Python value as a MaterialX attribute string."""
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    return str(value)


def _add_texture_node(nodegraph: Element, param_name: str, filename: str,
                      mat_name: str) -> str:
    """Add a texture image node to the nodegraph. Returns the output reference."""
    node_name = f"{mat_name}_{param_name}_tex"

    # Determine output type based on param
    is_color = param_name in ("base_color", "transmission_color",
                               "subsurface_color", "emission_color",
                               "specular_color")
    out_type = "color3" if is_color else "float"

    image_node = SubElement(nodegraph, "image", {
        "name": node_name,
        "type": out_type,
    })
    SubElement(image_node, "input", {
        "name": "file",
        "type": "filename",
        "value": filename,
    })

    # Normal maps need a normalmap node
    if param_name == "normal":
        normalmap_name = f"{mat_name}_normalmap"
        nm_node = SubElement(nodegraph, "normalmap", {
            "name": normalmap_name,
            "type": "vector3",
        })
        SubElement(nm_node, "input", {
            "name": "in",
            "type": "vector3",
            "nodename": node_name,
        })
        # Output for normal
        out_name = f"{normalmap_name}_out"
        output = SubElement(nodegraph, "output", {
            "name": out_name,
            "type": "vector3",
            "nodename": normalmap_name,
        })
        return out_name

    out_name = f"{node_name}_out"
    SubElement(nodegraph, "output", {
        "name": out_name,
        "type": out_type,
        "nodename": node_name,
    })
    return out_name


def generate_mtlx(material_zones: dict, output_path: Path) -> Path:
    """Generate a MaterialX file from material zone definitions.

    Args:
        material_zones: dict mapping zone names to their material properties.
        output_path: where to write the .mtlx file.

    Returns:
        The path to the written file.
    """
    root = Element("materialx", {"version": "1.39"})

    for zone_name, params in material_zones.items():
        shader_type = params.get("type", "standard_surface")

        # Collect texture params vs direct value params
        texture_params = {}
        value_params = {}
        for key, val in params.items():
            if key == "type":
                continue
            if key in PARAM_MAP:
                param_type, target = PARAM_MAP[key]
                if param_type == "filename":
                    texture_params[target or key] = val
                else:
                    value_params[key] = (param_type, val)

        # If we have textures, create a nodegraph
        tex_outputs = {}
        if texture_params:
            ng_name = f"NG_{zone_name}"
            nodegraph = SubElement(root, "nodegraph", {"name": ng_name})

            for target_param, filename in texture_params.items():
                out_ref = _add_texture_node(
                    nodegraph, target_param, filename, zone_name
                )
                tex_outputs[target_param] = (ng_name, out_ref)

        # Create the shader node
        shader_name = f"SR_{zone_name}"
        shader = SubElement(root, shader_type, {
            "name": shader_name,
            "type": "surfaceshader",
        })

        # Direct value inputs
        for key, (param_type, val) in value_params.items():
            SubElement(shader, "input", {
                "name": key,
                "type": param_type,
                "value": _format_value(val),
            })

        # Texture-connected inputs
        for target_param, (ng_name, out_ref) in tex_outputs.items():
            is_normal = target_param == "normal"
            SubElement(shader, "input", {
                "name": target_param if not is_normal else "normal",
                "type": "vector3" if is_normal else (
                    "color3" if target_param in (
                        "base_color", "transmission_color",
                        "subsurface_color", "emission_color",
                        "specular_color"
                    ) else "float"
                ),
                "nodegraph": ng_name,
                "output": out_ref,
            })

        # Create the material
        mat_name = f"MAT_{zone_name}"
        material = SubElement(root, "surfacematerial", {
            "name": mat_name,
            "type": "material",
        })
        SubElement(material, "input", {
            "name": "surfaceshader",
            "type": "surfaceshader",
            "nodename": shader_name,
        })

    # Write
    indent(root, space="  ")
    tree = ElementTree(root)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(output_path, encoding="unicode", xml_declaration=True)

    return output_path
