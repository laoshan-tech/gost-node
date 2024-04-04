import logging
from typing import List

from exceptions.gost import GOSTApiException
from services.api import GOSTApi, PrometheusApi
from utils.gost import GOSTAuth, RelayRuleLimit

logger = logging.getLogger(__name__)


async def fetch_all_config(gost_api: GOSTApi) -> dict:
    success, msg, result = await gost_api.request(url="/config", method="get")
    if success:
        return result
    else:
        raise GOSTApiException(f"fetch all config error: {msg}")


async def del_service(gost_api: GOSTApi, name: str):
    """
    Delete service.
    :param gost_api:
    :param name:
    :return:
    """
    await gost_api.request(url=f"/config/services/{name}", method="DELETE")


async def del_chain(gost_api: GOSTApi, name: str):
    """
    Delete chain.
    :param gost_api:
    :param name:
    :return:
    """
    await gost_api.request(url=f"/config/chains/{name}", method="DELETE")


async def update_ws_chain(gost_api: GOSTApi, name: str, relay: str, auth: GOSTAuth) -> bool:
    data = {
        "hops": [
            {
                "name": f"{name}-hop",
                "nodes": [
                    {
                        "name": f"{name}-relay-node",
                        "addr": relay,
                        "connector": {"type": "relay", "auth": {"username": auth.username, "password": auth.password}},
                        "dialer": {"type": "ws"},
                    }
                ],
            }
        ],
    }
    success, msg, result = await gost_api.request(url=f"/config/chains/{name}", method="put", data=data)
    if success and msg == "OK":
        return True
    else:
        logger.error(f"update ws chain error: {msg}")
        return False


async def add_ws_chain(gost_api: GOSTApi, name: str, relay: str, auth: GOSTAuth) -> bool:
    data = {
        "name": name,
        "hops": [
            {
                "name": f"{name}-hop",
                "nodes": [
                    {
                        "name": f"{name}-relay-node",
                        "addr": relay,
                        "connector": {"type": "relay", "auth": {"username": auth.username, "password": auth.password}},
                        "dialer": {"type": "ws"},
                    }
                ],
            }
        ],
    }
    success, msg, result = await gost_api.request(url="/config/chains", method="post", data=data)
    if success and msg == "OK":
        return True
    elif msg == "object duplicated":
        return await update_ws_chain(gost_api=gost_api, name=name, relay=relay, auth=auth)
    else:
        logger.error(f"add ws chain error: {msg}")
        return False


async def update_ws_ingress_service(
    gost_api: GOSTApi, name: str, addr: str, targets: List[str], limit: RelayRuleLimit = None
) -> bool:
    chain_name = f"{name}-chain"
    data = {
        "addr": addr,
        "handler": {"type": "tcp", "chain": chain_name},
        "listener": {"type": "tcp"},
        "forwarder": {
            "nodes": [{"name": f"{name}-target-{index}", "addr": target}] for index, target in enumerate(targets)
        },
        "observer": "node-observer",
    }
    if limit:
        speed_limiter_name = f"{name}-speed-limiter"
        conn_limiter_name = f"{name}-conn-limiter"
        data["limiter"] = speed_limiter_name
        data["climiter"] = conn_limiter_name

    success, msg, result = await gost_api.request(url=f"/config/services/{name}", method="put", data=data)
    if success and msg == "OK":
        return True
    else:
        logger.error(f"update ws ingress service error: {msg}")
        return False


async def add_ws_ingress_service(
    gost_api: GOSTApi,
    name: str,
    addr: str,
    relay: str,
    targets: List[str],
    auth: GOSTAuth,
    limit: RelayRuleLimit = None,
):
    """

    :param gost_api: gost endpoint
    :param name: service name
    :param addr: listen address
    :param relay: relay address
    :param targets: relay targets
    :param auth:
    :param limit:
    :return:
    """
    chain_name = f"{name}-chain"
    await add_ws_chain(gost_api=gost_api, name=chain_name, relay=relay, auth=auth)
    data = {
        "name": name,
        "addr": addr,
        "handler": {"type": "tcp", "chain": chain_name},
        "listener": {"type": "tcp"},
        "forwarder": {
            "nodes": [{"name": f"{name}-target-{index}", "addr": target}] for index, target in enumerate(targets)
        },
        "observer": "node-observer",
    }

    if limit:
        speed_limiter_name = f"{name}-speed-limiter"
        conn_limiter_name = f"{name}-conn-limiter"
        data["limiter"] = speed_limiter_name
        data["climiter"] = conn_limiter_name

    success, msg, result = await gost_api.request(url="/config/services", method="post", data=data)
    if success and msg == "OK":
        return True
    elif "object duplicated" == msg:
        return await update_ws_ingress_service(gost_api=gost_api, name=name, addr=addr, targets=targets)
    else:
        logger.error(f"add ws ingress service error: {msg}")
        return False


async def update_ws_egress_service(gost_api: GOSTApi, name: str, addr: str, auth: GOSTAuth) -> bool:
    data = {
        "addr": addr,
        "handler": {"type": "relay", "auth": {"username": auth.username, "password": auth.password}},
        "listener": {"type": "ws"},
        "observer": "node-observer",
    }
    success, msg, result = await gost_api.request(url=f"/config/services/{name}", method="put", data=data)
    if success and msg == "OK":
        return True
    else:
        logger.error(f"update ws egress service error: {msg}")
        return False


