# Foris - web administration interface for OpenWrt based on NETCONF
# Copyright (C) 2016 CZ.NIC, z. s. p. o. <https://www.nic.cz>
#
# Foris is distributed under the terms of GNU General Public License v3.
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import re
from xml.etree import cElementTree as ET

from foris.nuci.modules import uci_raw
from foris.nuci.modules.base import YinElement

client_name_regexp = r'[a-zA-Z0-9_.-]+'
re_client_name = re.compile(client_name_regexp)

OPENVPN_CLIENT_URI = "http://www.nic.cz/ns/router/openvpn-client"
CAGEN_URI = "http://www.nic.cz/ns/router/ca-gen"


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
    def rpc_download_config():

        element = ET.Element(Download.qual_tag(Download.tag))
        cert_tag = Download.qual_tag("cert-name")
        cert_elem = ET.SubElement(element, cert_tag)
        cert_elem.text = "turris"  # client name is turris

        return element

    @property
    def key(self):
        return "download-config"


class CaGen(YinElement):
    tag = "ca-gen"
    NS_URI = CAGEN_URI

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
    def generating(self):
        if self.data['dhparams'] and self.data['dhparams']['generating']:
            return True
        for cert in self.data['certs']:
            if cert['status'] == 'generating':
                return True

        return False

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
            res = {'certs': [], 'dhparams': {}, 'crl': None}
            for cert_element in ca_element.findall(CaGen.qual_tag("cert")):
                status = cert_element.find(CaGen.qual_tag("status")).text
                record = {
                    'name': cert_element.find(CaGen.qual_tag("name")).text,
                    'type': cert_element.find(CaGen.qual_tag("type")).text,
                    'status': status,
                }

                if not status == "generating":
                    record['key_path'] = cert_element.find(CaGen.qual_tag("key")).text
                    record['cert_path'] = cert_element.find(CaGen.qual_tag("cert")).text

                res['certs'].append(record)
            dhparams_node = ca_element.find(CaGen.qual_tag("dhparams"))
            if dhparams_node:
                res['dhparams']['path'] = dhparams_node.find(CaGen.qual_tag("file")).text
                res['dhparams']['generating'] = \
                    False if dhparams_node.find(CaGen.qual_tag("generating")) is None else True
            crl_node = ca_element.find(CaGen.qual_tag("crl"))
            if crl_node:
                res['crl'] = crl_node.text

            return CaGen(res)

    @staticmethod
    def rpc_generate_certificates():
        root = ET.Element(CaGen.qual_tag("generate"))
        ET.SubElement(root, CaGen.qual_tag("background"))
        ca_element = ET.SubElement(root, CaGen.qual_tag("ca"))
        ET.SubElement(ca_element, CaGen.qual_tag("name")).text = 'openvpn'  # CA name
        ET.SubElement(ca_element, CaGen.qual_tag("new"))
        ET.SubElement(ca_element, CaGen.qual_tag("dhparams"))
        server_element = ET.SubElement(ca_element, CaGen.qual_tag("cert"))
        ET.SubElement(server_element, CaGen.qual_tag("name")).text = 'turris'
        ET.SubElement(server_element, CaGen.qual_tag("type")).text = 'server'
        client_cert = ET.SubElement(ca_element, CaGen.qual_tag("cert"))
        ET.SubElement(client_cert, CaGen.qual_tag("name")).text = 'turris'
        ET.SubElement(client_cert, CaGen.qual_tag("type")).text = 'client'

        return root


