# Foris - web administration interface for OpenWrt based on NETCONF
# Copyright (C) 2016 CZ.NIC, z. s. p. o. <https://www.nic.cz>
#
# Foris is distributed under the terms of GNU General Public License v3.
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import logging
from xml.etree import cElementTree as ET

from foris.nuci.client import dispatch
from ncclient.operations import TimeoutExpiredError
from ncclient.operations import RPCError

from . import openvpn_module as openvpn


logger = logging.getLogger(__name__)


def get_client_config():
    try:
        data = dispatch(openvpn.Download.rpc_download_config())
        return openvpn.Download.from_element(ET.fromstring(data.xml)).configuration
    except (RPCError, TimeoutExpiredError):
        return None
