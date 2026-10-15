# Simplified Chinese (zh_HANS) translations of the add-on's texts; plain Python.
# Keys are (context, English text) as bpy.app.translations expects; the
# English texts must match the code exactly (tests check this).

from typing import Dict, Tuple

from . import messages

# Contexts used by Blender: '*' for most texts, 'Operator' for operator labels
DEFAULT = '*'
OPERATOR = 'Operator'

# Node axes offered by the Length Axis and Roll Axis options
_AXES = ('X', 'Y', 'Z', '-X', '-Y', '-Z')

_INTERFACE = {
    # Sidebar panel
    "No armature in the scene": "场景里没有骨架",
    "Armature: {name}": "骨架：{name}",
    # Mode
    "Mode": "模式",
    "How to build the node list": "节点列表的生成方式",
    "From Armature": "仅用骨架生成",
    "Build every node from the armature. No reference JSON is needed":
        "所有节点都由骨架生成，不需要参考 JSON",
    "Merge into Reference JSON": "合并到参考 JSON",
    "Keep every node of a reference JSON (for example a vanilla one from FLVER_Editor) "
    "and add the armature's bones that it lacks":
        "保留参考 JSON（如 FLVER_Editor 导出的原版 JSON）中的所有节点，只补上其中缺少的骨骼",
    # Reference JSON
    "Reference JSON": "参考 JSON",
    "The node JSON used as the reference, usually a vanilla one exported by FLVER_Editor. "
    "Its nodes are kept as they are":
        "作为参考的节点 JSON，一般是 FLVER_Editor 导出的原版 JSON。其中的节点会原样保留",
    # Reparented Bones
    "Reparented Bones": "父级有变动的骨骼",
    "What to do with bones that are in the reference JSON but have a different parent in "
    "Blender (the bone's parent in Blender is not the parent recorded in the reference JSON)":
        "参考 JSON 中已有、但在 Blender 中父级不同的骨骼（即该骨骼在 Blender 中的父级，"
        "与参考 JSON 中记录的父级不一致）的处理方式",
    "Keep Reference Parent": "沿用原父级",
    "Keep the reference JSON's parent and values. The bone stays where it was":
        "沿用参考 JSON 中的父级和数值，骨骼位置不变",
    "Use Blender Parent, Keep Placement": "改用 Blender 父级，位置不变",
    "Use the Blender parent and recompute the bone's values, so it stays where it was, "
    "axes included":
        "改用 Blender 中的父级，并重新计算骨骼数值，位置和朝向都保持不变",
    "Use Blender Parent, Keep Values (1.0.0)":
        "改用 Blender 父级，数值不变（1.0.0 的做法）",
    "Use the Blender parent but keep the values relative to the old parent, as "
    "Armature2JSON 1.0.0 did. The bone can move":
        "改用 Blender 中的父级，但数值仍按原父级计算，与 Armature2JSON 1.0.0 相同。骨骼可能会错位",
    # Axes
    "Length Axis": "长度轴",
    "Node axis that runs along each bone. Vanilla skeletons use the X axis":
        "骨骼长度方向对应的节点轴。原版骨架用 X 轴",
    "Roll Axis": "扭转轴",
    "Node axis that each bone's Z axis becomes. -Z gives core vanilla bones their vanilla axes":
        "骨骼 Z 轴对应的节点轴。选 -Z 时，原版核心骨骼的轴向与原版一致",
    # Root flag
    "Mark Root as Mesh Node": "根节点同时标记为网格",
    "Write node 0 with Flags 12 (Mesh and Bone) instead of 8 (Bone). "
    "FLVER_Editor points every mesh it imports from FBX at node 0":
        "节点 0 的 Flags 写为 12（网格 + 骨骼），而不是 8（骨骼）。"
        "FLVER_Editor 从 FBX 导入的网格都会关联到节点 0",
    # Vanilla orientations
    "Vanilla Bone Orientations": "原版骨骼朝向",
    "Give bones with Elden Ring bone names their vanilla orientation, keeping "
    "their positions. Without ERCS, the game turns the mesh around any bone "
    "whose orientation differs from vanilla":
        "名称与艾尔登法环骨骼相同的骨骼使用原版朝向，位置保持不变。"
        "不使用 ERCS 时，游戏会让网格绕朝向与原版不同的骨骼扭转",
}
_INTERFACE.update({f"Node {axis} axis": f"节点 {axis} 轴" for axis in _AXES})

