import pytest

from services.gost import add_ws_ingress_service, add_ws_egress_service, fetch_all_config
from utils.gost import json_key_extract


@pytest.mark.asyncio
async def test_add_ws_ingress():
    endpoint = "http://127.0.0.1:18080"
    result = await add_ws_ingress_service(
        endpoint=endpoint, name="ingress-service-0", addr=":8888", relay="127.0.0.1:8899", targets=["127.0.0.1:5201"]
    )
    assert result


@pytest.mark.asyncio
async def test_add_ws_egress():
    endpoint = "http://127.0.0.1:18080"
    result = await add_ws_egress_service(endpoint=endpoint, name="egress-service-0", addr=":8899")
    assert result


@pytest.mark.asyncio
async def test_parse_services():
    endpoint = "http://127.0.0.1:18080"
    result = await fetch_all_config(endpoint=endpoint)
    service_list = result.get("services")
    service_map = json_key_extract(_list=service_list, key="name")
    assert len(service_map) == 2
