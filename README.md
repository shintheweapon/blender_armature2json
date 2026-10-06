# FLVER Node Exporter

A Blender 4.5 extension that writes a FLVER node list (the "Nodes JSON" that FLVER_Editor loads) straight from
a Blender armature. A vanilla node JSON is not needed.

## Install

1. Zip the contents of the `src` folder, so that `blender_manifest.toml` sits at the top of the zip.
2. In Blender: Edit > Preferences > Get Extensions, open the menu at the top right, choose "Install from Disk"
   and pick the zip.

## Use

1. Select the armature (or keep it as the only armature in the scene).
2. Choose File > Export > FLVER Nodes JSON (.json), or use the "FLVER Nodes" tab in the 3D Viewport sidebar.
3. In FLVER_Editor, open the vanilla FLVER, press "Load JSON" and pick the exported file. Answer "Yes" when it
   asks to shift bone weights to the new bone indices.
4. Import the new meshes with "Import Model" (FBX). FLVER_Editor matches their vertex groups to nodes by name.
5. Open the "Dummy" window and check each dummy's parent and attach bone (see the warning below).

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
- the node index of any vanilla mesh that stays in the FLVER.

Point them at the right nodes again in FLVER_Editor after loading the JSON. Meshes imported from FBX afterwards
point at node 0, which is why "Mark Root as Mesh Node" is on by default.

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

Run the tests inside Blender 4.5:

```
"blender.exe" -b -P tests\run_tests.py
```

Compare the output with a vanilla node JSON saved next to a sample `.blend` under the same name:

```
"blender.exe" -b sample.blend -P tests\check_samples.py
```

The check passes when names and parents match, joint positions match within 1e-4, and every box, turned into
the vanilla node's axes, matches within 1e-4. It also lists which core bones get their vanilla axes.
