import json
import logging
import math
from dataclasses import dataclass, field
from json import JSONDecodeError
from typing import List, Tuple

logger = logging.getLogger(__name__)


@dataclass
class GOSTAuth:
    username: str
    password: str


@dataclass
class RelayRuleLimit:
    speed_limits: List[str] = field(default_factory=list)
    conn_limits: List[str] = field(default_factory=list)


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


def safe_json_loads(s: str) -> dict:
    """
    Load json string safely.
    :param s:
    :return:
    """
    try:
        return json.loads(s)
    except JSONDecodeError:
        logger.error(f"json load error: {s}")
        return {}


def parse_gost_limits(limit: str) -> RelayRuleLimit:
    """
    Parse gost limits from JSON string.
    :param limit:
    :return:
    """
    origin_limit = safe_json_loads(limit)
    rule_limit = RelayRuleLimit()
    speed_limit = math.ceil(origin_limit.get("speed", 0) / 8)
    conn_limit = origin_limit.get("conn", 0)
    if speed_limit > 0:
        rule_limit.speed_limits = [f"$ {speed_limit}MB {speed_limit}MB"]
    if conn_limit > 0:
        rule_limit.conn_limits = [f"$ {conn_limit}"]

    return rule_limit


def gen_service_name(rule_id: int, rule_type: str, node_id: int) -> str:
    """
    Generate service name.
    :return:
    """
    return f"rule-{rule_id}-{rule_type.lower()}-node-{node_id}"


def gen_limiter_name(service: str, _type: str) -> str:
    """
    Generate limiter name.
    :param service:
    :param _type:
    :return:
    """
    return f"{service}-{_type}-limiter"


def parse_rule_info_from_service(service: str) -> Tuple[int, str, int]:
    """
    Parse rule id, rule type, node id from service name.
    :param service:
    :return:
    """
    data = service.split("-")
    rule_id = int(data[1])
    rule_type = data[2]
    node_id = int(data[4])
    return rule_id, rule_type, node_id
