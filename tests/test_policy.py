"""Regression tests for the controller's pure policy layer."""

import unittest

from flow_timeout_manager.config import BLOCK_TIMEOUT, FORWARDING_TIMEOUT
from flow_timeout_manager.policy import (
    ETH_TYPE_IP,
    IPPROTO_TCP,
    PacketFacts,
    blocked_match_fields,
    demo_host_inventory,
    forwarding_match_fields,
    should_block_service_flow,
    timeout_profile_for,
)


class PolicyTests(unittest.TestCase):
    def test_block_rule_is_selected_for_h1_to_h4_iperf(self):
        packet = PacketFacts(
            src_mac="00:00:00:00:00:01",
            dst_mac="00:00:00:00:00:04",
            in_port=1,
            eth_type=ETH_TYPE_IP,
            ipv4_src="10.0.0.1",
            ipv4_dst="10.0.0.4",
            ip_proto=IPPROTO_TCP,
            tcp_dst=5001,
        )

        self.assertTrue(should_block_service_flow(packet))
        self.assertEqual(timeout_profile_for(packet), BLOCK_TIMEOUT)
        self.assertEqual(
            blocked_match_fields(packet),
            {
                "in_port": 1,
                "eth_type": ETH_TYPE_IP,
                "ipv4_src": "10.0.0.1",
                "ipv4_dst": "10.0.0.4",
                "ip_proto": IPPROTO_TCP,
                "tcp_dst": 5001,
            },
        )

    def test_forwarding_rule_is_selected_for_normal_traffic(self):
        packet = PacketFacts(
            src_mac="00:00:00:00:00:02",
            dst_mac="00:00:00:00:00:03",
            in_port=2,
            eth_type=ETH_TYPE_IP,
            ipv4_src="10.0.0.2",
            ipv4_dst="10.0.0.3",
            ip_proto=IPPROTO_TCP,
            tcp_dst=5001,
        )

        self.assertFalse(should_block_service_flow(packet))
        self.assertEqual(timeout_profile_for(packet), FORWARDING_TIMEOUT)
        self.assertEqual(
            forwarding_match_fields(packet),
            {"in_port": 2, "eth_src": "00:00:00:00:00:02", "eth_dst": "00:00:00:00:00:03"},
        )

    def test_demo_inventory_is_complete(self):
        inventory = demo_host_inventory()
        self.assertEqual(len(inventory), 4)
        self.assertEqual({item["name"] for item in inventory}, {"h1", "h2", "h3", "h4"})


if __name__ == "__main__":
    unittest.main()
