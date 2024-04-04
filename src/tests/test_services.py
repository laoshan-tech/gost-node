import pytest

from services.api import GOSTApi, PrometheusApi
from services.gost import add_ws_ingress_service, add_ws_egress_service, fetch_all_config, calc_traffic_by_service
from utils.gost import extract_key_from_dict_list, GOSTAuth


@pytest.mark.asyncio
async def test_add_ws_ingress():
    gost_api = GOSTApi(endpoint="http://192.168.135.128:18080")
    result = await add_ws_ingress_service(
        gost_api=gost_api,
        name="ingress-service-0",
        addr=":8888",
        relay="127.0.0.1:8899",
        targets=["127.0.0.1:5201"],
        auth=GOSTAuth(username="n1", password="n2"),
    )
    assert result


@pytest.mark.asyncio
async def test_add_ws_egress():
    gost_api = GOSTApi(endpoint="http://192.168.135.128:18080")
    result = await add_ws_egress_service(
        gost_api=gost_api, name="egress-service-0", addr=":8899", auth=GOSTAuth(username="n1", password="n2")
    )
    assert result


@pytest.mark.asyncio
async def test_parse_services():
    gost_api = GOSTApi(endpoint="http://192.168.135.128:18080")
    result = await fetch_all_config(gost_api=gost_api)
    service_list = result.get("services")
    service_map = extract_key_from_dict_list(_list=service_list, key="name")
    assert len(service_map) == 2


@pytest.mark.asyncio
async def test_calc_traffic():
    prom = PrometheusApi(endpoint="http://192.168.135.128:19090")
    result = await calc_traffic_by_service(prom_api=prom, seconds=30, direction="output")
    assert len(result) > 0
