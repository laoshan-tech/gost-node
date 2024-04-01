import asyncio
import logging
from dataclasses import dataclass
from json import JSONDecodeError
from typing import Tuple, Optional
from urllib.parse import urljoin

import httpx

from exceptions.tyz import TYZApiException
from utils import consts
from utils.gost import extract_key_from_dict_list, collect_key_from_dict_list, GOSTAuth
from .gost import (
    fetch_all_config,
    add_ws_egress_service,
    add_ws_ingress_service,
    add_raw_redir_service,
    del_service,
    del_chain,
)

logger = logging.getLogger(__name__)


@dataclass
class PanelContext:
    endpoint: str
    node_id: int
    token: str
    rule_id: int = None
    rule_type: str = ""


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


async def report_rule_status(endpoint: str, node_id: int, token: str, rule_id: int, rule_type: str, status: int):
    await tyz_req(
        endpoint=endpoint,
        url=f"/api/relay-rule-sync/",
        method="PUT",
        data={"node_id": node_id, "token": token, "id": rule_id, "type": rule_type, "status": status},
    )


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
    gost_service_map = extract_key_from_dict_list(_list=gost_cfg.get("services"), key="name")
    gost_chain_map = extract_key_from_dict_list(_list=gost_cfg.get("chains"), key="name")
    success, msg, result = await tyz_req(
        endpoint=endpoint, url=f"/api/relay-rule-sync/", method="GET", params={"node_id": node_id, "token": token}
    )
    if success:
        tasks = []
        new_service_names = []
        rules = result.get("data", [])
        for r in rules:
            ctx = PanelContext(
                endpoint=endpoint, node_id=node_id, token=token, rule_id=r.get("id"), rule_type=r.get("type")
            )
            if ctx.rule_type == consts.RuleType.EGRESS.value:
                tasks.append(sync_egress_rule(rule=r, gost=gost, service_map=gost_service_map, ctx=ctx))
            elif ctx.rule_type == consts.RuleType.TUNNEL.value:
                tasks.append(
                    sync_ingress_rule(
                        rule=r, gost=gost, service_map=gost_service_map, chain_map=gost_chain_map, ctx=ctx
                    )
                )
            elif ctx.rule_type == consts.RuleType.RAW.value:
                tasks.append(sync_raw_redirect_rule(rule=r, gost=gost, service_map=gost_service_map, ctx=ctx))
            else:
                logger.warning(f"unsupported rule type of rule-{r.get('id')}: {r.get('type')}")

            new_service_names.append(gen_service_name(rule_id=r.get("id"), rule_type=r.get("type"), node_id=node_id))

        tasks.append(
            old_gost_service_cleanup(
                endpoint=gost,
                service_map=gost_service_map,
                chain_map=gost_chain_map,
                new_service_names=new_service_names,
            )
        )
        await asyncio.gather(*tasks)
    else:
        raise TYZApiException(f"sync relay rules error: {msg}")


async def sync_ingress_rule(rule: dict, gost: str, service_map: dict, chain_map: dict, ctx: PanelContext) -> bool:
    """
    Sync ingress rule.
    :param rule:
    :param gost: gost endpoint
    :param service_map: gost service map
    :param ctx:
    :return:
    """
    service_name = gen_service_name(
        rule_id=rule.get("id"), rule_type=rule.get("type"), node_id=rule.get("ingress_node")
    )
    old_service = service_map.get(service_name)
    if old_service:
        old_port = old_service.get("addr", ":").split(":")[1]
        old_targets = collect_key_from_dict_list(_list=old_service.get("forwarder", {}).get("nodes", []), key="addr")
        old_relay_name = old_service.get("handler", {}).get("chain", "")
        old_relay_addr = chain_map.get(old_relay_name, {}).get("hops", [{}])[0].get("nodes", [{}])[0].get("addr")

        if (
            old_port == str(rule.get("listen_port"))
            and old_relay_addr == rule.get("tunnel", {}).get("addr", "")
            and old_targets == rule.get("targets").split("\n")
        ):
            logger.info(f"{service_name} already exists")
            return True

    logger.info(f"creating or updating service {service_name}")
    add_ok = await add_ws_ingress_service(
        endpoint=gost,
        name=service_name,
        addr=f":{rule.get('listen_port')}",
        relay=rule.get("tunnel", {}).get("addr", ""),
        targets=rule.get("targets").split("\n"),
        auth=GOSTAuth(username=rule.get("tunnel", {}).get("username"), password=rule.get("tunnel", {}).get("password")),
    )
    if add_ok:
        logger.info(f"ingress rule {service_name} added success")
        await report_rule_status(
            endpoint=ctx.endpoint,
            node_id=ctx.node_id,
            token=ctx.token,
            rule_id=ctx.rule_id,
            rule_type=ctx.rule_type,
            status=3,
        )
        return True
    else:
        logger.error(f"ingress rule {service_name} add error")
        return False


