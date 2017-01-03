# Foris - web administration interface for OpenWrt based on NETCONF
# Copyright (C) 2016 CZ.NIC, z. s. p. o. <https://www.nic.cz>
#
# Foris is distributed under the terms of GNU General Public License v3.
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import re
from xml.etree import cElementTree as ET

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

####################################################################################################
ET.register_namespace("openvpn", Download.NS_URI)
ET.register_namespace("ca-gen", CaGen.NS_URI)
