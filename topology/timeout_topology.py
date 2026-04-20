"""Mininet topology for the Flow Rule Timeout Manager project."""

from mininet.link import TCLink
from mininet.topo import Topo

from flow_timeout_manager.policy import demo_host_inventory


class FlowTimeoutTopo(Topo):
    """Two-switch topology with static host identities for repeatable flow matches."""

    def build(self):
        hosts = {host["name"]: host for host in demo_host_inventory()}

        s1 = self.addSwitch("s1", protocols="OpenFlow13")
        s2 = self.addSwitch("s2", protocols="OpenFlow13")

        h1 = self.addHost("h1", ip=f'{hosts["h1"]["ip"]}/24', mac=hosts["h1"]["mac"])
        h2 = self.addHost("h2", ip=f'{hosts["h2"]["ip"]}/24', mac=hosts["h2"]["mac"])
        h3 = self.addHost("h3", ip=f'{hosts["h3"]["ip"]}/24', mac=hosts["h3"]["mac"])
        h4 = self.addHost("h4", ip=f'{hosts["h4"]["ip"]}/24', mac=hosts["h4"]["mac"])

        self.addLink(h1, s1, cls=TCLink, bw=20, delay="5ms")
        self.addLink(h2, s1, cls=TCLink, bw=20, delay="5ms")
        self.addLink(h3, s2, cls=TCLink, bw=20, delay="5ms")
        self.addLink(h4, s2, cls=TCLink, bw=20, delay="5ms")
        self.addLink(s1, s2, cls=TCLink, bw=10, delay="12ms")


topos = {"flowtimeout": FlowTimeoutTopo}
