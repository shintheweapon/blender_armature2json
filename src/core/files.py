# File safety helpers: same-file detection and atomic writes; plain Python

import os
import tempfile


def same_file(a: str, b: str) -> bool:
    """
    Tell whether two paths name the same file.

    When both exist, the file system decides, so hard links, links and a
    different letter case on Windows all count as the same file. Otherwise
    the resolved, case-normalised paths are compared.

    Parameters
    ----------
    a, b : str
        File paths, relative or absolute.

    Returns
    -------
    bool
        True when writing to one would change the other.
    """
    if os.path.exists(a) and os.path.exists(b):
        return os.path.samefile(a, b)
    return os.path.normcase(os.path.realpath(a)) == os.path.normcase(os.path.realpath(b))


def write_text_atomic(path: str, text: str) -> None:
    """
    Write text to a file so that a failure never leaves it half-written.

    The text goes to a temporary file in the same folder, which is flushed to
    disk and then moved onto ``path`` in one step. If anything fails, the
    temporary file is removed and an existing file at ``path`` is untouched.

    Parameters
    ----------
    path : str
        Target file path.
    text : str
        Text to write, as UTF-8 without BOM and without newline translation.

    Raises
    ------
    OSError
        If the file cannot be written or moved into place, for example when
        another program holds the target open.
    """
    folder = os.path.dirname(os.path.abspath(path))
    handle = tempfile.NamedTemporaryFile(
        mode='w', encoding='utf-8', newline='', dir=folder,
        prefix=os.path.basename(path) + '.', suffix='.tmp', delete=False)
    try:
        with handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(handle.name, path)
    except BaseException:
        try:
            os.remove(handle.name)
        except OSError:
            pass
        raise
