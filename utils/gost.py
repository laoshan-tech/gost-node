from dataclasses import dataclass


@dataclass
class GOSTAuth:
    username: str
    password: str


def extract_key_from_dict_list(_list: list, key: str) -> dict:
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


def collect_key_from_dict_list(_list: list, key: str) -> list:
    """

    :param _list:
    :param key:
    :return:
    """
    if not _list:
        return []

    res = [d.get(key) for d in _list]
    return res
