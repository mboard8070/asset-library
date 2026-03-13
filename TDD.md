# Technical Design Document: Digital Twin Asset Library

**Author:** Matthew Board
**Date:** March 13, 2026
**Status:** Draft

---

## 1. Purpose

Build a Single Source of Truth (SSOT) library of photorealistic 3D product assets — digital twins — that serve every downstream channel (e-commerce, social, retail, broadcast) from one canonical master. The system must handle global product variants, scale to hundreds of SKUs, and integrate AI-assisted workflows for texture generation, QC, and batch rendering.

---

## 2. Goals

- **One asset, many outputs** — a single master 3D product can render to any channel or format without rebuilding
- **Variant management** — regional labels, languages, and sizes are swappable configurations, not separate assets
- **Renderer-agnostic** — assets work across offline renderers (Arnold, V-Ray) and real-time engines (Unreal, Unity)
- **AI-accelerated** — automated texture generation, quality checks, and batch rendering
- **Team-scalable** — multiple artists and vendors can contribute without conflicts or drift

---

## 3. Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                     Asset Library                        │
│                                                         │
│  ┌──────────┐   ┌──────────┐   ┌──────────────────┐    │
│  │  Ingest   │──▶│  Store   │──▶│  Publish/Export   │   │
│  │  Pipeline │   │  (SSOT)  │   │  Pipeline         │   │
│  └──────────┘   └──────────┘   └──────────────────┘    │
│       ▲              │                  │               │
│       │              ▼                  ▼               │
│  ┌──────────┐   ┌──────────┐   ┌──────────────────┐    │
│  │    QC    │   │ Variant   │   │  Render Farm /    │   │
│  │  (AI +   │   │ Registry  │   │  Batch Output     │   │
│  │  Manual) │   │           │   │                   │   │
│  └──────────┘   └──────────┘   └──────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

### 3.1 Core Layers

| Layer | Responsibility | Key Tech |
|---|---|---|
| **Ingest** | Validate, normalize, and register incoming assets | Python CLI, USD validation, OpenAssetIO |
| **Store (SSOT)** | Versioned canonical assets with metadata | USD stages, Git LFS / Perforce for binary, PostgreSQL for metadata |
| **Variant Registry** | Map product SKUs to base geometry + variant configs | YAML/JSON manifests, MaterialX texture sets |
| **QC** | Automated + manual quality gates | AI texture/geometry checks, OpenCV, human review UI |
| **Publish/Export** | Channel-specific output generation | Render presets per channel, USD-to-engine exporters |
| **Render Farm** | Batch rendering and turntable generation | Deadline / cloud burst, standardized lighting rigs |

### 3.2 Asset Structure

Each product asset is a self-contained directory:

```
assets/
  olay-regenerist-50ml/
    manifest.yaml            # SKU metadata, variant mappings
    geo/
      base.usd               # Canonical geometry (no materials)
      lod1.usd               # LOD for real-time
      lod2.usd               # LOD for thumbnails
    materials/
      master.mtlx            # MaterialX master material
      textures/
        diffuse_4k.exr
        normal_4k.exr
        roughness_4k.exr
        translucency_4k.exr
    variants/
      en-us/
        label_diffuse.exr
        manifest_override.yaml
      ja-jp/
        label_diffuse.exr
        manifest_override.yaml
    rigs/
      turntable.usd          # Standard turntable camera + lights
      hero_beauty.usd        # Hero beauty shot rig
    renders/                  # Generated outputs (gitignored, cached)
      ecommerce/
      social/
      broadcast/
```

### 3.3 Manifest Schema

```yaml
# manifest.yaml
sku: "OLAY-REGEN-50ML"
product_name: "Olay Regenerist Micro-Sculpting Cream"
brand: "Olay"
category: "skincare"
archetype: "jar"             # Base shape template
base_geometry: "geo/base.usd"
material: "materials/master.mtlx"

variants:
  en-us:
    label_texture: "variants/en-us/label_diffuse.exr"
    product_name_localized: "Olay Regenerist"
  ja-jp:
    label_texture: "variants/ja-jp/label_diffuse.exr"
    product_name_localized: "オレイ リジェネリスト"

lods:
  hero: "geo/base.usd"       # Full resolution
  realtime: "geo/lod1.usd"   # Real-time engines
  thumbnail: "geo/lod2.usd"  # Quick previews

render_presets:
  ecommerce:
    resolution: [2048, 2048]
    renderer: "arnold"
    lighting_rig: "rigs/packshot_neutral.usd"
    background: "white"
  social:
    resolution: [1080, 1080]
    renderer: "unreal"
    lighting_rig: "rigs/lifestyle_warm.usd"
  broadcast:
    resolution: [3840, 2160]
    renderer: "arnold"
    lighting_rig: "rigs/hero_beauty.usd"
```

