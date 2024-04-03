import pytest

from services.gost import add_ws_ingress_service, add_ws_egress_service, fetch_all_config, calc_traffic_by_service
from utils.gost import extract_key_from_dict_list


@pytest.mark.asyncio
async def test_add_ws_ingress():
    endpoint = "http://192.168.135.128:18080"
    result = await add_ws_ingress_service(
        endpoint=endpoint, name="ingress-service-0", addr=":8888", relay="127.0.0.1:8899", targets=["127.0.0.1:5201"]
    )
    assert result


@pytest.mark.asyncio
async def test_add_ws_egress():
    endpoint = "http://192.168.135.128:18080"
    result = await add_ws_egress_service(endpoint=endpoint, name="egress-service-0", addr=":8899")
    assert result


@pytest.mark.asyncio
async def test_parse_services():
    endpoint = "http://192.168.135.128:18080"
    result = await fetch_all_config(endpoint=endpoint)
    service_list = result.get("services")
    service_map = extract_key_from_dict_list(_list=service_list, key="name")
    assert len(service_map) == 2


@pytest.mark.asyncio
async def test_calc_traffic():
    prom = "http://192.168.135.128:19090"
    success, result = await calc_traffic_by_service(prom=prom, seconds=30, direction="output")
    assert success
    assert len(result) > 0
