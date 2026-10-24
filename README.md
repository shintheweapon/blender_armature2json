# Armature2JSON

A Blender 4.5 extension that writes a FLVER node list (the "Nodes JSON" or the bone JSON that FLVER Editor loads) from a Blender armature, in one of two modes:

- **From Armature:** every node is built from the armature. A vanilla node JSON is not needed.
- **Merge into Reference JSON:** every node of a reference JSON (for example a vanilla one exported by FLVER Editor) is kept, and the armature's bones that it lacks are added. This is what Armature2JSON 1.0.0 did.

Version 2.0.0 is a rewrite of Armature2JSON 1.0.0: new maths, the From Armature mode, safe file writing and a Simplified Chinese interface (see [Upgrading from Armature2JSON 1.0.0](#upgrading-from-armature2json-100)).

## Install

1. Build the zip from PowerShell in this folder:

   ```
   .\build.ps1
   ```

   It runs Blender's own extension build, writes `dist\armature2json-2.2.0.zip` (the name follows `id` and `version` in `src\blender_manifest.toml`), and checks that the zip installs cleanly. It needs the path to your blender.exe: pass it with `.\build.ps1 -Blender "<path to blender.exe>"`, or put it on the first line of `build.local.txt` next to `build.ps1` (git-ignored, so the path stays on your machine). On a machine whose execution policy blocks scripts, run `powershell -ExecutionPolicy Bypass -File build.ps1` instead.
2. In Blender: Edit > Preferences > Get Extensions, open the menu at the top right, choose "Install from Disk" and pick the zip.

Without the script, zip the contents of the `src` folder by hand (not the folder itself, and without the `__pycache__` folders), so that `blender_manifest.toml` sits at the top of the zip.

### Upgrading from Armature2JSON 1.0.0

- Installing the 2.0.0 zip replaces 1.0.0, because both use the extension id `armature2json`.
- The 1.0.0 workflow is the Merge into Reference JSON mode. The reference JSON path saved in a .blend file carries over; the 1.0.0 axis settings do not, because the maths changed (see [Merge into Reference JSON](#merge-into-reference-json)).
- If the earlier test build `flver_node_export` is installed, uninstall it: it is this exporter under its old name.

## Use

1. Select the armature (or keep it as the only armature in the scene).
2. Choose File > Export > FLVER Nodes JSON (.json), or use the "Armature2JSON" tab in the 3D Viewport sidebar. Pick the mode; for Merge into Reference JSON, also pick the reference JSON. Hover any option for its tooltip. The add-on follows Blender's interface language; Simplified Chinese (简体中文) is included, for the interface, tooltips and messages, as far as Blender's Translation preferences allow.
3. In FLVER Editor, open the vanilla FLVER, press "Load JSON" and pick the exported file. Answer "Yes" when it asks to shift bone weights to the new bone indices.
4. Import the new meshes with "Import Model" (FBX). FLVER Editor matches their vertex groups to nodes by name.
5. Open the "Dummy" window and check each dummy's parent and attach bone (see the warning below).
6. After the last change in FLVER Editor, fix the SkeletonSet of the saved FLVER and use the fixed copy (see [Fix the SkeletonSet after Load JSON](#fix-the-skeletonset-after-load-json)).

### Options

| Option | Meaning | Default |
|---|---|---|
| Mode | From Armature, or Merge into Reference JSON | From Armature |
| Reference JSON | Merge only: the node JSON used as the reference (usually a vanilla one) | empty |
| Reparented Bones | Merge only: what to do with reference bones that have another parent in Blender (see [Merge into Reference JSON](#merge-into-reference-json)) | Keep Reference Parent |
| Coordinate Space | How Blender coordinates become FS (FLVER) coordinates: Blender World (Convert to FS) or Armature Space = FS Space (see [How bones become nodes](#how-bones-become-nodes)) | Blender World (Convert to FS) |
| Length Axis | The node axis that runs along each bone (in Merge, each added bone) | `X` |
| Roll Axis | The node axis that each bone's Z axis becomes (in Merge, each added bone's) | `-Z` |
| Vanilla Reference JSON | The node JSON of the vanilla character skeleton, for Match Vanilla Orientations (see [Vanilla orientations on the armature](#vanilla-orientations-on-the-armature)) | empty |
| Mark Root as Mesh Node | From Armature only: write node 0 with Flags 12 (Mesh and Bone) instead of 8 (Bone) | off |

**Reset Axes**, under the two axis options, sets them back to `X` and `-Z`. **As Imported**, next to it, sets them to `Y` and `Z`: each node keeps its bone's own axes.

Each .blend file keeps its own options, except Vanilla Reference JSON and Mark Root as Mesh Node: they are add-on preferences, so Blender remembers them between sessions (when it saves its preferences, which it does at quit by default). They also show in Edit > Preferences > Add-ons > Armature2JSON. Blender stores a preference only once it has been set: Mark Root as Mesh Node is off by default since 2.2.0, and a choice you made before stays.

## Vanilla orientations on the armature

The game's animations move the vanilla body bones (Pelvis, Spine, the arms and so on) in the axes of the vanilla character skeleton, c0000. A body bone with other axes twists in game, unless ERCS applies the animations relative to the rest pose. A custom physics skeleton (`Skeleton.hkx`, and the cloth `_c.hkx`) made with the Havok tools takes its bone axes from the Blender armature, so the axes have to be right on the armature itself, not only in the JSON.

**Match Vanilla Orientations**, at the top of the sidebar panel, does this. It reads the Vanilla Reference JSON, the node JSON of `chr\c0000-chrbnd-dcx\c0000.flver` saved by FLVER Editor (Nodes.json); the add-on remembers its path. Every bone of the armature whose name is in that JSON:

- gets the axes that export as the vanilla node's axes, with the Coordinate Space and axis options set at that moment;
- keeps its own head and length, so the model keeps its proportions.

Matched bones and their children are disconnected first, so no child moves. X-Axis Mirror is switched off while the bones are matched and restored afterwards. Bones of other names stay as they are, and a skinned mesh in rest pose keeps its shape. Matched bones may look sideways in Blender. Ctrl+Z undoes the match.

For a model with a custom physics skeleton, the recipe confirmed in game without ERCS:

1. Set Coordinate Space to Armature Space = FS Space and press As Imported.
2. Press Match Vanilla Orientations, with the armature in its rest pose (poses and actions of matched bones are relative to the old axes, so they change).
3. Export the JSON.
4. Export the FBX for the Havok tools from the same armature and make `Skeleton.hkx` and the cloth `_c.hkx` again; recheck any cloth setting given in a bone's own axes.

The recipe was confirmed with Tlarok's bones adder on the same armature, which writes the same nodes as Armature2JSON with these settings. Blender World (Convert to FS) with a custom physics skeleton has not been checked in game.

## Warning: indices that FLVER Editor does not update

In From Armature mode, nodes are written in depth-first order, which differs from the vanilla order. In Merge mode, the reference's nodes up to the last node with Flags 8 or 10 keep their indices, and the nodes after it (mesh and dummy-owner nodes in a vanilla list) move down by the number of added bones. "Load JSON" replaces the node list and, with the weight shift, moves vertex weights to the new indices by node name. It leaves these references at their old positions:

- each dummy's parent bone and attach bone (hit points, effect points and similar);
- the node index of any vanilla mesh that stays in the FLVER;
- the SkeletonSet, a second copy of the bone hierarchy stored in the FLVER, which FLVER Editor writes back unchanged.

Point the dummies and kept meshes at the right nodes again in FLVER Editor after loading the JSON. In Merge mode with a vanilla reference JSON, dummies that point at bones keep valid indices; kept meshes, whose nodes come after the added bones, still need re-pointing. Meshes imported from FBX afterwards point at node 0; turn on "Mark Root as Mesh Node" (From Armature mode) to write node 0 as a mesh node for them. Rebuild the SkeletonSet with the tool described in [Fix the SkeletonSet after Load JSON](#fix-the-skeletonset-after-load-json).

## Merge into Reference JSON

**Kept nodes.** Every reference node is copied unchanged: values, box and Flags. Only its index, its parent index and its child and sibling links change where needed. Reference nodes with no bone in the armature are kept too, and the export lists them in a warning. The reference JSON is only read: an output path that names the reference file (also through another letter case or a link) stops the export with a message.

**Added bones.** Bones the reference lacks are added in depth-first order as one block after the last reference node with Flags 8 or 10 (at the start if there is none), with Flags 8. Their values follow [How bones become nodes](#how-bones-become-nodes), taken relative to their parent as it is written in the output. A vanilla parent keeps its vanilla axes, so the added bone's values are computed against those axes and it lands where the bone is in Blender.

**Reparented bones.** A bone that is in the reference but has another parent in Blender is listed in a warning, and the Reparented Bones option decides its parent. Example: the reference has `L_Hand` under `L_Forearm`, and in Blender you moved `L_Hand` under `L_UpperArm`.

| Choice | Parent written | `L_Hand`'s values | Result |
|---|---|---|---|
| Keep Reference Parent | `L_Forearm` | as in the reference | stays in place |
| Use Blender Parent, Keep Placement | `L_UpperArm` | recomputed relative to `L_UpperArm` | stays in place, same axes |
| Use Blender Parent, Keep Values (1.0.0) | `L_UpperArm` | as in the reference, now read relative to `L_UpperArm` | moves |

A bone cannot be reparented under an added bone, because added bones come after the reference's bones and a parent must come first; the export stops and names the bone. Keep Reference Parent always works.

**Difference from Armature2JSON 1.0.0.** Both keep the reference nodes and add the missing bones in the same place. They compute the added bones differently:

|  | 1.0.0 | 2.0.0 |
|---|---|---|
| Space | Blender armature space; the armature object's transform is ignored | FLVER space (Y up, mirrored along Z), armature object included |
| Bone axes | One axis remap for all bones; by default the node keeps Blender's axes | Length and roll axes as in [How bones become nodes](#how-bones-become-nodes) |
| Parent used for the values | The bone's Blender parent | The parent as written in the output |
| Rotation | Single-precision `asin` | Double-precision `atan2`, exact near gimbal lock |
| Bounding box | Zero | From the weighted vertices |

On three sample characters, the 1.0.0 maths reproduces the vanilla joint positions for only part of the bones, while 2.0.0 matches them all. Since 2.2.0, the Coordinate Space option Armature Space = FS Space reads the armature's space as 1.0.0 did.

## Fix the SkeletonSet after Load JSON

A FLVER (version `0x2001A` and later) stores the bone hierarchy twice: in the node list and in the SkeletonSet. "Load JSON" replaces the node list only, so the SkeletonSet keeps describing the old node order. In a working FLVER, every SkeletonSet entry mirrors its node. In a FLVER whose SkeletonSet no longer matched its nodes, ERCharacterScale showed the model with vanilla proportions instead of retargeting it; rebuilding the SkeletonSet is the fix to test first.

Run the tool on the FLVER saved by FLVER Editor, after the last edit there:

```
python tools\fix_skeleton_set.py "path\to\model.flver"
```

It writes `model.skelfix.flver` next to the input (or to a second path, if given), with every SkeletonSet entry rebuilt from its node: parent, first child, next sibling, previous sibling, and the node's own index. When the SkeletonSet holds more entries than the FLVER has nodes (left over from a model with more bones), it is shrunk to the node count: the extra entries, which point at nodes that no longer exist, are zeroed. Nothing else in the file changes, the input is never overwritten, and an existing output file is not replaced. Rename the fixed copy to the original name when packing it into the game files.

The tool only needs Python 3. It refuses files it cannot fix safely: big-endian FLVERs, versions without a SkeletonSet, a SkeletonSet with fewer entries than nodes, and node lists with inconsistent links.

## How bones become nodes

A node (one entry of the JSON list) is SoulsFormats' `FLVER.Node`. Each Blender bone becomes one node.

**Position.** FS space (FLVER space) is the game's: Y up, the character faces -Z, and its left is +X. The Coordinate Space option sets how Blender coordinates become FS coordinates:

- **Blender World (Convert to FS)**, the default: the armature as it stands in Blender's world, Z up, including the armature object's transform and its parents. It is turned so that Y points up, then mirrored along Z: a point at Blender (x, y, z) lands at FS (x, z, y). This suits armatures that stand upright in Blender, such as those from the FLVER importer.
- **Armature Space = FS Space**: the armature's own coordinates are taken to be FS coordinates already and are written unchanged; the armature object's transform is ignored. Tlarok's script and FLVER Bones Adder read armatures this way. An armature imported from an FBX of a FLVER lies on its back in Blender, because its coordinates already are FS coordinates.

**Axes.** Blender always runs a bone along its own Y axis; vanilla FLVER bones run along their own X axis. The length and roll options set the conversion. For skeletons that came from FLVER Editor's FBX export, the defaults give the core bones (clavicles, upper arms, forearms, thighs, neck, fingers) their vanilla axes back, except where a Blender bone points at a different child than in the vanilla skeleton.

**Vanilla orientations.** The axes the options produce are written as they are. To give vanilla-named bones the vanilla skeleton's axes, use Match Vanilla Orientations on the armature before exporting (see [Vanilla orientations on the armature](#vanilla-orientations-on-the-armature)).

**Rotation.** Euler angles in radians, applied X, then Z, then Y, as SoulsFormats' `FLVER.Node.ComputeLocalTransform` expects. The angles are computed in double precision so that rotations close to gimbal lock stay exact.

**Order.** Nodes are listed depth first: each parent comes before its children, and the children of one parent keep Blender's order. ParentIndex, FirstChildIndex, NextSiblingIndex and PreviousSiblingIndex are computed from that order; root nodes link to each other as siblings, as in vanilla node lists.

**Bounding boxes.** A node's BoundingBoxMin and BoundingBoxMax enclose every vertex weighted to its bone (weight above zero), measured in the node's own axes. Only meshes with an Armature modifier that targets the armature count, and vertices are taken in their rest position. A node with no weighted vertices gets a zero box.

**Flags.** Every node gets 8 (Bone). Node 0 gets 12 (Mesh and Bone) while "Mark Root as Mesh Node" is on. In Merge mode, reference nodes keep their Flags and added bones get 8.

**File.** One compact line of UTF-8 JSON without a BOM, field names in `FLVER.Node` order, numbers rounded to single precision and whole numbers written without decimals, matching files exported by FLVER Editor. The file is first written to a temporary file in the same folder and then moved into place, so a failed export leaves an existing file untouched.

## Known limits

- A Blender file does not keep vanilla node axes. Bones other than the core ones (hair, cloth, physics and so on) get the axes the options produce, which can differ from vanilla by quarter or half turns.
- Scale is 1 unless the armature object itself is scaled; Blender rest bones have no scale.
- Bounding boxes ignore modifiers and shape keys; they use the mesh as stored.
- The DummyOwner flag (2) is never set on an exported bone; in Merge mode, reference nodes keep theirs.
- Merge keeps reference nodes with no bone in the armature as they are; delete them in the reference if they should go.
- Merge refuses to reparent a reference bone under an added bone (see [Merge into Reference JSON](#merge-into-reference-json)).

## Development

### Virtual environment

The development tools run in a Python 3.11 virtual environment managed by [uv](https://docs.astral.sh/uv/), the same minor version as Blender 4.5's Python. `pyproject.toml` lists what is wanted and `uv.lock` pins exactly what is installed; both are committed. The extension itself needs nothing beyond Blender.

Create or update `.venv` from the lock file (uv downloads Python 3.11 if needed):

```
uv sync
```

Run the tests that need no Blender (the pure logic in `tests/unit`, which imports `core.*` from `src`):

```
uv run pytest
```

### Tests in Blender

Run the full test suite inside Blender 4.5 (in the commands below, `blender.exe` stands for the path to your blender.exe). It includes `tests/unit`, and it switches Blender's interface to English for the run (preferences are not saved), because the tests check English messages:

```
"blender.exe" -b -P tests\run_tests.py
```

Compare the output with a vanilla node JSON saved next to a sample `.blend` under the same name:

```
"blender.exe" -b sample.blend -P tests\check_samples.py
```

For a JSON under another name, pass its path after `--`:

```
"blender.exe" -b sample.blend -P tests\check_samples.py -- "reference.json"
```

The check passes when names and parents match, joint positions match within 1e-4, and every box, turned into the vanilla node's axes, matches within 1e-4. It also lists which core bones get their vanilla axes.

It then checks Merge into Reference JSON: it drops the last 20 leaf nodes whose bones exist in Blender from the vanilla list and merges the armature back in. Every kept node must keep its vanilla values and parent, and every re-added node must come after the last node with Flags 8 or 10, with its joint position and box within 1e-4.