---

## 4. Technology Stack

### 4.1 Scene Description & Interchange

| Technology | Role |
|---|---|
| **USD (OpenUSD)** | Scene graph, composition, variant sets — the spine of the pipeline |
| **MaterialX** | Renderer-agnostic material definitions |
| **OpenAssetIO** | Standardized asset resolution across tools and engines |
| **Alembic** | Geometry cache interchange (legacy compat) |

### 4.2 DCC & Rendering

| Tool | Use |
|---|---|
| **Maya / Houdini / Blender** | Modeling, look-dev, scene assembly |
| **Arnold** | Offline hero rendering |
| **Unreal Engine** | Real-time rendering, virtual production, social content |
| **Nuke** | Compositing and final output |

### 4.3 Infrastructure

| Component | Technology |
|---|---|
| **Version control (code)** | Git |
| **Version control (assets)** | Git LFS (start), Perforce (scale) |
| **Metadata store** | PostgreSQL |
| **Asset browser / review** | Web UI (Next.js + Three.js for 3D preview) |
| **Render management** | Deadline (on-prem) / cloud burst to AWS Thinkbox |
| **CI/CD** | GitHub Actions — lint, validate USD, run QC on ingest |

### 4.4 AI Integration

| Capability | Approach |
|---|---|
| **Texture generation** | Diffusion models for label mockups and environment maps |
| **Automated QC** | Computer vision checks — texture resolution, UV coverage, polygon density, material consistency |
| **Batch variant generation** | Scripted label swaps + AI upscaling for regional texture variants |
| **Smart tagging** | Auto-classify assets by category, brand, archetype on ingest |

---

## 5. Pipeline Flows

### 5.1 Asset Ingest

```
Artist submits asset
  └─▶ CI validates USD structure
  └─▶ CI validates MaterialX materials
  └─▶ AI QC checks (texture res, UV coverage, poly budget)
  └─▶ Human review (look-dev approval via web UI)
  └─▶ Asset registered in metadata store
  └─▶ Thumbnails and preview renders generated
  └─▶ Asset published to SSOT
```

### 5.2 Variant Creation

```
PM requests new regional variant (e.g., ja-jp)
  └─▶ Label texture provided or AI-generated from template
  └─▶ manifest_override.yaml created
  └─▶ Validation render produced (turntable + packshot)
  └─▶ Review and approval
  └─▶ Variant registered under parent SKU
```

### 5.3 Channel Export

```
Request: "Generate ecommerce packshots for all Olay SKUs, en-us"
  └─▶ Query metadata store for matching assets
  └─▶ For each: load USD stage, apply variant, apply render preset
  └─▶ Submit to render farm
  └─▶ Post-process (compositing, crop, format conversion)
  └─▶ Deliver to output bucket (S3 / CDN)
```

---

## 6. Key Design Decisions

| Decision | Rationale |
|---|---|
| **USD as the spine** | Industry standard for composition and variants; native support in Maya, Houdini, Unreal, NVIDIA Omniverse |
| **MaterialX over proprietary shaders** | Renderer-agnostic; translates cleanly between Arnold, Unreal, V-Ray |
| **Manifests in YAML** | Human-readable, diffable, easy to template |
| **Git LFS to start, Perforce later** | Lower barrier to entry; migrate when team/asset count demands it |
| **AI QC as a gate, not a replacement** | Catches obvious issues automatically; human review remains final authority |
| **Archetype-based modeling** | New SKUs inherit base geometry (bottle, tube, jar, box), reducing per-asset build time |

---

## 7. Security & Access

- Asset repo requires authenticated access (SSO / API key)
- Write access gated by role (Artist, Lead, Admin)
- Render outputs stored in separate bucket with read-only CDN access
- No credentials stored in asset manifests

---

## 8. Performance Targets

| Metric | Target |
|---|---|
| Asset ingest to published | < 30 minutes (automated QC pass) |
| Variant creation (from existing base) | < 15 minutes |
| Batch render (100 SKU packshots) | < 4 hours |
| Asset browser load (3D preview) | < 3 seconds |
| Metadata query (any SKU lookup) | < 200ms |

---

## 9. Open Questions

- Perforce vs. Git LFS — at what asset count does migration become necessary?
- NVIDIA Omniverse as a collaboration layer — evaluate vs. raw USD + custom tooling
- Real-time preview fidelity — how close can Unreal Lumen get to Arnold ground truth for beauty products (translucency, SSS)?
- Licensing costs for Deadline vs. open-source alternatives (Flamenco, OpenCue)
- Label AI generation — fine-tune on brand guidelines or use template-based compositing?
