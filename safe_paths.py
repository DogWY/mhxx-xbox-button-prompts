"""Validate local build paths and portable ARC member names."""
from pathlib import Path, PureWindowsPath

try:
    from ntpath import isreserved
except ImportError:  # Python before 3.13
    def isreserved(component):
        return PureWindowsPath(component).is_reserved()


def relative_name(name):
    """Return a portable slash-delimited file name, rejecting ambiguous components."""
    name = str(name).replace('\\', '/')
    for component in name.split('/'):
        if (not component or component in ('.', '..') or component.endswith(('.', ' '))
                or any(ord(c) < 32 or c in '<>:"|?*' for c in component)
                or isreserved(component)):
            raise ValueError(f'Invalid relative file name: {name!r}')
    return name


def archive_name(raw_name):
    """Read a UTF-8 name from an ARC directory record's 64-byte field."""
    name, _, padding = raw_name.partition(b'\0')
    if any(padding):
        raise ValueError('Unexpected data after ARC member name')
    return relative_name(name.decode('utf-8'))


def within(root, relative):
    """Resolve a relative path and require its real location to stay inside root."""
    root = Path(root).resolve()
    target = (root / relative_name(relative)).resolve()
    if root not in target.parents:
        raise ValueError(f'Path escapes {root}: {relative!r}')
    return target


def require_disjoint(first, second):
    first, second = Path(first).resolve(), Path(second).resolve()
    if first == second or first in second.parents or second in first.parents:
        raise ValueError(f'Input and output directories overlap: {first}, {second}')
