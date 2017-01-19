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
  <h3>{{ trans("No certifite authority") }}</h3>
  <p>
  {{ trans("Currently there is no openvpn certificate authority(CA). A CA is required to generate client certificates to authenticate to the openvpn server. To proceed you need to generate it first.") }}
  <form method='post' action="{{ url("config_action", page_name="openvpn", action="generate-ca") }}">
    <input type="hidden" name="csrf_token" value="{{ get_csrf_token() }}">
    <button name="download-config" type="submit">{{ trans("Generate CA") }}</button>
  </form>
  </p>

%elif ca.missing or ca.generating:
  <h3>{{ trans("Generating certificate authority") }}</h3>
  <p>
  {{ trans("The CA necessary for the openvpn server is being generated. This could take a quite long time (up to 30 minutes). Please try to visit this page later. ") }}
  </p>
  <center><img src="{{ static("img/loader.gif") }}" alt="{{ trans("Loading...") }}"></center>

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
    %if config_form.data['enabled']:
       <div class="row config-readonly"><label>&nbsp;</label><input value="{{ current['network'] }}" readonly /></div>
       <div class="row config-readonly"><label>Device</label><input value="{{ current['device'] }}" readonly /></div>
       <div class="row config-readonly"><label>Protocol</label><input value="{{ current['protocol'] }}" readonly /></div>
       <div class="row config-readonly"><label>Port</label><input value="{{ current['port'] }}" readonly /></div>
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
                $('.config-readonly').show();
            } else {
                $('#field-network').parent().hide();
                $('.config-readonly').hide();
            }
        });
        %if not config_form.data['enabled']:
        $('#field-network').parent().hide();
        $('.config-readonly').hide();
        %end
    });
  </script>
  %if config_form.data['enabled']:
  <h3>{{ trans("Clients") }}</h3>
  <p>
    {{ trans("We assume that you have the openvpn server running on your router. The client configuration differs a bit based on your operating system. Be sure to check the configuration before you use it as a client configuration of your device. Especially check whether the public IP address matches your router.") }}
  </p>

    <h4>{{ trans("New client") }}</h4>

    <form action="{{ url("config_action", page_name="openvpn", action="generate-client") }}" method="post" class="config-form">
      <input type="hidden" name="csrf_token" value="{{ get_csrf_token() }}">
      %for field in client_form.active_fields:
          %include("_field.tpl", field=field)
      %end
      <button type="submit" name="send">{{ trans("Create") }}</button>
    </form>

  <p>
    %if client_certs:
  <form method='post' action='{{ url("config_action", page_name="openvpn", action="download-config") }}'>
    <input type="hidden" name="csrf_token" value="{{ get_csrf_token() }}">
    <table class="openvpn-clients">
      <thead>
        <tr>
          <th>{{ trans("Client") }}</th>
          <th>{{ trans("Status") }}</th>
          <th></th>
          <th></th>
        </tr>
      </thead>
      <tbody>
    %for cert in client_certs:
        <tr>
          <td>{{ cert["name"] }}</td>
          <td>{{ trans(cert['status']) }}</td>
          <td>
            %if cert['status'] == 'active':
            <button name="download-config" value="{{ cert["name"] }}" type="submit">{{ trans("Get Config") }}</button>
            %end
            %if cert['status'] != 'revoked':
            <button name="revoke-client" value="{{ cert["serial"] }}" type="submit">{{ trans("Revoke") }}</button>
            %end
          </td>
        </tr>
    %end
      </tbody>
    </table>
  </form>
    %end
  </p>
  <p>
    {{ trans("To apply this configuration on the client you need store it in the openvpn config directory (as /etc/openvpn/turris.conf or C:\\Program Files\\OpenVPN\\config\\turris.ovpn) and restart the openvpn client.") }}
  </p>
  %end
%end
</div>
