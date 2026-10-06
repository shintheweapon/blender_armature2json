# FLVER Node Exporter

A Blender 4.5 extension that writes a FLVER node list (the "Nodes JSON" that FLVER_Editor loads) straight from
a Blender armature. A vanilla node JSON is not needed.

Status: in development. The coordinate conversion is done; hierarchy, bounding boxes, file output and the
export menu follow.

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

## Development

Run the tests inside Blender 4.5:

```
"blender.exe" -b -P tests\run_tests.py
```
