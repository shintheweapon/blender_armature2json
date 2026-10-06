# FLVER Node Exporter

A Blender 4.5 extension that writes a FLVER node list (the "Nodes JSON" that FLVER_Editor loads) straight from
a Blender armature. A vanilla node JSON is not needed.

Status: in development. The node list can be built and written from Python; the export menu follows.

## How bones become nodes

A node (one entry of the JSON list) is SoulsFormats' `FLVER.Node`. Each Blender bone becomes one node.

**Position.** FLVER space is Blender space turned so that Y points up, then mirrored along Z:
a point at Blender (x, y, z) lands at FLVER (x, z, y). The armature object's own transform is included.

**Axes.** Blender always runs a bone along its own Y axis. FLVER nodes in the vanilla skeletons run along their
own X axis. Two export options set the conversion:

| Option | Meaning | Default |
|---|---|---|
| Length axis | The node axis that runs along the bone | `X` |
| Roll axis | The node axis that the bone's Z axis becomes | `-Z` |

With the defaults, core vanilla bones (clavicles, upper arms, forearms, thighs, neck, fingers) keep their
vanilla axes when a vanilla skeleton is round tripped through Blender.

**Rotation.** Stored as Euler angles in radians, applied X, then Z, then Y, as SoulsFormats'
`FLVER.Node.ComputeLocalTransform` expects.

**Order.** Nodes are listed depth first: each parent comes before its children, and the children of one
parent keep Blender's order. ParentIndex, FirstChildIndex, NextSiblingIndex and PreviousSiblingIndex are
computed from that order; root nodes link to each other as siblings, as in vanilla node lists.

**Bounding boxes.** A node's BoundingBoxMin and BoundingBoxMax enclose every vertex weighted to its bone
(weight above zero), measured in the node's own axes. Only meshes with an Armature modifier that targets the
armature count, and vertices are taken in their rest position. A node with no weighted vertices gets a zero box.

**Flags.** Every node gets 8 (Bone). Node 0 gets 12 (Mesh and Bone) while "Mark root as mesh node" is on,
which is the default: FLVER_Editor points every mesh it imports from FBX at node 0.

**File.** One compact line of UTF-8 JSON without a BOM, field names in `FLVER.Node` order, numbers rounded to
single precision and whole numbers written without decimals, matching files exported by FLVER_Editor.

## Development

Run the tests inside Blender 4.5:

```
"blender.exe" -b -P tests\run_tests.py
```
