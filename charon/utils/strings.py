def remove_prefix(string: str, prefix: str) -> str:
    if string and prefix and string.startswith(prefix):
        return string[len(prefix):]
    return string
