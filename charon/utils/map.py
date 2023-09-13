def del_none(d):
    for key, value in list(d.items()):
        if value is None:
            del d[key]
        elif isinstance(value, dict):
            del_none(value)
    return d


def replace_field(d, field, new_field):
    if d[field]:
        d[new_field] = d[field]
        del d[field]
    return d
