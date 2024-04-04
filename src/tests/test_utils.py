from utils.gost import parse_rule_info_from_service


def test_parse_rule_info_from_service():
    name = "rule-2-egress-node-1"
    rule_id, rule_type, node_id = parse_rule_info_from_service(service=name)
    assert rule_id == 2
    assert rule_type == "egress"
    assert node_id == 1
