# Foris - web administration interface for OpenWrt based on NETCONF
# Copyright (C) 2017 CZ.NIC, z. s. p. o. <https://www.nic.cz>
#
# Foris is distributed under the terms of GNU General Public License v3.
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import re
from xml.etree import cElementTree as ET

from foris.core import gettext_dummy as _
from foris.nuci.modules import uci_raw
from foris.nuci.modules.base import YinElement

client_name_regexp = r'[a-zA-Z0-9_.-]+'
re_client_name = re.compile(client_name_regexp)

from ..utils import normalize_subnet_4, mask_to_prefix_4

OPENVPN_CLIENT_URI = "http://www.nic.cz/ns/router/openvpn-client"
CAGEN_URI = "http://www.nic.cz/ns/router/ca-gen"
UCI_RAW = "http://www.nic.cz/ns/router/uci-raw"


class Download(YinElement):
    tag = "download-config"
    NS_URI = OPENVPN_CLIENT_URI

    def __init__(self, configuration):
        super(Download, self).__init__()
        self.configuration = configuration

    @staticmethod
    def from_element(element):
        openvpn_client_node = element.find(Download.qual_tag("openvpn-client"))
        configuration_node = openvpn_client_node.find(Download.qual_tag("configuration"))
        return Download(configuration_node.text)

    @staticmethod
    def rpc_download_config(serial, server_address=None):

        element = ET.Element(Download.qual_tag(Download.tag))
        cert_elem = ET.SubElement(element, Download.qual_tag("cert-serial"))
        cert_elem.text = serial

        config_elem = ET.SubElement(element, Download.qual_tag("config-name"))
        config_elem.text = "server_turris"  # config name is server_turris

        if server_address:
            server_elem = ET.SubElement(element, Download.qual_tag("server-address"))
            server_elem.text = server_address

        return element

    @property
    def key(self):
        return "download-config"


class CaGen(YinElement):
    tag = "ca-gen"
    NS_URI = CAGEN_URI

    CLIENT_STATUS_ACTIVE = _("active")
    CLIENT_STATUS_REVOKED = _("revoked")
    CLIENT_STATUS_EXPIRED = _("expired")
    CLIENT_STATUS_GENERATING = _("generating")
    CLIENT_STATUS_LOST = _("lost")

    def __init__(self, data):
        super(CaGen, self).__init__()
        self.data = data

    @property
    def key(self):
        return "ca-gen"

    @property
    def missing(self):
        return False if self.data['certs'] else True

    @property
    def ca_ready(self):
        # ca missing
        if self.missing:
            return False

        # At least one root certificate is ready
        if not [e for e in self.data['certs'] if e['type'] == 'root' and
                e['status'] != 'generating']:
            return False

        # At least one server certificate is ready
        if not [e for e in self.data['certs'] if e['type'] == 'server' and
                e['status'] != 'generating']:
            return False

        return True

    def get_paths(self, cert_type):
        res = []
        for cert in self.data['certs']:
            if cert['type'] == cert_type and cert['status'] == 'active':
                res.append((cert['cert_path'], cert['key_path']))
        return res

    @staticmethod
    def openvpn_filter():
        cas_element = ET.Element(CaGen.qual_tag("cas"))
        ca_element = ET.SubElement(cas_element, "ca")
        name_element = ET.SubElement(ca_element, "name")
        name_element.text = "openvpn"
        return cas_element

    @staticmethod
    def from_element(element):
        for ca_element in element.findall(CaGen.qual_tag("ca")):
            # handle only openvpn ca
            if ca_element.find(CaGen.qual_tag("name")).text != "openvpn":
                continue
            res = {'certs': [], 'crl': None}
            for cert_element in ca_element.findall(CaGen.qual_tag("cert")):
                status = cert_element.find(CaGen.qual_tag("status")).text
                record = {
                    'name': cert_element.find(CaGen.qual_tag("name")).text,
                    'serial': cert_element.find(CaGen.qual_tag("serial")).text,
                    'type': cert_element.find(CaGen.qual_tag("type")).text,
                    'status': status,
                }

                if status == "active":
                    record['key_path'] = cert_element.find(CaGen.qual_tag("key")).text
                    record['cert_path'] = cert_element.find(CaGen.qual_tag("cert")).text

                res['certs'].append(record)
            crl_node = ca_element.find(CaGen.qual_tag("crl"))
            if crl_node:
                res['crl'] = crl_node.text

            return CaGen(res)

    @staticmethod
    def rpc_generate_ca():
        root = ET.Element(CaGen.qual_tag("generate"))
        ET.SubElement(root, CaGen.qual_tag("background"))
        ca_element = ET.SubElement(root, CaGen.qual_tag("ca"))
        ET.SubElement(ca_element, CaGen.qual_tag("name")).text = 'openvpn'  # CA name
        ET.SubElement(ca_element, CaGen.qual_tag("new"))
        server_element = ET.SubElement(ca_element, CaGen.qual_tag("cert"))
        ET.SubElement(server_element, CaGen.qual_tag("name")).text = 'turris'
        ET.SubElement(server_element, CaGen.qual_tag("type")).text = 'server'

        return root

    @staticmethod
    def rpc_delete_ca():
        root = ET.Element(CaGen.qual_tag("delete-ca"))
        ET.SubElement(root, CaGen.qual_tag("ca")).text = 'openvpn'
        return root

    @staticmethod
    def rpc_generate_client(name):
        root = ET.Element(CaGen.qual_tag("generate"))
        ET.SubElement(root, CaGen.qual_tag("background"))
        ca_element = ET.SubElement(root, CaGen.qual_tag("ca"))
        ET.SubElement(ca_element, CaGen.qual_tag("name")).text = 'openvpn'
        client_cert = ET.SubElement(ca_element, CaGen.qual_tag("cert"))
        ET.SubElement(client_cert, CaGen.qual_tag("name")).text = name
        ET.SubElement(client_cert, CaGen.qual_tag("type")).text = 'client'

        return root

    @staticmethod
    def rpc_revoke_client(serial):
        root = ET.Element(CaGen.qual_tag("revoke"))
        ca_element = ET.SubElement(root, CaGen.qual_tag("ca"))
        ET.SubElement(ca_element, CaGen.qual_tag("name")).text = 'openvpn'
        ET.SubElement(ca_element, CaGen.qual_tag("cert")).text = serial
        return root


