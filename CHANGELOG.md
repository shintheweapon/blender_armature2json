# Changelog

## 0.2.0 (unreleased)

### Added
- Plain-Python unit tests in `tests/unit`, run with `uv run pytest` and also by the Blender suite:
  `link_indices` (`test_links.py`) and the SkeletonSet tool (moved from `tests/`).
- Merge of an armature's bones into an input node list: `src/core/merge.py` plans the order and parents
  (plain Python, tested in `tests/unit/test_merge.py`), and `writer.merge_nodes` fills in the values
  (`tests/test_merge_blender.py`). An added bone's values are relative to its parent as written in the output,
  so it lands where the bone is even when that parent keeps the input's axes.
- Mode choice in the sidebar panel and the export dialog: "From Armature" (as before) or "Merge into Input
  JSON", with the input JSON path and a "Reparented Bones" choice (Keep Input Parent; Use Blender Parent, Keep
  Placement; Use Blender Parent, Keep Values as the old Armature2JSON add-on did). Every option and choice has
  a tooltip. Merge reports the number of added bones and warns about input nodes with no bone and about
  reparented bones.

### Changed
- `src/core/hierarchy.py` imports `bpy` only for type hints, so `link_indices` runs without Blender.
- `world_matrices` moved from `tests/check_samples.py` to `src/core/transforms.py`, with a new
  `node_local_matrix`.

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
- `build.ps1`, which builds the installable zip with Blender's extension build and checks its layout.
- `tools/fix_skeleton_set.py`, which rebuilds a FLVER's SkeletonSet from its node list after FLVER_Editor's
  "Load JSON", writing a fixed copy. A SkeletonSet larger than the node list is shrunk to the node count, with
  the unused entries zeroed.
- Test runner for Blender (`tests/run_tests.py`), unit and end-to-end tests, and a comparison against vanilla
  node JSON files (`tests/check_samples.py`).
- Development environment: a uv-managed Python 3.11 virtual environment with pinned test dependencies
  (`pyproject.toml`, `uv.lock`, `.python-version`).
