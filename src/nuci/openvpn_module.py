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
        download_tag = Download.qual_tag(Download.tag)

        element = ET.Element(download_tag)
        cert_tag = Download.qual_tag("cert-name")
        cert_elem = ET.SubElement(element, cert_tag)
        cert_elem.text = "turris"  # client name is turris

        return element

    @property
    def key(self):
        return "download-config"


####################################################################################################
ET.register_namespace("openvpn", Download.NS_URI)
