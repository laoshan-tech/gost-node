import logging
from json import JSONDecodeError
from typing import Tuple, Optional
from urllib.parse import urljoin

import httpx
from httpx import Response

from exceptions.gost import GOSTApiException
from exceptions.tyz import TYZApiException

logger = logging.getLogger(__name__)


class BasicApi:
    def __init__(self, endpoint: str):
        self.endpoint = endpoint

    async def req(self, url: str, method: str, params: dict = None, data: dict = None) -> Response:
        async with httpx.AsyncClient(timeout=10) as client:
            return await client.request(
                method=method.upper(), url=urljoin(self.endpoint, url), params=params, json=data
            )


class TYZApi(BasicApi):
    def __init__(self, endpoint: str, node_id: int, token: str):
        super().__init__(endpoint)
        self.node_id = node_id
        self.token = token

    async def request(
        self, url: str, method: str, params: dict = None, data: dict = None
    ) -> Tuple[bool, str, Optional[dict]]:
        try:
            if method.upper() not in ("GET", "POST", "PUT", "DELETE"):
                raise TYZApiException(f"unsupported method: {method}")

            response = await self.req(method=method, url=url, params=params, data=data)
            result = response.json()
            msg = result.get("msg", "")
            return response.status_code == 200, msg, result
        except JSONDecodeError:
            logger.error(f"json decode error:\n{response.text}")
            return False, "json decode error", None
        except Exception as e:
            logger.error(f"panel req error: {e}")
            return False, f"req error: {e}", None

    async def update_relay_rule_status(self, rule_id: int, rule_type: str, status: int):
        return await self.request(
            url="/api/relay-rule-sync/",
            method="PUT",
            data={"node_id": self.node_id, "token": self.token, "id": rule_id, "type": rule_type, "status": status},
        )

    async def fetch_relay_rules(self):
        return await self.request(
            url="/api/relay-rule-sync/", method="GET", params={"node_id": self.node_id, "token": self.token}
        )

    async def traffic_report(self, data: dict):
        post_data = {"node_id": self.node_id, "token": self.token, "data": data}
        return await self.request(url="/api/relay-rule-traffic/", method="POST", data=post_data)


class GOSTApi(BasicApi):
    def __init__(self, endpoint: str):
        super().__init__(endpoint)

    async def request(self, url: str, method: str, data: dict = None) -> Tuple[bool, str, Optional[dict]]:
        try:
            if method.upper() not in ("GET", "POST", "PUT", "DELETE"):
                raise GOSTApiException(f"unsupported method: {method}")

            response = await self.req(method=method, url=url, data=data)
            result = response.json()
            msg = result.get("msg", "")
            return response.status_code == 200, msg, result
        except JSONDecodeError:
            logger.error(f"json decode error:\n{response.text}")
            return False, "json decode error", None
        except Exception as e:
            logger.error(f"gost req error: {e}")
            return False, "req error", None


class PrometheusApi(BasicApi):
    def __init__(self, endpoint: str):
        super().__init__(endpoint=endpoint)

    async def request(self, url: str, method: str, params: dict = None) -> Tuple[bool, Optional[dict]]:
        try:
            response = await self.req(method=method.upper(), url=urljoin(self.endpoint, url), params=params)
            result = response.json()
            success = result.get("status", "") == "success"
            return success, result
        except JSONDecodeError:
            logger.error(f"json decode error:\n{response.text}")
            return False, None
        except Exception as e:
            logger.error(f"prometheus req error: {e}")
            return False, None
