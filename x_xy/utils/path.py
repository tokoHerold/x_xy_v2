import os
from pathlib import Path
from typing import Optional
import warnings


def parse_path(
    path: str,
    *join_paths: str,
    extension: Optional[str] = None,
    file_exists_ok: bool = True,
    mkdir: bool = True,
) -> str:
    path = Path(os.path.expanduser(path))

    for p in join_paths:
        path = path.joinpath(p)

    if extension is not None:
        if extension != "":
            extension = ("." + extension) if (extension[0] != ".") else extension

        # check for paths that contain a dot "." in their filename (through a number)
        # or that already have an extension
        old_suffix = path.suffix
        if old_suffix != "" and old_suffix != extension:
            warnings.warn(
                f"The path ({path}) already has an extension (`{old_suffix}`), but "
                f"it gets replaced by the extension=`{extension}`."
            )

        path = path.with_suffix(extension)

    if not file_exists_ok and os.path.exists(path):
        raise Exception(f"File {path} already exists but shouldn't")

    if mkdir:
        path.parent.mkdir(parents=True, exist_ok=True)

    return str(path)
