# Changelog

## 2.2.0 (unreleased)

2.1.0 was never published; its changes are part of 2.2.0.

### Added
- **Coordinate Space** option (sidebar panel and export dialog, kept per .blend file): **Blender World (Convert to FS)**,
  the default and the behaviour so far, or **Armature Space = FS Space**, which writes the armature's own coordinates
  unchanged, as Tlarok's script, FLVER Bones Adder and Armature2JSON 1.0.0 read them. An FBX import that lies on its back
  in Blender exported lying down with Blender World. Applies to both modes and to the bounding boxes.
- **Match Vanilla Orientations** (top of the sidebar panel): turns the armature's bones that have vanilla names to the
  axes of the vanilla character skeleton, read from the **Vanilla Reference JSON** (c0000's Nodes.json, an add-on
  preference so its path is remembered), keeping each bone's head and length. It uses the Coordinate Space and axis
  options, so the export then writes the vanilla axes, and a custom Havok skeleton made from the same armature gets
  them too. X-Axis Mirror is switched off while matching. Ctrl+Z undoes it.
- **As Imported** button next to Reset Axes: sets Length Axis `Y` and Roll Axis `Z`, so each node keeps its bone's
  own axes, as a custom Havok skeleton does.
- **Reset Axes** button under Length Axis and Roll Axis (sidebar panel and export dialog): sets them back to `X`
  and `-Z`, the defaults, which match vanilla body bones. Ctrl+Z undoes it.

### Fixed
- Reinstalling or re-enabling the add-on in a running Blender now reloads all its modules. Before, Blender
  kept their old code in memory until it was restarted.

### Changed
- **Mark Root as Mesh Node** is off by default. Blender keeps a choice you made before, since it stores a preference
  only once it has been set.
- `build.ps1` has no built-in Blender path: pass `-Blender`, or put the path on the first line of `build.local.txt`
  (git-ignored).
- `tests/check_samples.py` takes the reference JSON's path after `--`; without it, it still reads `<blend>.json`.
- Version 2.2.0 (`src/blender_manifest.toml`, `pyproject.toml`, `uv.lock`).

## 2.0.0

The first release of the rewrite, from the Armature2JSON repository. It replaces Armature2JSON 1.0.0 (tag
v0.1.0) and takes over its extension id `armature2json`, so installing it replaces 1.0.0.

### Added
- Plain-Python unit tests in `tests/unit`, run with `uv run pytest` and also by the Blender suite:
  `link_indices` (`test_links.py`) and the SkeletonSet tool (moved from `tests/`).
- File safety (`src/core/files.py`, tested in `tests/unit/test_files.py`): Merge refuses an output that is the
  reference JSON (same path, another letter case or a link), and every export writes through a temporary file that
  is moved into place, so a failed export leaves an existing file untouched.
- Merge of an armature's bones into a reference node list: `src/core/merge.py` plans the order and parents
  (plain Python, tested in `tests/unit/test_merge.py`), and `writer.merge_nodes` fills in the values
  (`tests/test_merge_blender.py`). An added bone's values are relative to its parent as written in the output,
  so it lands where the bone is even when that parent keeps the reference's axes.
- Mode choice in the sidebar panel and the export dialog: "From Armature" (as before) or "Merge into Reference
  JSON", with the reference JSON path and a "Reparented Bones" choice (Keep Reference Parent; Use Blender
  Parent, Keep Placement; Use Blender Parent, Keep Values (1.0.0), as Armature2JSON 1.0.0 did). Every option and
  choice has a tooltip. Merge reports the number of added bones and warns about reference nodes with no bone and about
  reparented bones.
- `tests/check_samples.py` also checks Merge into Reference JSON: it drops leaf nodes from the vanilla list, merges
  the armature back in, and compares the kept and re-added nodes with vanilla.
- README: the two modes, a "Merge into Reference JSON" section with the reparent choices and the differences from
  Armature2JSON 1.0.0.

- Simplified Chinese (zh_HANS) interface, tooltips and messages (`src/core/i18n_zh_hans.py`), registered with
  `bpy.app.translations`. The table is checked for completeness and matching fields in
  `tests/unit/test_i18n.py`, and in Blender by `tests/test_i18n_blender.py`.

### Changed
- Version 2.0.0 (`src/blender_manifest.toml`, `pyproject.toml`).
- Mark Root as Mesh Node is an add-on preference (`src/prefs.py`) instead of a scene setting, so Blender remembers
  the choice between sessions. It also shows in the add-on's preferences.
- Every name is Armature2JSON: extension id `armature2json`, the sidebar tab and panel, the command
  `armature2json.export`, the scene settings `armature2json_*` and the pyproject package. The reference JSON
  path keeps the setting name 1.0.0 used, so a saved path carries over. The File > Export entry keeps
  FLVER_Editor's "Nodes JSON" name.
- Every report and error text is a template in `src/core/messages.py`; core errors are `ExportError`, a
  `ValueError` that keeps its template and fields. The Blender test runner switches the interface to English
  for the run, since the tests check English messages.
- `src/core/hierarchy.py` imports `bpy` only for type hints, so `link_indices` runs without Blender.
- `world_matrices` moved from `tests/check_samples.py` to `src/core/transforms.py`, with a new
  `node_local_matrix`.

## Rewrite, first steps (not released)

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
