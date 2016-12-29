%# Foris - web administration interface for OpenWrt based on NETCONF
%# Copyright (C) 2015 CZ.NIC, z. s. p. o. <https://www.nic.cz>
%#
%# Foris is distributed under the terms of GNU General Public License v3.
%# You should have received a copy of the GNU General Public License
%# along with this program.  If not, see <https://www.gnu.org/licenses/>.

%rebase("config/base.tpl", **locals())

<div id="page-openvpn" class="config-page">
  %include("_messages.tpl")
  <h3>{{ trans("Client configuration") }}</h3>
  <p>
    {{ trans("We assume that you have the openvpn server running on your router. The client configuration differs a bit based on your operating system. Be sure to check the configuration before you use it as a client configuration of your device. Especially check whether the public IP address matches your router.") }}
  </p>
  <p>
  <form method='post' action='{{ url("config_action", page_name="openvpn", action="download-config") }}'>
    <input type="hidden" name="csrf_token" value="{{ get_csrf_token() }}">
    <button name="download-config" type="submit">{{ trans("Download Configuration") }}</button>
  </form>
  </p>
  <p>
    {{ trans("To apply this configuration on the client you need store it in the openvpn config directory (as /etc/openvpn/turris.conf or C:\\Program Files\\OpenVPN\\config\\turris.ovpn) and restart the openvpn client.") }}
  </p>
</div>