class Config(YinElement):
    tag = "config"
    NS_URI = UCI_RAW

    IF_NAME = "tun_turris"
    PORT = "1194"
    PROTO = "udp"
    DEFAULT_MASK = "255.255.255.0"
    DEFAULT_NETWORK = "10.111.111.0"
    DEFAULT_VPN_DEF_ROUTE = False

    @property
    def key(self):
        return Config.tag

    @staticmethod
    def enabled_preproc(data):
        if data.find_child('uci.network.vpn_turris') \
                and data.find_child('uci.firewall.vpn_turris_rule') \
                and data.find_child('uci.firewall.vpn_turris') \
                and data.find_child('uci.firewall.vpn_turris_forward_lan_in') \
                and data.find_child('uci.firewall.vpn_turris_forward_lan_out') \
                and data.find_child('uci.openvpn.server_turris'):
            return True
        else:
            return False

    @staticmethod
    def network_preproc(data):
        # default values
        address = Config.DEFAULT_NETWORK
        prefix = mask_to_prefix_4(Config.DEFAULT_MASK)

        network_node = data.find_child('uci.openvpn.server_turris.server')
        if network_node:
            network_data = network_node.value.split()
            if len(network_data) == 0:
                address, mask = Config.DEFAULT_NETWORK, Config.DEFAULT_SUBNET
            elif len(network_data) == 1:
                address, mask = network_data[0], Config.DEFAULT_SUBNET
            else:
                address, mask = network_data[0], network_data[1]
            try:
                address = normalize_subnet_4(address, mask)
                prefix = mask_to_prefix_4(mask)
            except ValueError:
                address = Config.DEFAULT_NETWORK
                prefix = mask_to_prefix_4(Config.DEFAULT_MASK)

        return "%s/%d" % (address, prefix)

    @staticmethod
    def default_route_preproc(data):
        # default value
        default_route = Config.DEFAULT_VPN_DEF_ROUTE

        push_node = data.find_child('uci.openvpn.server_turris.push')
        if push_node:
            return "redirect-gateway def1" in [e.content for e in push_node.children]

        return default_route

    @staticmethod
    def openvpn_filter():
        uci = uci_raw.Uci()
        network_conf = uci_raw.Config("network")
        uci.add(network_conf)
        network_conf.add(uci_raw.Section("vpn_turris", "interface"))

        firewall_conf = uci_raw.Config("firewall")
        uci.add(firewall_conf)  # get the whole firewall config - unable to filter

        openvpn_conf = uci_raw.Config("openvpn")
        uci.add(openvpn_conf)
        openvpn_conf.add(uci_raw.Section("server_turris", "openvpn"))

        return uci.get_xml()

    @staticmethod
    def prepare_edit_config(
            enabled, network, netmask, route_network, route_netmask,
            default_route, cert_path, key_path):
        uci = uci_raw.Uci()

        # network config
        network_conf = uci_raw.Config("network")
        uci.add(network_conf)
        interface_section = uci_raw.Section("vpn_turris", "interface")
        network_conf.add_replace(interface_section) if enabled else \
            network_conf.add_removal(interface_section)
        interface_section.add(uci_raw.Option("ifname", Config.IF_NAME))
        interface_section.add(uci_raw.Option("proto", "none"))
        interface_section.add(uci_raw.Option("auto", "1"))

        # firewall config
        firewall_conf = uci_raw.Config("firewall")
        uci.add(firewall_conf)
        rule_section = uci_raw.Section("vpn_turris_rule", "rule")
        firewall_conf.add_replace(rule_section) if enabled else \
            firewall_conf.add_removal(rule_section)
        rule_section.add(uci_raw.Option("name", "vpn_turris_rule"))
        rule_section.add(uci_raw.Option("target", "ACCEPT"))
        rule_section.add(uci_raw.Option("proto", Config.PROTO))
        rule_section.add(uci_raw.Option("src", "wan"))
        rule_section.add(uci_raw.Option("dest_port", Config.PORT))
        zone_section = uci_raw.Section("vpn_turris", "zone")
        firewall_conf.add_replace(zone_section) if enabled else \
            firewall_conf.add_removal(zone_section)
        zone_section.add(uci_raw.Option("name", "vpn_turris"))
        network_list = uci_raw.List("network")
        network_list.add(uci_raw.Value(0, "vpn_turris"))
        zone_section.add(network_list)
        zone_section.add(uci_raw.Option("input", "ACCEPT"))
        zone_section.add(uci_raw.Option("forward", "REJECT"))
        zone_section.add(uci_raw.Option("output", "ACCEPT"))
        zone_section.add(uci_raw.Option("masq", "1"))
        forward_lan_in_section = uci_raw.Section("vpn_turris_forward_lan_in", "forwarding")
        firewall_conf.add_replace(forward_lan_in_section) if enabled else \
            firewall_conf.add_removal(forward_lan_in_section)
        forward_lan_in_section.add(uci_raw.Option("src", "vpn_turris"))
        forward_lan_in_section.add(uci_raw.Option("dest", "lan"))
        forward_lan_out_section = uci_raw.Section("vpn_turris_forward_lan_out", "forwarding")
        firewall_conf.add_replace(forward_lan_out_section) if enabled else \
            firewall_conf.add_removal(forward_lan_out_section)
        forward_lan_out_section.add(uci_raw.Option("src", "lan"))
        forward_lan_out_section.add(uci_raw.Option("dest", "vpn_turris"))
        if default_route:
            forward_wan_out_section = uci_raw.Section("vpn_turris_forward_wan_out", "forwarding")
            firewall_conf.add_replace(forward_wan_out_section) if enabled else \
                firewall_conf.add_removal(forward_wan_out_section)
            forward_wan_out_section.add(uci_raw.Option("src", "vpn_turris"))
            forward_wan_out_section.add(uci_raw.Option("dest", "wan"))

        # openvpn config
        openvpn_conf = uci_raw.Config("openvpn")
        uci.add(openvpn_conf)
        server_section = uci_raw.Section("server_turris", "openvpn")
        openvpn_conf.add_replace(server_section) if enabled else \
            openvpn_conf.add_removal(server_section)
        server_section.add(uci_raw.Option("enabled", "1"))
        server_section.add(uci_raw.Option("port", Config.PORT))
        server_section.add(uci_raw.Option("proto", Config.PROTO))
        server_section.add(uci_raw.Option("dev", Config.IF_NAME))
        server_section.add(uci_raw.Option("ca", "/etc/ssl/ca/openvpn/ca.crt"))
        server_section.add(uci_raw.Option("crl_verify", "/etc/ssl/ca/openvpn/ca.crl"))
        server_section.add(uci_raw.Option("cert", cert_path))
        server_section.add(uci_raw.Option("key", key_path))
        server_section.add(uci_raw.Option("dh", "/etc/dhparam/dh-default.pem"))
        server_section.add(uci_raw.Option("server", "%s %s" % (network, netmask)))
        server_section.add(uci_raw.Option("ifconfig_pool_persist", "/tmp/ipp.txt"))
        #server_section.add(uci_raw.Option("client_to_client", "1")) # TODO config option
        server_section.add(uci_raw.Option("duplicate_cn", "0"))
        server_section.add(uci_raw.Option("keepalive", "10 120"))
        # TODO might be nice to generate tls_auth as well
        server_section.add(uci_raw.Option("comp_lzo", "yes"))
        server_section.add(uci_raw.Option("persist_key", "1"))
        server_section.add(uci_raw.Option("persist_tun", "1"))
        server_section.add(uci_raw.Option("status", "/tmp/openvpn-status.log"))
        server_section.add(uci_raw.Option("verb", "3"))
        server_section.add(uci_raw.Option("mute", "20"))
        routes = uci_raw.List("push")
        routes.add(uci_raw.Value(
            0, "route %s %s" % (normalize_subnet_4(route_network, route_netmask), route_netmask))
        )
        if default_route:
            routes.add(uci_raw.Value(1, "redirect-gateway def1"))

        server_section.add(routes)

        return uci.get_xml()


