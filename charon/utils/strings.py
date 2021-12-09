def remove_prefix(string: str, prefix: str) -> str:
    if string and prefix and string.startswith(prefix):
        return string[len(prefix):]
    return string

def remove_sufix(string: str, sufix: str) -> str:
    if string and sufix and string.endswith(sufix):
        return string[:-len(sufix)]
    return string
