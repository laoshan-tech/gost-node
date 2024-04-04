import asyncio
import logging
from collections import Counter

from exceptions.tyz import TYZApiException
from utils import consts
from utils.gost import (
    extract_key_from_dict_list,
    collect_key_from_dict_list,
    GOSTAuth,
    parse_gost_limits,
    RelayRuleLimit,
    gen_service_name,
    gen_limiter_name,
    parse_rule_info_from_service,
)
from .api import TYZApi, GOSTApi, PrometheusApi
from .gost import (
    fetch_all_config,
    add_ws_egress_service,
    add_ws_ingress_service,
    add_raw_redir_service,
    add_conn_limiter,
    add_speed_limiter,
    del_service,
    del_chain,
    calc_traffic_by_service,
)

logger = logging.getLogger(__name__)


async def add_or_update_limiters(gost_api: GOSTApi, service_name: str, limit: RelayRuleLimit):
    """
    Add or update limiters.
    :param gost_api: gost endpoint
    :param service_name:
    :param limit:
    :return:
    """
    if limit:
        add_speed_limit_ok = await add_speed_limiter(
            gost_api=gost_api, name=gen_limiter_name(service=service_name, _type="speed"), values=limit.speed_limits
        )
        add_conn_limit_ok = await add_conn_limiter(
            gost_api=gost_api, name=gen_limiter_name(service=service_name, _type="conn"), values=limit.conn_limits
        )
        if add_speed_limit_ok and add_conn_limit_ok:
            logger.info(f"create speed and conn limiter success")


async def sync_relay_rules(panel_api: TYZApi, gost_api: GOSTApi):
    """
    Sync relay rules.
    :param panel_api:
    :param gost_api:
    :return:
    """
    gost_cfg = await fetch_all_config(gost_api=gost_api)
    gost_service_map = extract_key_from_dict_list(_list=gost_cfg.get("services"), key="name")
    gost_chain_map = extract_key_from_dict_list(_list=gost_cfg.get("chains"), key="name")
    success, msg, result = await panel_api.fetch_relay_rules()
    if not success:
        raise TYZApiException(f"sync relay rules error: {msg}")

    tasks = []
    new_service_names = []
    rules = result.get("data", [])
    for r in rules:
        limit = parse_gost_limits(limit=r.get("limit", "{}"))
        rule_type = r.get("type")
        if rule_type == consts.RuleType.EGRESS.value:
            tasks.append(sync_egress_rule(panel_api=panel_api, rule=r, gost_api=gost_api, service_map=gost_service_map))
        elif rule_type == consts.RuleType.TUNNEL.value:
            tasks.append(
                sync_ingress_rule(
                    panel_api=panel_api,
                    rule=r,
                    gost_api=gost_api,
                    service_map=gost_service_map,
                    chain_map=gost_chain_map,
                    limit=limit,
                )
            )
        elif rule_type == consts.RuleType.RAW.value:
            tasks.append(
                sync_raw_redirect_rule(
                    panel_api=panel_api, rule=r, gost_api=gost_api, service_map=gost_service_map, limit=limit
                )
            )
        else:
            logger.warning(f"unsupported rule type of rule-{r.get('id')}: {r.get('type')}")

        new_service_names.append(
            gen_service_name(rule_id=r.get("id"), rule_type=r.get("type"), node_id=panel_api.node_id)
        )

    tasks.append(
        old_gost_service_cleanup(
            gost_api=gost_api,
            service_map=gost_service_map,
            chain_map=gost_chain_map,
            new_service_names=new_service_names,
        )
    )
    await asyncio.gather(*tasks)


async def sync_ingress_rule(
    panel_api: TYZApi, rule: dict, gost_api: GOSTApi, service_map: dict, chain_map: dict, limit: RelayRuleLimit = None
) -> bool:
    """
    Sync ingress rule.
    :param panel_api:
    :param rule:
    :param gost_api: gost endpoint
    :param service_map: gost service map
    :param chain_map: gost chain map
    :param limit:
    :return:
    """
    service_name = gen_service_name(
        rule_id=rule.get("id"), rule_type=rule.get("type"), node_id=rule.get("ingress_node")
    )
    await add_or_update_limiters(gost_api=gost_api, service_name=service_name, limit=limit)

    old_service = service_map.get(service_name)
    if old_service:
        old_port = old_service.get("addr", ":").split(":")[1]
        old_targets = collect_key_from_dict_list(_list=old_service.get("forwarder", {}).get("nodes", []), key="addr")
        old_relay_name = old_service.get("handler", {}).get("chain", "")
        old_relay_addr = chain_map.get(old_relay_name, {}).get("hops", [{}])[0].get("nodes", [{}])[0].get("addr")
        old_speed_limiter = old_service.get("limiter", "")
        old_conn_limiter = old_service.get("climiter", "")

        if (
            old_port == str(rule.get("listen_port"))
            and old_relay_addr == rule.get("tunnel", {}).get("addr", "")
            and old_targets == rule.get("targets").split("\n")
            and old_speed_limiter == gen_limiter_name(service=service_name, _type="speed")
            and old_conn_limiter == gen_limiter_name(service=service_name, _type="conn")
        ):
            logger.info(f"{service_name} already exists")
            return True

    logger.info(f"creating or updating service {service_name}")
    add_ok = await add_ws_ingress_service(
        gost_api=gost_api,
        name=service_name,
        addr=f":{rule.get('listen_port')}",
        relay=rule.get("tunnel", {}).get("addr", ""),
        targets=rule.get("targets").split("\n"),
        auth=GOSTAuth(username=rule.get("tunnel", {}).get("username"), password=rule.get("tunnel", {}).get("password")),
        limit=limit,
    )
    if add_ok:
        logger.info(f"ingress rule {service_name} added success")
        await panel_api.update_relay_rule_status(rule_id=rule.get("id"), rule_type=rule.get("type"), status=3)
        return True
    else:
        logger.error(f"ingress rule {service_name} add error")
        return False