class LAN(YinElement):
    tag = "config"
    NS_URI = UCI_RAW

    def __init__(self, network, netmask):
        super(LAN, self).__init__()
        self.network = network
        self.netmask = netmask

    @staticmethod
    def from_element(element):

        uci_element = element.find(LAN.qual_tag("uci"))
        uci = uci_raw.Uci.from_element(uci_element)
        network = uci.find_child('network.lan.ipaddr')
        netmask = uci.find_child('network.lan.netmask')

        if not network or not netmask:
            return None

        return LAN(network.value, netmask.value)

    @staticmethod
    def lan_network_filter():
        uci = uci_raw.Uci()
        network_conf = uci_raw.Config("network")
        uci.add(network_conf)
        network_conf.add(uci_raw.Section("lan", "interface"))
        return uci.get_xml()


class Foris(YinElement):
    tag = "config"
    NS_URI = UCI_RAW

    def __init__(self, server_address):
        super(Foris, self).__init__()
        self.server_address = server_address

    @staticmethod
    def foris_openvpn_filter():
        uci = uci_raw.Uci()
        uci_foris = uci_raw.Config("foris")
        uci.add(uci_foris)
        uci_foris.add(uci_raw.Section("openvpn_plugin", "config"))
        return uci.get_xml()

    @staticmethod
    def from_element(element):
        uci_element = element.find(Foris.qual_tag("uci"))
        uci = uci_raw.Uci.from_element(uci_element)
        server_address = uci.find_child('foris.openvpn_plugin.server_address')
        return Foris(server_address.value if server_address else "")

    @staticmethod
    def prepare_edit(data):
        uci = uci_raw.Uci()
        uci_foris = uci_raw.Config("foris")
        uci.add(uci_foris)
        uci_section = uci_raw.Section("openvpn_plugin", "config")
        uci_foris.add(uci_section)
        if "server-address" in data:
            uci_section.add(uci_raw.Option("server_address", data["server-address"]))

        return uci


####################################################################################################
ET.register_namespace("openvpn-client", Download.NS_URI)
ET.register_namespace("ca-gen", CaGen.NS_URI)
