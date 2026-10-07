"""Keep a bounded display name without removing the uploaded file's extension."""
from pathlib import PurePath


def upload_filename(filename: str | None, max_length: int = 200) -> str:
    name = PurePath((filename or '').replace('\\', '/')).name
    if len(name) <= max_length:
        return name
    suffix = PurePath(name).suffix
    if len(suffix) >= max_length:
        return name[:max_length]
    return name[:max_length - len(suffix)] + suffix