async def sync_egress_rule(rule: dict, gost: str, service_map: dict, ctx: PanelContext) -> bool:
    """
    Sync egress rule.
    :param rule:
    :param gost: gost endpoint
    :param service_map: gost service map
    :param ctx: panel context
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

    add_ok = await add_ws_egress_service(
        endpoint=gost,
        name=service_name,
        addr=f":{rule.get('listen_port')}",
        auth=GOSTAuth(username=rule.get("tunnel", {}).get("username"), password=rule.get("tunnel", {}).get("password")),
    )
    if add_ok:
        logger.info(f"egress rule {service_name} added success")
        await report_rule_status(
            endpoint=ctx.endpoint,
            node_id=ctx.node_id,
            token=ctx.token,
            rule_id=ctx.rule_id,
            rule_type=ctx.rule_type,
            status=3,
        )
        return True
    else:
        logger.error(f"egress rule {service_name} add error")
        return False


async def sync_raw_redirect_rule(rule: dict, gost: str, service_map: dict, ctx: PanelContext) -> bool:
    """
    Sync raw redirect rule.
    :param rule:
    :param gost:
    :param service_map:
    :param ctx:
    :return:
    """
    service_name = gen_service_name(rule.get("id"), rule_type=rule.get("type"), node_id=rule.get("ingress_node"))
    old_service = service_map.get(service_name)
    if old_service:
        old_port = old_service.get("addr", ":").split(":")[1]
        old_targets = collect_key_from_dict_list(_list=old_service.get("forwarder", {}).get("nodes", []), key="addr")
        if old_port == str(rule.get("listen_port")) and old_targets == rule.get("targets").split("\n"):
            logger.info(f"{service_name} already exists")
            return True

    logger.info(f"creating or updating service {service_name}")
    add_ok = await add_raw_redir_service(
        endpoint=gost, name=service_name, addr=f":{rule.get('listen_port')}", targets=rule.get("targets").split("\n")
    )
    if add_ok:
        logger.info(f"ingress rule {service_name} added success")
        await report_rule_status(
            endpoint=ctx.endpoint,
            node_id=ctx.node_id,
            token=ctx.token,
            rule_id=ctx.rule_id,
            rule_type=ctx.rule_type,
            status=3,
        )
        return True
    else:
        logger.error(f"ingress rule {service_name} add error")
        return False


async def old_gost_service_cleanup(endpoint: str, service_map: dict, chain_map: dict, new_service_names: list):
    """
    Delete useless services and chains.
    :param endpoint:
    :param service_map: old services
    :param chain_map: old chains
    :param new_service_names:
    :return:
    """
    useless_services = [k for k, _ in service_map.items() if k not in new_service_names]
    new_chain_names = [f"{s}-chain" for s in new_service_names]
    useless_chains = [k for k, _ in chain_map.items() if k not in new_chain_names]
    del_service_tasks = [del_service(endpoint=endpoint, name=s) for s in useless_services]
    del_chain_tasks = [del_chain(endpoint=endpoint, name=c) for c in useless_chains]
    tasks = del_service_tasks + del_chain_tasks
    await asyncio.gather(*tasks)
    logger.info(f"del {len(useless_services)} services and {len(useless_chains)} chains success")
