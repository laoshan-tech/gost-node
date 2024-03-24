import logging
from json import JSONDecodeError
from typing import Tuple, Optional
from urllib.parse import urljoin

import httpx

from exceptions.tyz import TYZApiException
from utils import consts
from utils.gost import json_key_extract
from .gost import fetch_all_config, add_ws_egress_service

logger = logging.getLogger(__name__)


def gen_service_name(rule_id: int, rule_type: str, node_id: int) -> str:
    """
    Generate service name.
    :return:
    """
    return f"rule-{rule_id}-{rule_type.lower()}-node-{node_id}"


async def tyz_req(
    endpoint: str, url: str, method: str, params: dict = None, data: dict = None
) -> Tuple[bool, str, Optional[dict]]:
    """
    GOST API request.
    :param endpoint: gost api addr
    :param url:
    :param method: get/post/put/delete/etc
    :param params: get params
    :param data: json post data
    :return:
    """
    async with httpx.AsyncClient() as client:
        try:
            if method.upper() == "GET":
                response = await client.get(urljoin(endpoint, url), params=params)
            elif method.upper() in ("POST", "PUT", "DELETE"):
                response = await client.request(method=method, url=urljoin(endpoint, url), json=data)
            else:
                raise TYZApiException(f"unsupported method: {method}")

            result = response.json()
        except JSONDecodeError:
            logger.error(f"json decode error:\n{response.text}")
            return False, "json decode error", None
        except Exception as e:
            logger.error(f"gost req error: {e}")
            return False, "req error", None

        msg = result.get("msg", "")
        return response.status_code == 200, msg, result


async def sync_relay_rules(endpoint: str, node_id: int, token: str, gost: str):
    """
    Sync relay rules.
    :param endpoint:
    :param node_id:
    :param token:
    :param gost: gost endpoint
    :return:
    """
    gost_cfg = await fetch_all_config(endpoint=gost)
    gost_service_map = json_key_extract(_list=gost_cfg.get("services"), key="name")
    success, msg, result = await tyz_req(
        endpoint=endpoint, url=f"/api/relay-rule-sync/", method="GET", params={"node_id": node_id, "token": token}
    )
    if success:
        rules = result.get("data", [])
        for r in rules:
            if r.get("type") == consts.RuleType.EGRESS.value:
                await sync_egress_rule(rule=r, gost=gost, service_map=gost_service_map)
    else:
        raise TYZApiException(f"sync relay rules error: {msg}")


async def sync_egress_rule(rule: dict, gost: str, service_map: dict) -> bool:
    """
    Sync egress rule.
    :param rule:
    :param gost: gost endpoint
    :param service_map: gost service map
    :return:
    """
    service_name = gen_service_name(rule.get("id"), rule_type=rule.get("type"), node_id=rule.get("egress_node"))
    old_service = service_map.get(service_name)
    if old_service:
        old_port = old_service.get("addr", ":").split(":")[1]
        old_transport_type = old_service.get("listener", {}).get("type", "")
        new_transport_type = "ws" if rule.get("transport_type", "") == "WebSocket" else "unknown"
        if old_port == str(rule.get("listen_port")) and old_transport_type == new_transport_type:
            logger.info(f"{service_name} already exists")
            return True

    logger.info(f"creating or updating service {service_name}")
    add_ok = await add_ws_egress_service(endpoint=gost, name=service_name, addr=f":{rule.get('listen_port')}")
    if add_ok:
        logger.info(f"{service_name} added success")
        return True
    else:
        logger.error(f"{service_name} add error")
        return False
