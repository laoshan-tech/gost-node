def json_key_extract(_list: list, key: str):
    """
    Extract specific key from a list of dict.
    :param _list:
    :param key:
    :return:
    """
    if not _list:
        return {}

    res = {d.get(key): d for d in _list}
    return res
