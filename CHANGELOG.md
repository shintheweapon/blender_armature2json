# Changelog

## Unreleased

### Added
- Conversion from Blender bone transforms to FLVER node transforms (`src/core/transforms.py`): Y-up turn, Z
  mirror, length axis and roll axis options, Euler angles in FLVER order.
- Depth-first node order and FLVER child and sibling links (`src/core/hierarchy.py`).
- Per-node bounding boxes from weighted rest-pose vertices (`src/core/bounds.py`).
- Node list building with Flags and compact JSON output (`src/core/writer.py`), including the "Mark root as
  mesh node" option.
- Test runner for Blender (`tests/run_tests.py`) and tests for the conversion.
