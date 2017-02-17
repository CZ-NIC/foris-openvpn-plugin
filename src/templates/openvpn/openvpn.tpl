%# Foris - web administration interface for OpenWrt based on NETCONF
%# Copyright (C) 2017 CZ.NIC, z. s. p. o. <https://www.nic.cz>
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
  {{ trans("Currently there is no OpenVPN certificate authority(CA). A CA is required to generate client certificates to authenticate to the OpenVPN server. To proceed you need to generate it first.") }}
  <form method='post' action="{{ url("config_action", page_name="openvpn", action="generate-ca") }}">
    <input type="hidden" name="csrf_token" value="{{ get_csrf_token() }}">
    <button name="download-config" type="submit">{{ trans("Generate CA") }}</button>
  </form>
  </p>

%elif not ca.ca_ready:
  <h3>{{ trans("Generating certificate authority") }}</h3>
  <p>
  {{ trans("The CA necessary for the OpenVPN server is being generated. The time required for generating CA way differ. It could take up to 30 minutes. Please try to reload this page lager.") }}
  </p>
  <center><img src="{{ static("img/loader.gif") }}" alt="{{ trans("Loading...") }}"></center>
  <br/>
  <center><form><button name="reload-page" type="submit">{{ trans("Reload page") }}</button></form></center>

%else:
  <h3>{{ trans("Server configuration") }}</h3>
  <span>{{ trans("To work properly OpenVPN plugin needs:") }}</span>
  <ul class="points">
    <li>{{ trans("public IP address (preferably static)") }}</li>
    <li>{{ trans("standard network settings (WAN and LAN devices present)") }}</li>
  </ul>
  <h4>{{ trans("Previous settings") }}</h4>
  <p>{{! trans("If you haven't tried to set up OpenVPN server on our router yet, you can safely proceed to <strong>\"Apply configuration\"</strong> button.") }}</p>
  <p>{{ trans("Otherwise if you've tried to set up OpenVPN outside this plugin, there is a chance that your configuration might collide with the configuration created by this plugin. Therefore you might need to disable the old configuration first.") }}</p>
  <table class="opevpn-settings">
    <tbody><tr><td>
      <form method='post' action='{{ url("config_page", page_name="openvpn") }}' class="config-form">
        <input type="hidden" name="csrf_token" value="{{ get_csrf_token() }}">
    %for field in config_form.active_fields:
        %include("_field.tpl", field=field)
    %end
        <button name="apply" type="submit">{{ trans("Apply configuration") }}</button>
      </form>
    </td><td>
    <div class="openvpn-config-current">
    %if config_form.data['enabled']:
      <table class="openvpn-current-settings">
       <tr><th colspan="2"><strong>{{ trans("Current settings") }}</strong></th></tr>
       <tr><td>{{ trans("Network:") }}</td><td>{{ current['network'] }}</td></tr>
       <tr><td>{{ trans("Device:") }}</td><td>{{ current['device'] }}</td></tr>
       <tr><td>{{ trans("Protocol:") }}</td><td>{{ current['protocol'] }}</td></tr>
       <tr><td>{{ trans("Port:") }}</td><td>{{ current['port'] }}</td></tr>
      </table>
    %end
    </div>
    </td></tr></tbody>
    </table>
  <p>
  {{! trans("Note that when you trigger <strong>\"Apply configuration\"</strong> button you might lose the connection to the router for a while. This means that you might need to reopen this admin page again.") }}
  </p>
  <script>
    $(document).ready(function() {
        $('#field-enabled_1').click(function () {
            if ($(this).prop('checked')) {
                $('#field-network').parent().show();
                $('.openvpn-config-current').show();
            } else {
                $('#field-network').parent().hide();
                $('.openvpn-config-current').hide();
            }
        });
        %if not config_form.data['enabled']:
        $('#field-network').parent().hide();
        $('.openvpn-config-current').hide();
        %end
    });
  </script>
  %if config_form.data['enabled']:
  <h3>{{ trans("Client configuration") }}</h3>
    <p>{{ trans("Here you can create and revoke the client capability to connect to your OpenVPN network.") }}</p>

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
    % include('openvpn/_clients.tpl', client_certs=client_certs)
  </form>
    %end
  </p>
  <p>
    {{ trans("Be sure to check, that the server IP address provided in you configuration file actually matches the public IP address of your router.") }}
  </p>

  <p>
    {{ trans("To apply the client configuration you need to download it and put it into the OpenVPN config directory or you might try to open it using your OpenVPN client directly. You might need to restart your client afterwards.") }}
  </p>
  %end
  <h3>{{ trans("Delete CA") }}</h3>
  <p>
    %if config_form.data['enabled']:
      {{ trans("You can't delete the CA while the OpenVPN server is enabled. To delete the CA you need to disable the server configuration first.") }}
    %else:
      {{ trans("You can delete the whole CA. Note that all the cerificates issued by this CA will be useless and if you wanted to use this plugin, you'd need to generate a new CA first.") }}
    <form action="{{ url("config_action", page_name="openvpn", action="delete-ca") }}" method="post" id="delete-ca-form">
      <input type="hidden" name="csrf_token" value="{{ get_csrf_token() }}">
      <button type="submit" name="send" id="reset-ca-submit">{{ trans("Delete CA") }}</button>
    </form>
    <script>
      $(document).ready(function() {
          $('#delete-ca-form').on('click', function(e) {
              var answer = confirm("{{ trans("Are you sure you want to delete the OpenVPN CA?") }}");
              if (!answer) {
                e.preventDefault();
              }
          });
      });
    </script>
    %end
  </p>
