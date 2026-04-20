"""Ryu controller for the Flow Rule Timeout Manager demo."""

from collections import defaultdict

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, DEAD_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.lib import hub
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.lib.packet import ipv4
from ryu.lib.packet import packet
from ryu.lib.packet import tcp
from ryu.ofproto import ofproto_v1_3

from flow_timeout_manager.config import MONITOR_INTERVAL
from flow_timeout_manager.policy import (
    PacketFacts,
    blocked_match_fields,
    forwarding_match_fields,
    should_block_service_flow,
    timeout_profile_for,
)


class FlowRuleTimeoutManager(app_manager.RyuApp):
    """Learning-switch controller with explicit timeout and block rules."""

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mac_to_port = defaultdict(dict)
        self.datapaths = {}
        self.monitor_thread = hub.spawn(self._monitor)

    @set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def _state_change_handler(self, ev):
        datapath = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            if datapath.id not in self.datapaths:
                self.logger.info("datapath %016x connected", datapath.id)
                self.datapaths[datapath.id] = datapath
        elif ev.state == DEAD_DISPATCHER and datapath.id in self.datapaths:
            self.logger.info("datapath %016x disconnected", datapath.id)
            del self.datapaths[datapath.id]

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(
            datapath=datapath,
            priority=0,
            match=match,
            actions=actions,
            idle_timeout=0,
            hard_timeout=0,
            send_flow_removed=False,
        )
        self.logger.info("table-miss rule installed on switch %016x", datapath.id)

    def add_flow(
        self,
        datapath,
        priority,
        match,
        actions,
        idle_timeout,
        hard_timeout,
        send_flow_removed,
        buffer_id=None,
    ):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        instructions = []
        if actions:
            instructions = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]

        flags = ofproto.OFPFF_SEND_FLOW_REM if send_flow_removed else 0
        kwargs = {
            "datapath": datapath,
            "priority": priority,
            "match": match,
            "instructions": instructions,
            "idle_timeout": idle_timeout,
            "hard_timeout": hard_timeout,
            "flags": flags,
        }
        if buffer_id is not None:
            kwargs["buffer_id"] = buffer_id
        mod = parser.OFPFlowMod(**kwargs)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        dpid = datapath.id
        in_port = msg.match["in_port"]

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        ip_pkt = pkt.get_protocol(ipv4.ipv4)
        tcp_pkt = pkt.get_protocol(tcp.tcp)

        facts = PacketFacts(
            src_mac=eth.src,
            dst_mac=eth.dst,
            in_port=in_port,
            eth_type=eth.ethertype,
            ipv4_src=ip_pkt.src if ip_pkt else None,
            ipv4_dst=ip_pkt.dst if ip_pkt else None,
            ip_proto=ip_pkt.proto if ip_pkt else None,
            tcp_dst=tcp_pkt.dst_port if tcp_pkt else None,
        )

        if should_block_service_flow(facts):
            timeout = timeout_profile_for(facts)
            match = parser.OFPMatch(**blocked_match_fields(facts))
            self.add_flow(
                datapath=datapath,
                priority=200,
                match=match,
                actions=[],
                idle_timeout=timeout.idle_timeout,
                hard_timeout=timeout.hard_timeout,
                send_flow_removed=True,
            )
            self.logger.info(
                "installed drop rule on switch %016x for %s -> %s tcp/%s",
                dpid,
                facts.ipv4_src,
                facts.ipv4_dst,
                facts.tcp_dst,
            )
            return

        self.mac_to_port[dpid][eth.src] = in_port
        if eth.dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][eth.dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]
        if out_port != ofproto.OFPP_FLOOD:
            timeout = timeout_profile_for(facts)
            match = parser.OFPMatch(**forwarding_match_fields(facts))
            buffer_id = None
            if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                buffer_id = msg.buffer_id

            self.add_flow(
                datapath=datapath,
                priority=100,
                match=match,
                actions=actions,
                idle_timeout=timeout.idle_timeout,
                hard_timeout=timeout.hard_timeout,
                send_flow_removed=True,
                buffer_id=buffer_id,
            )
            self.logger.info(
                "installed forwarding rule on switch %016x: %s -> %s via port %s (idle=%ss hard=%ss)",
                dpid,
                eth.src,
                eth.dst,
                out_port,
                timeout.idle_timeout,
                timeout.hard_timeout,
            )
            if buffer_id is not None:
                return
        else:
            self.logger.info("flooding unknown destination %s on switch %016x", eth.dst, dpid)

        data = None if msg.buffer_id != ofproto.OFP_NO_BUFFER else msg.data
        out = parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=msg.buffer_id,
            in_port=in_port,
            actions=actions,
            data=data,
        )
        datapath.send_msg(out)

    @set_ev_cls(ofp_event.EventOFPFlowRemoved, MAIN_DISPATCHER)
    def flow_removed_handler(self, ev):
        msg = ev.msg
        ofproto = msg.datapath.ofproto
        reasons = {
            ofproto.OFPRR_IDLE_TIMEOUT: "idle_timeout",
            ofproto.OFPRR_HARD_TIMEOUT: "hard_timeout",
            ofproto.OFPRR_DELETE: "delete",
            ofproto.OFPRR_GROUP_DELETE: "group_delete",
        }
        reason = reasons.get(msg.reason, f"unknown({msg.reason})")
        self.logger.info(
            "flow removed on switch %016x reason=%s packets=%s bytes=%s match=%s",
            msg.datapath.id,
            reason,
            msg.packet_count,
            msg.byte_count,
            msg.match,
        )

    def _monitor(self):
        while True:
            for datapath in list(self.datapaths.values()):
                self._request_flow_stats(datapath)
            hub.sleep(MONITOR_INTERVAL)

    def _request_flow_stats(self, datapath):
        parser = datapath.ofproto_parser
        req = parser.OFPFlowStatsRequest(datapath)
        datapath.send_msg(req)

    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def _flow_stats_reply_handler(self, ev):
        body = ev.msg.body
        interesting_flows = [
            stat
            for stat in body
            if stat.priority > 0 and stat.match
        ]
        if not interesting_flows:
            return

        self.logger.info("flow stats snapshot from switch %016x", ev.msg.datapath.id)
        for stat in sorted(interesting_flows, key=lambda item: (item.priority, str(item.match))):
            self.logger.info(
                "priority=%s packets=%s bytes=%s idle_timeout=%s hard_timeout=%s match=%s instructions=%s",
                stat.priority,
                stat.packet_count,
                stat.byte_count,
                stat.idle_timeout,
                stat.hard_timeout,
                stat.match,
                stat.instructions,
            )