async def add_ws_egress_service(gost_api: GOSTApi, name: str, addr: str, auth: GOSTAuth) -> bool:
    data = {
        "name": name,
        "addr": addr,
        "handler": {"type": "relay", "auth": {"username": auth.username, "password": auth.password}},
        "listener": {"type": "ws"},
        "observer": "node-observer",
    }
    success, msg, result = await gost_api.request(url="/config/services", method="post", data=data)
    if success and msg == "OK":
        return True
    elif "object duplicated" == msg:
        return await update_ws_egress_service(gost_api=gost_api, name=name, addr=addr, auth=auth)
    else:
        logger.error(f"add ws egress service error: {msg}")
        return False


async def update_raw_redir_service(
    gost_api: GOSTApi, name: str, addr: str, targets: List[str], limit: RelayRuleLimit = None
) -> bool:
    data = {
        "addr": addr,
        "handler": {"type": "tcp"},
        "listener": {"type": "tcp"},
        "forwarder": {"nodes": [{"name": f"{name}-node-{index}", "addr": t} for index, t in enumerate(targets)]},
    }
    if limit:
        speed_limiter_name = f"{name}-speed-limiter"
        conn_limiter_name = f"{name}-conn-limiter"
        data["limiter"] = speed_limiter_name
        data["climiter"] = conn_limiter_name
    success, msg, result = await gost_api.request(url=f"/config/services/{name}", method="put", data=data)
    if success and msg == "OK":
        return True
    else:
        logger.error(f"update raw redirect service error: {msg}")
        return False


async def add_raw_redir_service(
    gost_api: GOSTApi, name: str, addr: str, targets: List[str], limit: RelayRuleLimit = None
) -> bool:
    data = {
        "name": name,
        "addr": addr,
        "handler": {"type": "tcp"},
        "listener": {"type": "tcp"},
        "forwarder": {"nodes": [{"name": f"{name}-node-{index}", "addr": t} for index, t in enumerate(targets)]},
    }

    if limit:
        speed_limiter_name = f"{name}-speed-limiter"
        conn_limiter_name = f"{name}-conn-limiter"
        data["limiter"] = speed_limiter_name
        data["climiter"] = conn_limiter_name

    success, msg, result = await gost_api.request(url="/config/services", method="post", data=data)
    if success and msg == "OK":
        return True
    elif msg == "object duplicated":
        return await update_raw_redir_service(gost_api=gost_api, name=name, addr=addr, targets=targets, limit=limit)
    else:
        logger.error(f"add raw redirect service error: {msg}")
        return False


async def update_speed_limiter(gost_api: GOSTApi, name: str, values: List = None) -> bool:
    data = {"limits": values}
    success, msg, result = await gost_api.request(url=f"/config/limiters/{name}", method="put", data=data)
    if success and msg == "OK":
        return True
    else:
        logger.error(f"update speed limiter error: {msg}")
        return False


async def add_speed_limiter(gost_api: GOSTApi, name: str, values: List = None) -> bool:
    if not values:
        return True

    data = {"name": name, "limits": values}
    success, msg, result = await gost_api.request(url="/config/limiters", method="post", data=data)
    if success and msg == "OK":
        return True
    elif msg == "object duplicated":
        return await update_speed_limiter(gost_api=gost_api, name=name, values=values)
    else:
        logger.error(f"add speed limiter error: {msg}")
        return False


async def update_conn_limiter(gost_api: GOSTApi, name: str, values: List = None) -> bool:
    data = {"limits": values}
    success, msg, result = await gost_api.request(url=f"/config/climiters/{name}", method="put", data=data)
    if success and msg == "OK":
        return True
    else:
        logger.error(f"update speed limiter error: {msg}")
        return False


async def add_conn_limiter(gost_api: GOSTApi, name: str, values: List = None) -> bool:
    if not values:
        return True

    data = {"name": name, "limits": values}
    success, msg, result = await gost_api.request(url="/config/climiters", method="post", data=data)
    if success and msg == "OK":
        return True
    elif msg == "object duplicated":
        return await update_conn_limiter(gost_api=gost_api, name=name, values=values)
    else:
        logger.error(f"add speed limiter error: {msg}")
        return False


async def calc_traffic_by_service(prom_api: PrometheusApi, seconds: int, direction: str) -> dict:
    """
    Calculate traffic by service during seconds.
    :param prom_api:
    :param seconds:
    :param direction:
    :return:
    """
    traffics = {}
    metrics = {"input": "gost_service_transfer_input_bytes_total", "output": "gost_service_transfer_output_bytes_total"}
    pql = f"sum by (service) (increase({metrics[direction]}[{seconds}s]))"
    success, result = await prom_api.request(url="/api/v1/query", method="get", params={"query": pql})
    if not success:
        logger.error(f"prom query error")
        return traffics

    data = result.get("data", {}).get("result", [])
    for d in data:
        service_name = d.get("metric", {}).get("service", "")
        value = float(d.get("value", [])[1])
        traffics[service_name] = value

    return traffics