class Config(YinElement):
    tag = "config"

    IF_NAME = "tun_turris"
    PORT = "1194"
    PROTO = "udp"
    NETWORK = "10.111.0.0 255.255.255.0"

    @property
    def key(self):
        return Config.tag

    def __init__(self, network_enabled, firewall_enabled, openvpn_enabled):
        super(Config, self).__init__()
        self.enabled = network_enabled and firewall_enabled and openvpn_enabled

    @staticmethod
    def enabled_preproc(data):
        if data.find_child('uci.network.openvpn_turris_interface') \
                and data.find_child('uci.firewall.openvpn_turris_rule') \
                and data.find_child('uci.firewall.openvpn_turris_zone') \
                and data.find_child('uci.firewall.openvpn_turris_forward_lan_in') \
                and data.find_child('uci.firewall.openvpn_turris_forward_lan_out') \
                and data.find_child('uci.openvpn.server_turris'):
            return True
        else:
            return False

    @staticmethod
    def openvpn_filter():
        uci = uci_raw.Uci()
        network_conf = uci_raw.Config("network")
        uci.add(network_conf)
        network_conf.add(uci_raw.Section("openvpn_turris_interface", "interface"))

        firewall_conf = uci_raw.Config("firewall")
        uci.add(firewall_conf)  # get the whole firewall config - unable to filter

        openvpn_conf = uci_raw.Config("openvpn")
        uci.add(openvpn_conf)
        openvpn_conf.add(uci_raw.Section("server_turris", "openvpn"))

        return uci.get_xml()

    @staticmethod
    def prepare_edit_config(enabled):
        uci = uci_raw.Uci()

        # network config
        network_conf = uci_raw.Config("network")
        uci.add(network_conf)
        interface_section = uci_raw.Section("openvpn_turris_interface", "interface")
        network_conf.add_replace(interface_section) if enabled else \
            network_conf.add_removal(interface_section)
        interface_section.add(uci_raw.Option("ifname", Config.IF_NAME))
        interface_section.add(uci_raw.Option("proto", "none"))
        interface_section.add(uci_raw.Option("auto", "1"))

        # firewall config
        firewall_conf = uci_raw.Config("firewall")
        uci.add(firewall_conf)
        rule_section = uci_raw.Section("openvpn_turris_rule", "rule")
        firewall_conf.add_replace(rule_section) if enabled else \
            firewall_conf.add_removal(rule_section)
        rule_section.add(uci_raw.Option("target", "ACCEPT"))
        rule_section.add(uci_raw.Option("proto", Config.PROTO))
        rule_section.add(uci_raw.Option("src", "wan"))
        rule_section.add(uci_raw.Option("dest_port", Config.PORT))
        zone_section = uci_raw.Section("openvpn_turris_zone", "zone")
        firewall_conf.add_replace(zone_section) if enabled else \
            firewall_conf.add_removal(zone_section)
        zone_section.add(uci_raw.Option("name", "openvpn_turris_zone"))
        zone_section.add(uci_raw.Option("network", "openvpn_turris_interface"))
        zone_section.add(uci_raw.Option("input", "ACCEPT"))
        zone_section.add(uci_raw.Option("forward", "REJECT"))
        zone_section.add(uci_raw.Option("output", "ACCEPT"))
        zone_section.add(uci_raw.Option("masq", "1"))
        forward_lan_in_section = uci_raw.Section("openvpn_turris_forward_lan_in", "forwarding")
        firewall_conf.add_replace(forward_lan_in_section) if enabled else \
            firewall_conf.add_removal(forward_lan_in_section)
        forward_lan_in_section.add(uci_raw.Option("src", "openvpn_turris_zone"))
        forward_lan_in_section.add(uci_raw.Option("dest", "lan"))
        forward_lan_out_section = uci_raw.Section("openvpn_turris_forward_lan_out", "forwarding")
        firewall_conf.add_replace(forward_lan_out_section) if enabled else \
            firewall_conf.add_removal(forward_lan_out_section)
        forward_lan_out_section.add(uci_raw.Option("src", "lan"))
        forward_lan_out_section.add(uci_raw.Option("dest", "openvpn_turris_zone"))
        # TODO we could optionally add openvpn_turris_zone -> wan forwarding

        # openvpn config
        openvpn_conf = uci_raw.Config("openvpn")
        uci.add(openvpn_conf)
        server_section = uci_raw.Section("server_turris", "openvpn")
        openvpn_conf.add_replace(server_section) if enabled else \
            openvpn_conf.add_removal(server_section)
        server_section.add(uci_raw.Option("port", Config.PORT))
        server_section.add(uci_raw.Option("proto", Config.PROTO))
        server_section.add(uci_raw.Option("dev", Config.IF_NAME))
        server_section.add(uci_raw.Option("ca", "/etc/ssl/ca/openvpn/ca.crt"))
        server_section.add(uci_raw.Option("cert", "/etc/ssl/ca/openvpn/server-turris.crt"))
        server_section.add(uci_raw.Option("key", "/etc/ssl/ca/openvpn/server-turris.key"))
        server_section.add(uci_raw.Option("dh", "/etc/ssl/ca/openvpn/dhparam.pem"))
        server_section.add(uci_raw.Option("server", Config.NETWORK))  # TODO config option
        server_section.add(uci_raw.Option("ifconfig_pool_persist", "/tmp/ipp.txt"))
        #server_section.add(uci_raw.Option("client_to_client", "1")) # TODO config option
        server_section.add(uci_raw.Option("duplicate_cn", "1"))  # TODO we could use more cert -> remove
        server_section.add(uci_raw.Option("keepalive", "10 120"))
        # TODO might be nice to generate tls_auth as well
        server_section.add(uci_raw.Option("comp_lzo", "yes"))
        server_section.add(uci_raw.Option("persist_key", "1"))
        server_section.add(uci_raw.Option("persist_tun", "1"))
        server_section.add(uci_raw.Option("status", "/tmp/openvpn-status.log"))
        server_section.add(uci_raw.Option("verb", "3"))
        server_section.add(uci_raw.Option("mute", "20"))

        return uci.get_xml()

####################################################################################################
ET.register_namespace("openvpn", Download.NS_URI)
ET.register_namespace("ca-gen", CaGen.NS_URI)
