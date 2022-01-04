def remove_prefix(string: str, prefix: str) -> str:
    if string and prefix and string.startswith(prefix):
        return string[len(prefix):]
    return string


def trail_path_with_root(path: str, root: str) -> str:
    slash_root = root
    if not slash_root.endswith("/"):
        slash_root = slash_root + "/"
    return remove_prefix(path, slash_root)
