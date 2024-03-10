import pytest

from services.gost import add_ws_ingress_service, add_ws_egress_service


@pytest.mark.asyncio
async def test_add_ws_ingress():
    endpoint = "http://127.0.0.1:18080"
    result = await add_ws_ingress_service(
        endpoint=endpoint, name="ingress-service-0", addr=":8888", targets=["127.0.0.1:8899"]
    )
    assert result


@pytest.mark.asyncio
async def test_add_ws_egress():
    endpoint = "http://127.0.0.1:18080"
    result = await add_ws_egress_service(
        endpoint=endpoint, name="egress-service-0", addr=":8899", targets=["127.0.0.1:5201"]
    )
    assert result
