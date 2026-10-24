# Armature2JSON

A Blender 4.5 extension that writes a FLVER node JSON, the bone list that FLVER Editor's "Load JSON" reads, from a Blender armature. Two modes:

- **From Armature:** every node comes from the armature. No vanilla JSON is needed.
- **Merge into Reference JSON:** every node of a reference JSON (usually a vanilla one) is kept, and the armature's bones that it lacks are added.

The interface is in English and Simplified Chinese (简体中文), following Blender's language setting.

## Install

1. Download `armature2json-<version>.zip` from the [Releases page](https://github.com/shintheweapon/blender_armature2json/releases).
2. In Blender: Edit > Preferences > Get Extensions, open the menu at the top right, choose Install from Disk and pick the zip.

The zip replaces Armature2JSON 1.0.0. To build the zip yourself, see [Build from source](docs/DETAILS.md#build-from-source).

## Use

1. Select the armature.
2. Choose File > Export > FLVER Nodes JSON (.json), or use the Armature2JSON tab in the 3D Viewport sidebar. Pick the mode; for Merge into Reference JSON, also pick the reference JSON.
3. In FLVER Editor, open the FLVER, press Load JSON and pick the exported file.

## Options

Every option has a tooltip. FS space is the game's coordinate system: Y up, the character facing -Z.

| Option | What it does | Default |
|---|---|---|
| Mode | From Armature, or Merge into Reference JSON | From Armature |
| Reference JSON | Merge only: the JSON whose nodes are kept | empty |
| Reparented Bones | Merge only: the parent written for a reference bone that has another parent in Blender | Keep Reference Parent |
| Coordinate Space | Blender World (Convert to FS) for armatures standing upright in Blender; Armature Space = FS Space for armatures whose coordinates already are FS coordinates | Blender World (Convert to FS) |
| Length Axis, Roll Axis | Which node axes a bone's length and roll become. Reset Axes sets `X` / `-Z`; As Imported sets `Y` / `Z` | `X`, `-Z` |
| Vanilla Reference JSON | c0000's node JSON, for Match Vanilla Orientations | empty |
| Mark Root as Mesh Node | From Armature only: node 0 is also written as a mesh node | off |

## Custom physics skeleton

The game animates vanilla body bones in the axes of the vanilla skeleton (c0000), and a custom `Skeleton.hkx` takes its axes from the Blender armature. So match the axes on the armature itself before exporting:

1. Set Coordinate Space to Armature Space = FS Space and press As Imported.
2. Set Vanilla Reference JSON to c0000's Nodes.json (exported with FLVER Editor) and press Match Vanilla Orientations, with the armature in its rest pose.
3. Export the JSON.

## More

[docs/DETAILS.md](docs/DETAILS.md) covers vanilla orientations in full, what Load JSON leaves at old node numbers, how bones become nodes, Merge in detail, the differences from 1.0.0, known limits, the SkeletonSet tool, building from source and the tests.