%end

<meta name="ubus-session" content="{{ ubus_session }}">
<meta name="ubus-ready" content="{{ ubus_ready }}">

<script>
    var ws;

    var process_ca_gen = function(data) {
      if (data.ca != "openvpn") {
        // we are interrested only in openvpn ca
        return;
      }
      switch (data.action) {
        case "revoke":
        case "gen_client":
          renew_clients();
          return;
        case "gen_server":
        case "gen_dh":
        case "gen_ca":
          // reload current window
          window.location.reload();
          return;
      };
    };

    var renew_clients = function() {
      $.get('{{ url("config_ajax", page_name="openvpn") }}', {action: "update-clients"})
        .done(function(response, status, xhr) {
          if (xhr.status == 200) {
            // Redraw
            $("#openvpn-clients").replaceWith(response);
          } else {
            // Logout or other
            window.location.reload();
          }
        })
        .fail(function(xhr) {
            if (xhr.responseJSON && xhr.responseJSON.loggedOut && xhr.responseJSON.loginUrl) {
                window.location.replace(xhr.responseJSON.loginUrl);
                return;
            }
        });
    };

    $(document).ready(function() {
      var protocol = window.location.protocol == "http:" ? "ws:" : "wss:";
      var port = window.location.protocol == "http:" ? "9080" : "9443";
      var token = $("meta[name=ubus-session]").attr("content");
      var url = protocol + "//" + window.location.hostname + ":" + port + "/" + token;

      // Connect to Web Socket
      ws = new WebSocket(url);

      // Set event handlers.
      ws.onopen = function() {
      // register for lookup
        ws.send(JSON.stringify({"action": "register", "params": {"kinds": ["ca-gen"]}}));
      };

      ws.onmessage = function(e) {
        console.log("onmessage: " + e.data);
        var parsed = JSON.parse(e.data);
        if (parsed['ca-gen']) {
          // perform appropriate action
          process_ca_gen(parsed['ca-gen']);
        };
      };

      ws.onclose = function() {
        // TDB WS closed
        console.log("Disconnected from websocket server.");
      };

      ws.onerror = function(e) {
        // TDW WS error
        console.log("Websocket server error occured:" + e);
      };
    });
</script>

</div>
