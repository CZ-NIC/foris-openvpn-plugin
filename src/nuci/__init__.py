# Foris - web administration interface for OpenWrt based on NETCONF
# Copyright (C) 2016 CZ.NIC, z. s. p. o. <https://www.nic.cz>
#
# Foris is distributed under the terms of GNU General Public License v3.
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import logging
from xml.etree import cElementTree as ET

from foris.nuci.client import dispatch, netconf, edit_config
from ncclient.operations import TimeoutExpiredError
from ncclient.operations import RPCError

from . import openvpn_module as openvpn


logger = logging.getLogger(__name__)


def get_client_config(name):
    try:
        data = dispatch(openvpn.Download.rpc_download_config(name))
        return openvpn.Download.from_element(ET.fromstring(data.xml)).configuration
    except (RPCError, TimeoutExpiredError):
        return None


def get_openvpn_ca():
    try:
        data = netconf.get(filter=("subtree", openvpn.CaGen.openvpn_filter())).data_ele
        for elem in data.iter():
            if elem.tag == openvpn.CaGen.qual_tag("cas"):
                return openvpn.CaGen.from_element(elem)
    except (RPCError, TimeoutExpiredError):
        return None
    return None


def generate_ca():
    try:
        dispatch(openvpn.CaGen.rpc_generate_ca())
        return True
    except (RPCError, TimeoutExpiredError):
        return False


def generate_client(name):
    try:
        dispatch(openvpn.CaGen.rpc_generate_client(name))
        return True
    except (RPCError, TimeoutExpiredError):
        return False


def update_configs(
        enabled, network, netmask,
        cert_path="/etc/ssl/ca/openvpn/01.pem", key_path="/etc/ssl/ca/openvpn/01.key"):
    try:
        # read lan
        data = netconf.get(filter=("subtree", openvpn.LAN.lan_network_filter())).data_ele
        lan_config = openvpn.LAN.from_element(data)
        if not lan_config:
            return False
        # update config
        edit_config(openvpn.Config.prepare_edit_config(
            enabled, network, netmask, lan_config.network, lan_config.netmask, cert_path, key_path
        ))
        return True
    except (RPCError, TimeoutExpiredError):
        return False


def revoke_client(serial):
    try:
        dispatch(openvpn.CaGen.rpc_revoke_client(serial))
        return True
    except (RPCError, TimeoutExpiredError):
        return False