async def sync_egress_rule(panel_api: TYZApi, rule: dict, gost_api: GOSTApi, service_map: dict) -> bool:
    """
    Sync egress rule.
    :param panel_api:
    :param rule:
    :param gost_api: gost api client
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

    add_ok = await add_ws_egress_service(
        gost_api=gost_api,
        name=service_name,
        addr=f":{rule.get('listen_port')}",
        auth=GOSTAuth(username=rule.get("tunnel", {}).get("username"), password=rule.get("tunnel", {}).get("password")),
    )
    if add_ok:
        logger.info(f"egress rule {service_name} added success")
        await panel_api.update_relay_rule_status(rule_id=rule.get("id"), rule_type=rule.get("type"), status=3)
        return True
    else:
        logger.error(f"egress rule {service_name} add error")
        return False


async def sync_raw_redirect_rule(
    panel_api: TYZApi, rule: dict, gost_api: GOSTApi, service_map: dict, limit: RelayRuleLimit = None
) -> bool:
    """
    Sync raw redirect rule.
    :param panel_api:
    :param rule:
    :param gost_api:
    :param service_map:
    :param limit:
    :return:
    """
    service_name = gen_service_name(rule.get("id"), rule_type=rule.get("type"), node_id=rule.get("ingress_node"))
    await add_or_update_limiters(gost_api=gost_api, service_name=service_name, limit=limit)

    old_service = service_map.get(service_name)
    if old_service:
        old_port = old_service.get("addr", ":").split(":")[1]
        old_targets = collect_key_from_dict_list(_list=old_service.get("forwarder", {}).get("nodes", []), key="addr")
        old_speed_limiter = old_service.get("limiter", "")
        old_conn_limiter = old_service.get("climiter", "")
        if (
            old_port == str(rule.get("listen_port"))
            and old_targets == rule.get("targets").split("\n")
            and old_speed_limiter == gen_limiter_name(service=service_name, _type="speed")
            and old_conn_limiter == gen_limiter_name(service=service_name, _type="conn")
        ):
            logger.info(f"{service_name} already exists")
            return True

    logger.info(f"creating or updating service {service_name}")
    add_ok = await add_raw_redir_service(
        gost_api=gost_api,
        name=service_name,
        addr=f":{rule.get('listen_port')}",
        targets=rule.get("targets").split("\n"),
        limit=limit,
    )
    if add_ok:
        logger.info(f"ingress rule {service_name} added success")
        await panel_api.update_relay_rule_status(rule_id=rule.get("id"), rule_type=rule.get("type"), status=3)
        return True
    else:
        logger.error(f"ingress rule {service_name} add error")
        return False


async def report_traffic_by_rules(panel_api: TYZApi, prom_api: PrometheusApi):
    """
    Report used traffic by rules.
    :param panel_api: panel api client
    :param prom_api: prometheus api client
    :return:
    """
    t1 = asyncio.create_task(calc_traffic_by_service(prom_api=prom_api, seconds=30, direction="input"))
    t2 = asyncio.create_task(calc_traffic_by_service(prom_api=prom_api, seconds=30, direction="output"))
    inputs = await t1
    outputs = await t2

    result = Counter(inputs) + Counter(outputs)
    traffic_data = {"raw": {}, "tunnel": {}, "egress": {}}
    for service_name in result:
        rule_id, rule_type, node_id = parse_rule_info_from_service(service=service_name)
        # Use MB
        traffic_data[rule_type.lower()][str(rule_id)] = int(result[service_name])

    logger.info(f"report traffic data: {result}")
    await panel_api.traffic_report(data=traffic_data)


async def old_gost_service_cleanup(gost_api: GOSTApi, service_map: dict, chain_map: dict, new_service_names: list):
    """
    Delete useless services and chains.
    :param gost_api:
    :param service_map: old services
    :param chain_map: old chains
    :param new_service_names:
    :return:
    """
    useless_services = [k for k, _ in service_map.items() if k not in new_service_names]
    new_chain_names = [f"{s}-chain" for s in new_service_names]
    useless_chains = [k for k, _ in chain_map.items() if k not in new_chain_names]
    del_service_tasks = [del_service(gost_api=gost_api, name=s) for s in useless_services]
    del_chain_tasks = [del_chain(gost_api=gost_api, name=c) for c in useless_chains]
    tasks = del_service_tasks + del_chain_tasks
    await asyncio.gather(*tasks)
    logger.info(f"del {len(useless_services)} services and {len(useless_chains)} chains success")
