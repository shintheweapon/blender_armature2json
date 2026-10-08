# FLVER Node Exporter

A Blender 4.5 extension that writes a FLVER node list (the "Nodes JSON" that FLVER_Editor loads) straight from
a Blender armature. A vanilla node JSON is not needed.

## Install

1. Build the zip from PowerShell in this folder:

   ```
   .\build.ps1
   ```

   It runs Blender's own extension build, writes `dist\flver_node_export-0.1.0.zip` (the name follows `id` and
   `version` in `src\blender_manifest.toml`), and checks that the zip installs cleanly. If Blender lives
   elsewhere, pass its path: `.\build.ps1 -Blender "<path to blender.exe>"`. On a machine whose execution
   policy blocks scripts, run `powershell -ExecutionPolicy Bypass -File build.ps1` instead.
2. In Blender: Edit > Preferences > Get Extensions, open the menu at the top right, choose "Install from Disk"
   and pick the zip.

Without the script, zip the contents of the `src` folder by hand (not the folder itself, and without the
`__pycache__` folders), so that `blender_manifest.toml` sits at the top of the zip.

## Use

1. Select the armature (or keep it as the only armature in the scene).
2. Choose File > Export > FLVER Nodes JSON (.json), or use the "FLVER Nodes" tab in the 3D Viewport sidebar.
3. In FLVER_Editor, open the vanilla FLVER, press "Load JSON" and pick the exported file. Answer "Yes" when it
   asks to shift bone weights to the new bone indices.
4. Import the new meshes with "Import Model" (FBX). FLVER_Editor matches their vertex groups to nodes by name.
5. Open the "Dummy" window and check each dummy's parent and attach bone (see the warning below).
6. After the last change in FLVER_Editor, fix the SkeletonSet of the saved FLVER and use the fixed copy (see
   [Fix the SkeletonSet after Load JSON](#fix-the-skeletonset-after-load-json)).

### Options

| Option | Meaning | Default |
|---|---|---|
| Length Axis | The node axis that runs along each bone | `X` |
| Roll Axis | The node axis that each bone's Z axis becomes | `-Z` |
| Mark Root as Mesh Node | Write node 0 with Flags 12 (Mesh and Bone) instead of 8 (Bone) | on |

## Warning: indices that FLVER_Editor does not update

Nodes are written in depth-first order, which differs from the vanilla order. "Load JSON" replaces the node
list and, with the weight shift, moves vertex weights to the new indices by node name. It leaves these
references at their old positions:

- each dummy's parent bone and attach bone (hit points, effect points and similar);
- the node index of any vanilla mesh that stays in the FLVER;
- the SkeletonSet, a second copy of the bone hierarchy stored in the FLVER, which FLVER_Editor writes back
  unchanged.

Point the dummies and kept meshes at the right nodes again in FLVER_Editor after loading the JSON. Meshes
imported from FBX afterwards point at node 0, which is why "Mark Root as Mesh Node" is on by default. Rebuild
the SkeletonSet with the tool described next.

## Fix the SkeletonSet after Load JSON

A FLVER (version `0x2001A` and later) stores the bone hierarchy twice: in the node list and in the SkeletonSet.
"Load JSON" replaces the node list only, so the SkeletonSet keeps describing the old node order. In a working
FLVER, every SkeletonSet entry mirrors its node. In a FLVER whose SkeletonSet no longer matched its nodes,
ERCharacterScale showed the model with vanilla proportions instead of retargeting it; rebuilding the
SkeletonSet is the fix to test first.

Run the tool on the FLVER saved by FLVER_Editor, after the last edit there:

```
python tools\fix_skeleton_set.py "path\to\model.flver"
```

It writes `model.skelfix.flver` next to the input (or to a second path, if given), with every SkeletonSet entry
rebuilt from its node: parent, first child, next sibling, previous sibling, and the node's own index. When the
SkeletonSet holds more entries than the FLVER has nodes (left over from a model with more bones), it is shrunk
to the node count: the extra entries, which point at nodes that no longer exist, are zeroed. Nothing else in the
file changes, the input is never overwritten, and an existing output file is not replaced. Rename the fixed copy
to the original name when packing it into the game files.

The tool only needs Python 3. It refuses files it cannot fix safely: big-endian FLVERs, versions without a
SkeletonSet, a SkeletonSet with fewer entries than nodes, and node lists with inconsistent links.

## How bones become nodes

A node (one entry of the JSON list) is SoulsFormats' `FLVER.Node`. Each Blender bone becomes one node.

**Position.** FLVER space is Blender space turned so that Y points up, then mirrored along Z:
a point at Blender (x, y, z) lands at FLVER (x, z, y). The armature object's own transform is included.

**Axes.** Blender always runs a bone along its own Y axis; vanilla FLVER bones run along their own X axis. The
length and roll options set the conversion. For skeletons that came from FLVER_Editor's FBX export, the defaults
give the core bones (clavicles, upper arms, forearms, thighs, neck, fingers) their vanilla axes back, except
where a Blender bone points at a different child than in the vanilla skeleton.

**Rotation.** Euler angles in radians, applied X, then Z, then Y, as SoulsFormats'
`FLVER.Node.ComputeLocalTransform` expects. The angles are computed in double precision so that rotations
close to gimbal lock stay exact.

**Order.** Nodes are listed depth first: each parent comes before its children, and the children of one
parent keep Blender's order. ParentIndex, FirstChildIndex, NextSiblingIndex and PreviousSiblingIndex are
computed from that order; root nodes link to each other as siblings, as in vanilla node lists.

**Bounding boxes.** A node's BoundingBoxMin and BoundingBoxMax enclose every vertex weighted to its bone
(weight above zero), measured in the node's own axes. Only meshes with an Armature modifier that targets the
armature count, and vertices are taken in their rest position. A node with no weighted vertices gets a zero box.

**Flags.** Every node gets 8 (Bone). Node 0 gets 12 (Mesh and Bone) while "Mark Root as Mesh Node" is on.

**File.** One compact line of UTF-8 JSON without a BOM, field names in `FLVER.Node` order, numbers rounded to
single precision and whole numbers written without decimals, matching files exported by FLVER_Editor.

## Known limits

- A Blender file does not keep vanilla node axes. Bones other than the core ones (hair, cloth, physics and
  so on) get the axes the options produce, which can differ from vanilla by quarter or half turns.
- Scale is 1 unless the armature object itself is scaled; Blender rest bones have no scale.
- Bounding boxes ignore modifiers and shape keys; they use the mesh as stored.
- The DummyOwner flag (2) is never set.

## Development

### Virtual environment

The development tools run in a Python 3.11 virtual environment managed by [uv](https://docs.astral.sh/uv/),
the same minor version as Blender 4.5's Python. `pyproject.toml` lists what is wanted and `uv.lock` pins
exactly what is installed; both are committed. The extension itself needs nothing beyond Blender.

Create or update `.venv` from the lock file (uv downloads Python 3.11 if needed):

```
uv sync
```

Run the tests that need no Blender:

```
uv run pytest tests\test_fix_skeleton_set.py
```

### Tests in Blender

Run the full test suite inside Blender 4.5:

```
"blender.exe" -b -P tests\run_tests.py
```

Compare the output with a vanilla node JSON saved next to a sample `.blend` under the same name:

```
"blender.exe" -b sample.blend -P tests\check_samples.py
```

The check passes when names and parents match, joint positions match within 1e-4, and every box, turned into
the vanilla node's axes, matches within 1e-4. It also lists which core bones get their vanilla axes.