# Operator label, tooltip and File > Export entry: registered in both contexts
_OPERATOR = {
    "Export FLVER Nodes JSON": "导出 FLVER 节点 JSON",
    "Export the armature's bones as a FLVER node JSON for FLVER_Editor":
        "把骨架中的骨骼导出为 FLVER_Editor 可读取的节点 JSON",
    "FLVER Nodes JSON (.json)": "FLVER 节点 JSON (.json)",
}

_MESSAGES = {
    messages.NO_ARMATURE: "请先选中要导出的骨架。",
    messages.NO_BONES: "骨架“{name}”里没有骨骼。",
    messages.NOT_A_LIST: "参考 JSON 应为节点列表，即 FLVER_Editor 导出的格式。",
    messages.NOT_AN_OBJECT: "编号 {index} 的节点不是有效的对象。",
    messages.MISSING_FIELDS: "编号 {index} 的节点缺少字段：{fields}。",
    messages.NO_NAME: "编号 {index} 的节点没有名称。",
    messages.DUPLICATE_NAME: "参考 JSON 中有两个节点都叫“{name}”。",
    messages.BAD_PARENT_INDEX: "节点“{name}”的父级编号 {parent} 无效，没有对应的其他节点。",
    messages.PARENT_AFTER_CHILD:
        "节点“{name}”会排在它的父级“{parent}”前面。新增骨骼排在原有骨骼之后，"
        "所以不能把原有骨骼的父级设为新增骨骼。请选择“沿用原父级”，"
        "或在 Blender 中把它的父级改回原来的骨骼。",
    messages.UNKNOWN_REPARENT: "未知的父级处理方式“{choice}”，可选：{choices}。",
    messages.UNKNOWN_AXIS: "未知的轴“{name}”，可选：{axes}。",
    messages.SAME_LINE_AXES: "长度轴“{length}”和扭转轴“{roll}”不能在同一条直线上。",
    messages.PARENTS_FIRST: "编号 {index} 的节点的父级是 {parent}，但父级必须排在它前面。",
    messages.EXPORTED: "已从骨架“{armature}”导出 {count} 个节点到 {path}",
    messages.MERGED:
        "已把骨架“{armature}”中的 {added} 根骨骼合并进 {inputs} 个参考节点"
        "（从编号 {insertion} 处插入），共 {count} 个节点，写入 {path}",
    messages.REFERENCE_ONLY: "{count} 个参考节点在骨架中没有对应骨骼，已原样保留：{names}",
    messages.REPARENTED: "{count} 根骨骼在 Blender 中换了父级：{names}",
    messages.MORE_IN_CONSOLE: "……（完整列表见系统控制台）",
    messages.CHOOSE_REFERENCE: "请先选择要合并的参考 JSON。",
    messages.WOULD_OVERWRITE: "输出文件就是参考 JSON，会被覆盖。请换一个文件名。",
    messages.CANNOT_READ: "无法读取参考 JSON：{error}",
    messages.NOT_JSON: "参考 JSON 格式有误，无法解析：{error}",
    messages.CANNOT_WRITE: "无法写入文件：{error}",
}


def table() -> Dict[Tuple[str, str], str]:
    """
    Build the zh_HANS table in the form ``bpy.app.translations`` expects.

    Returns
    -------
    dict
        ``{(context, English text): Chinese text}``. Operator texts appear
        under both the default and the ``Operator`` context.
    """
    entries = {(DEFAULT, en): zh for en, zh in {**_INTERFACE, **_MESSAGES}.items()}
    for en, zh in _OPERATOR.items():
        entries[(DEFAULT, en)] = zh
        entries[(OPERATOR, en)] = zh
    return entries
