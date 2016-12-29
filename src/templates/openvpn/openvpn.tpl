%# Foris - web administration interface for OpenWrt based on NETCONF
%# Copyright (C) 2015 CZ.NIC, z. s. p. o. <https://www.nic.cz>
%#
%# Foris is distributed under the terms of GNU General Public License v3.
%# You should have received a copy of the GNU General Public License
%# along with this program.  If not, see <https://www.gnu.org/licenses/>.

%rebase("config/base.tpl", **locals())

<div id="page-openvpn" class="config-page">
  %include("_messages.tpl")
    <form method='post' action='{{ url("config_action", page_name="openvpn", action="download-config") }}'>
        <input type="hidden" name="csrf_token" value="{{ get_csrf_token() }}">
        <button name="download-config" type="submit">{{ trans("Download") }}</button>
    </form>

</div>
