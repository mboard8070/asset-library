# Project Plan: Digital Twin Asset Library

**Author:** Matthew Board
**Date:** March 13, 2026
**Status:** Draft

---

## Overview

Build a production-grade digital twin asset library that demonstrates the first pillar of the P&G COHO Technical Director role: **Digital Twin Pipeline Architecture & Leadership**. This is a working prototype — not a mockup — that proves the pipeline end-to-end with real assets.

---

## Phase 1: Foundation (Weeks 1-2)

**Goal:** Repo structure, tooling, and a single working asset from ingest to render.

### Tasks

- [ ] Define directory structure matching TDD asset layout
- [ ] Set up Git LFS for binary assets (`.exr`, `.usd`, `.abc`, `.png`)
- [ ] Create the manifest schema (YAML) with JSON Schema validation
- [ ] Build the ingest CLI (`python -m assetlib ingest <path>`)
  - Validates directory structure
  - Validates USD file integrity (pxr.Usd stage open)
  - Validates MaterialX file
  - Registers asset in local metadata store (SQLite for prototype, PostgreSQL later)
- [ ] Create one hero asset — pick a simple product (bottle archetype)
  - Base geometry in USD
  - MaterialX material with PBR textures
  - Two regional variants (en-us, ja-jp) with label texture swaps
  - Turntable rig
- [ ] Generate first renders (Arnold or Blender Cycles) from the pipeline

### Deliverables
- Working `assetlib ingest` command
- One complete product asset in the library
- Renders from two variants

---

## Phase 2: Variant System & Batch Rendering (Weeks 3-4)

**Goal:** Prove the "one asset, many outputs" promise at small scale.

### Tasks

- [ ] Build variant resolution logic — given a SKU + locale, compose the correct USD stage with overrides
- [ ] Implement render preset system — define channel presets (ecommerce, social, broadcast) in YAML
- [ ] Build batch render CLI (`python -m assetlib render --sku "*" --channel ecommerce --locale en-us`)
- [ ] Standardized lighting rigs per channel (packshot neutral, lifestyle warm, hero beauty)
- [ ] Post-processing pipeline (crop, format conversion, naming convention)
- [ ] Add 3-5 more product assets across different archetypes (jar, tube, box, pump bottle)

### Deliverables
- Batch render of all assets across channels
- Consistent output naming and folder structure
- Variant swapping working across all archetypes

---

## Phase 3: AI Integration (Weeks 5-6)

**Goal:** Demonstrate AI-accelerated workflows.

### Tasks

- [ ] **Automated QC module**
  - Texture resolution check (min 4K for hero)
  - UV coverage analysis (flag islands < threshold)
  - Polygon budget validation per LOD tier
  - Material consistency check (PBR value ranges)
- [ ] **AI texture generation**
  - Label variant generation from template + text prompt
  - Environment map generation for lifestyle renders
  - Texture upscaling for lower-res source assets
- [ ] **Smart tagging on ingest**
  - Auto-classify archetype, brand, category from geometry + textures
  - Auto-generate search keywords for the asset browser
- [ ] Integrate QC as a CI gate — GitHub Actions runs checks on every asset PR

### Deliverables
- QC report generated on every ingest
- At least one AI-generated label variant that passes QC
- CI pipeline with automated validation

---

## Phase 4: Web UI & Review (Weeks 7-8)

**Goal:** Non-technical stakeholders can browse, preview, and approve assets.

### Tasks

- [ ] Asset browser web app (Next.js)
  - Grid view with thumbnail previews
  - Filter by brand, category, archetype, locale
  - Search by SKU or product name
- [ ] 3D preview (Three.js / model-viewer)
  - Load USD-exported glTF for real-time preview
  - Variant switcher (toggle locales in the viewer)
  - Turntable and orbit controls
- [ ] Review workflow
  - Approve / request changes on pending assets
  - Comment thread per asset
  - Status tracking (draft → review → approved → published)
- [ ] Render gallery — view all generated outputs per asset

### Deliverables
- Working web UI with 3D preview
- Review workflow for asset approval
- Deployed prototype (local or cloud)

---

## Phase 5: Scale & Real-Time (Weeks 9-10)

**Goal:** Prove the pipeline works at scale and in real-time engines.

### Tasks

- [ ] Unreal Engine integration
  - USD import plugin setup
  - MaterialX-to-Unreal material translation
  - Real-time packshot scene with Lumen GI
- [ ] Virtual production scene — product in environment with real-time lighting
- [ ] Performance benchmark — render 50+ SKUs across 3 channels in batch
- [ ] Export to Omniverse (if evaluating NVIDIA collaboration layer)
- [ ] Documentation — pipeline guide for onboarding artists and vendors

### Deliverables
- Unreal real-time renders matching offline quality benchmarks
- Batch render benchmark results
- Pipeline documentation

---

## Technical Milestones

| Milestone | Target | Proves |
|---|---|---|
| First asset ingested | End of Week 1 | Pipeline works end-to-end |
| First batch render | End of Week 3 | One asset → many outputs |
| AI QC gate passing | End of Week 5 | Automated quality at scale |
| Web UI with 3D preview | End of Week 7 | Stakeholder accessibility |
| 50-SKU batch benchmark | End of Week 9 | Production scalability |

---

## Tech Stack Summary

| Layer | Choice | Fallback |
|---|---|---|
| Scene graph | OpenUSD | — |
| Materials | MaterialX | glTF PBR (web preview) |
| Metadata | SQLite → PostgreSQL | — |
| CLI framework | Python (click) | — |
| Rendering (offline) | Blender Cycles (free) | Arnold |
| Rendering (real-time) | Unreal Engine 5 | — |
| Web UI | Next.js + Three.js | — |
| CI/CD | GitHub Actions | — |
| AI (textures) | Stable Diffusion / SDXL | — |
| AI (QC) | OpenCV + custom classifiers | — |

---

## Risk Register

| Risk | Impact | Mitigation |
|---|---|---|
| USD tooling complexity | High | Start with Python `pxr` bindings; lean on Houdini for authoring |
| MaterialX-to-engine gaps | Medium | Test material translation early; maintain per-engine fallback shaders |
| Asset size bloats repo | High | Git LFS from day one; evaluate Perforce at Phase 5 |
| AI texture quality inconsistent | Medium | AI generates candidates; human selects and retouches |
| Scope creep | High | Each phase has hard deliverables; ship the prototype, not the platform |

---

## Success Criteria

This project succeeds if it can demonstrate, in a live walkthrough:

1. **Ingest** a new product asset via CLI with automated QC
2. **Generate variants** for multiple regions from a single base
3. **Batch render** packshots across ecommerce/social/broadcast channels
4. **Preview** assets in a web browser with 3D viewer and variant switching
5. **Render in real-time** in Unreal Engine from the same source asset

That's the first pillar, built and running.
