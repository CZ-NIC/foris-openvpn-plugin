%# Foris - web administration interface for OpenWrt based on NETCONF
%# Copyright (C) 2015 CZ.NIC, z. s. p. o. <https://www.nic.cz>
%#
%# Foris is distributed under the terms of GNU General Public License v3.
%# You should have received a copy of the GNU General Public License
%# along with this program.  If not, see <https://www.gnu.org/licenses/>.

%rebase("config/base.tpl", **locals())

<div id="page-openvpn" class="config-page">
%include("_messages.tpl")

%if not ca:
  <h3>{{ trans("No certificates") }}</h3>
  <p>
  {{ trans("Currently there are no certificates generated for the openvpn server. To proceed you need to generate the certificates.") }}
  <form method='post' action="{{ url("config_action", page_name="openvpn", action="generate-ca") }}">
    <input type="hidden" name="csrf_token" value="{{ get_csrf_token() }}">
    <button name="download-config" type="submit">{{ trans("Generate Certificates") }}</button>
  </form>
  </p>

%elif ca.missing or ca.generating:
  <h3>{{ trans("Generating certificates") }}</h3>
  <p>
  {{ trans("The certificates necessary for the openvpn server are being generated. This could take a quite long time (up to 30 minutes). You can try to visit this page later. ") }}
  </p>

%else:
  <h3>{{ trans("Server configuration") }}</h3>
  <p>
  {{ trans("You need to have your server properly configured (including firewall rules and network devices). To do so you need to apply the configuration provided by openvpn plugin. Note that the configuration might be in conflict with your existing configuration. So please disable your existing openvpn server configuration first.") }}
  </p>
  <p>
  {{! trans("It is also assumed that you have more or less standard network configuration (notably <strong>wan</strong> and <strong>lan</strong> interfaces are present).") }}
  </p>
  <form method='post' action='{{ url("config_page", page_name="openvpn") }}' class="config-form">
    <input type="hidden" name="csrf_token" value="{{ get_csrf_token() }}">
    %for field in config_form.active_fields:
        %include("_field.tpl", field=field)
    %end
    <button name="apply" type="submit">{{ trans("Apply") }}</button>
  </form>
  <p>
  {{! trans("Note that when you use <strong>Apply</strong> button you might lose the connection to the router for a while. This means that you might need <strong>reopen this page</strong> manually.") }}
  </p>
  <script>
    $(document).ready(function() {
        $('#field-enabled_1').click(function () {
            if ($(this).prop('checked')) {
                $('#field-network').parent().show();
            } else {
                $('#field-network').parent().hide();
            }
        });
        %if not config_form.data['enabled']:
        $('#field-network').parent().hide();
        %end
    });
  </script>
  %if config_form.data['enabled']:
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
  %end
%end
</div>
