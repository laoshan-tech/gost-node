import logging
from json import JSONDecodeError
from typing import List, Tuple, Optional
from urllib.parse import urljoin

import httpx

from exceptions.gost import GOSTApiException

logger = logging.getLogger(__name__)


async def gost_req(endpoint: str, url: str, method: str, data: dict = None) -> Tuple[bool, str, Optional[dict]]:
    """
    GOST API request.
    :param endpoint: gost api addr
    :param url:
    :param method: get/post/put/delete/etc
    :param data: json post data
    :return:
    """
    async with httpx.AsyncClient() as client:
        try:
            if method.upper() == "GET":
                response = await client.get(urljoin(endpoint, url))
            elif method.upper() in ("POST", "PUT", "DELETE"):
                response = await client.request(method=method, url=urljoin(endpoint, url), json=data)
            else:
                raise GOSTApiException(f"unsupported method: {method}")

            result = response.json()
        except JSONDecodeError:
            logger.error(f"json decode error:\n{response.text}")
            return False, "json decode error", None
        except Exception as e:
            logger.error(f"gost req error: {e}")
            return False, "req error", None

        msg = result.get("msg", "")
        return response.status_code == 200, msg, result


async def fetch_all_config(endpoint: str):
    success, msg, result = await gost_req(endpoint=endpoint, url="/config", method="get")
    if success:
        return result
    else:
        raise GOSTApiException(f"fetch all config error: {msg}")


async def update_ws_chain(endpoint: str, name: str, relay: str) -> bool:
    data = {
        "hops": [
            {
                "name": f"{name}-hop",
                "nodes": [
                    {
                        "name": f"{name}-relay-node",
                        "addr": relay,
                        "connector": {"type": "relay"},
                        "dialer": {"type": "ws"},
                    }
                ],
            }
        ],
    }
    success, msg, result = await gost_req(endpoint=endpoint, url=f"/config/chains/{name}", method="put", data=data)
    if success and msg == "OK":
        return True
    else:
        logger.error(f"update ws chain error: {msg}")
        return False


async def add_ws_chain(endpoint: str, name: str, relay: str) -> bool:
    data = {
        "name": name,
        "hops": [
            {
                "name": f"{name}-hop",
                "nodes": [
                    {
                        "name": f"{name}-relay-node",
                        "addr": relay,
                        "connector": {"type": "relay"},
                        "dialer": {"type": "ws"},
                    }
                ],
            }
        ],
    }
    success, msg, result = await gost_req(endpoint=endpoint, url="/config/chains", method="post", data=data)
    if success and msg == "OK":
        return True
    elif msg == "object duplicated":
        return await update_ws_chain(endpoint=endpoint, name=name, relay=relay)
    else:
        logger.error(f"add ws chain error: {msg}")
        return False


async def update_ws_ingress_service(endpoint: str, name: str, addr: str, targets: List[str]) -> bool:
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
    success, msg, result = await gost_req(endpoint=endpoint, url=f"/config/services/{name}", method="put", data=data)
    if success and msg == "OK":
        return True
    else:
        logger.error(f"update ws ingress service error: {msg}")
        return False


async def add_ws_ingress_service(endpoint: str, name: str, addr: str, relay: str, targets: List[str]):
    chain_name = f"{name}-chain"
    await add_ws_chain(endpoint=endpoint, name=chain_name, relay=relay)
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
    success, msg, result = await gost_req(endpoint=endpoint, url="/config/services", method="post", data=data)
    if success and msg == "OK":
        return True
    elif "object duplicated" == msg:
        return await update_ws_ingress_service(endpoint=endpoint, name=name, addr=addr, targets=targets)
    else:
        logger.error(f"add ws ingress service error: {msg}")
        return False


async def update_ws_egress_service(endpoint: str, name: str, addr: str) -> bool:
    data = {
        "addr": addr,
        "handler": {"type": "relay"},
        "listener": {"type": "ws"},
        "observer": "node-observer",
    }
    success, msg, result = await gost_req(endpoint=endpoint, url=f"/config/services/{name}", method="put", data=data)
    if success and msg == "OK":
        return True
    else:
        logger.error(f"update ws egress service error: {msg}")
        return False


async def add_ws_egress_service(endpoint: str, name: str, addr: str) -> bool:
    data = {
        "name": name,
        "addr": addr,
        "handler": {"type": "relay"},
        "listener": {"type": "ws"},
        "observer": "node-observer",
    }
    success, msg, result = await gost_req(endpoint=endpoint, url="/config/services", method="post", data=data)
    if success and msg == "OK":
        return True
    elif "object duplicated" == msg:
        return await update_ws_egress_service(endpoint=endpoint, name=name, addr=addr)
    else:
        logger.error(f"add ws egress service error: {msg}")
        return False
