from enum import Enum


class RuleType(Enum):
    EGRESS = "Egress"
    RAW = "Raw"
    TUNNEL = "Tunnel"
