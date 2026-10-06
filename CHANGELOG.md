# Changelog

## 0.1.0 (unreleased)

### Added
- Conversion from Blender bone transforms to FLVER node transforms (`src/core/transforms.py`): Y-up turn, Z
  mirror, length axis and roll axis options, and Euler angles in FLVER order computed in double precision so
  that rotations close to gimbal lock stay exact.
- Depth-first node order and FLVER child and sibling links (`src/core/hierarchy.py`).
- Per-node bounding boxes from weighted rest-pose vertices (`src/core/bounds.py`).
- Node list building with Flags and compact JSON output (`src/core/writer.py`), including the "Mark Root as
  Mesh Node" option.
- Extension manifest, File > Export > FLVER Nodes JSON (.json), and a "FLVER Nodes" sidebar panel.
- Test runner for Blender (`tests/run_tests.py`), unit and end-to-end tests, and a comparison against vanilla
  node JSON files (`tests/check_samples.py`).
