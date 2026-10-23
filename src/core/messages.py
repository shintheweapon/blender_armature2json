# Every report and error text of the exporter, as templates with named
# fields; plain Python. The templates are also the keys of the translations.

# Errors raised by the core modules
NO_ARMATURE = "Select an armature object to export."
NO_BONES = "Armature '{name}' has no bones."
NOT_A_LIST = "The reference JSON must be a list of nodes, as FLVER_Editor exports."
NOT_AN_OBJECT = "Reference node {index} is not an object."
MISSING_FIELDS = "Reference node {index} lacks {fields}."
NO_NAME = "Reference node {index} has no name."
DUPLICATE_NAME = "The reference JSON has two nodes named '{name}'."
BAD_PARENT_INDEX = ("Reference node '{name}' has parent index {parent}, "
                    "which points at no other node.")
PARENT_AFTER_CHILD = (
    "Node '{name}' would come before its parent '{parent}'. An existing bone cannot be "
    "reparented under a bone the reference lacks, because added bones go after the "
    "reference's bones. Choose 'Keep Reference Parent' or move the bone back.")
UNKNOWN_REPARENT = "Unknown reparent choice '{choice}'. Expected one of {choices}."
UNKNOWN_AXIS = "Unknown axis '{name}'. Expected one of {axes}."
UNKNOWN_SPACE = "Unknown coordinate space '{name}'. Expected one of {spaces}."
SAME_LINE_AXES = "Length axis '{length}' and roll axis '{roll}' must be different lines."
PARENTS_FIRST = "Node {index} has parent {parent}; parents must come first."

# Reports of the export operator
EXPORTED = "Exported {count} nodes from '{armature}' to {path}"
MERGED = ("Merged {added} bones from '{armature}' into {inputs} reference nodes "
          "(inserted at node {insertion}); wrote {count} nodes to {path}")
REFERENCE_ONLY = ("{count} reference nodes have no bone in the armature, "
                  "kept as they are: {names}")
REPARENTED = "{count} bones have another parent in Blender: {names}"
MORE_IN_CONSOLE = ", ... (full list in the system console)"
CHOOSE_REFERENCE = "Choose a reference JSON to merge into."
WOULD_OVERWRITE = "The output would overwrite the reference JSON. Choose another file name."
CANNOT_READ = "Could not read the reference JSON: {error}"
NOT_JSON = "The reference JSON is not valid JSON: {error}"
CANNOT_WRITE = "Could not write the file: {error}"


def templates() -> dict:
    """
    List every message template of this module.

    Returns
    -------
    dict
        Constant name to template, for every upper-case string constant.
    """
    return {name: value for name, value in globals().items()
            if name.isupper() and isinstance(value, str)}


class ExportError(ValueError):
    """
    An export error that keeps its message template and fields.

    ``str(error)`` is the English message. The template and fields let the
    add-on show the message in the interface language instead.

    Parameters
    ----------
    template : str
        One of the templates in this module.
    **fields
        Values for the template's named fields.
    """

    def __init__(self, template: str, **fields):
        super().__init__(template.format(**fields))
        self.template = template
        self.fields = fields
