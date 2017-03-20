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

var WS = {
  handlers: {
    open: function() {
      // register for lookup
      ws.send(JSON.stringify({"action": "register", "params": {"kinds": ["ca-gen"]}}));
    },
    message: function(e) {
      console.log("message: " + e.data);
      var parsed = JSON.parse(e.data);
      if (parsed['ca-gen']) {
        // perform appropriate action
        process_ca_gen(parsed['ca-gen']);
      };
    },
    error: function(e) {
      // TDW WS error
      console.log("Websocket server error occured:" + e);
    },
    close: function() {
      // TDB WS closed
      console.log("Disconnected from websocket server.");
    }
  }
}


$(document).ready(function() {
  $('#delete-ca-form').on('click', function(e) {
    var answer = confirm("{{ trans("Are you sure you want to delete the OpenVPN CA?") }}");
    if (!answer) {
      e.preventDefault();
    }
  });
  $('#field-enabled_1').click(function () {
    if ($(this).prop('checked')) {
      $('#openvpn-config-form div:not(:first):not(:last)').show();
      $('.openvpn-config-current').show();
    } else {
      $('#openvpn-config-form div:not(:first):not(:last)').hide();
      $('.openvpn-config-current').hide();
    }
  });
  if ($('#field-enabled_1').is(':checked')) {
      $('#openvpn-config-form div:not(:first):not(:last)').show();
  } else {
      $('#openvpn-config-form div:not(:first):not(:last)').hide();
  };
});
