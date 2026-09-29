from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def file_exist(path: str) -> bool:
    """Return whether a regular file exists at a project-relative path."""
    relative_path = Path(path)
    if relative_path.is_absolute():
        return False

    file_path = (PROJECT_ROOT / relative_path).resolve()
    if not file_path.is_relative_to(PROJECT_ROOT):
        return False
    return file_path.is_file()
