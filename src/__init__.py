# Foris - web administration interface for OpenWrt based on NETCONF
# Copyright (C) 2017 CZ.NIC, z. s. p. o. <https://www.nic.cz>
#
# Foris is distributed under the terms of GNU General Public License v3.
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import os

import bottle

from foris.core import gettext_dummy as gettext, ugettext as _
from foris.fapi import ForisForm
from foris.form import Checkbox, Textbox
from foris.plugins import ForisPlugin
from foris.config import ConfigPageMixin, add_config_page
from foris.config_handlers import BaseConfigHandler
from foris.utils import messages, reverse
from foris.validators import IPv4Prefix, LenRange, RegExp
from .nuci import openvpn
from .utils import prefix_to_mask_4
from .ubus import create_session, grant_listen

from .nuci import (
    delete_ca, generate_ca, generate_client, get_client_config, get_openvpn_ca, revoke_client,
    update_configs,
)


class OpenvpnConfigHandler(BaseConfigHandler):
    userfriendly_title = gettext("OpenVPN")

    def get_form(self):

        form = ForisForm(
            "openvpn-configuration", self.data, filter=openvpn.Config.openvpn_filter())
        config_section = form.add_section(name="config", title=_(self.userfriendly_title))
        config_section.add_field(
            Checkbox, name="enabled", label=_("Configuration enabled"),
            nuci_preproc=openvpn.Config.enabled_preproc
        )
        config_section.add_field(
            Textbox, name="network", label=_("OpenVPN network"),
            nuci_preproc=openvpn.Config.network_preproc,
            validators=[IPv4Prefix()],
            hint=_(
                "This network should be different than any network directly "
                "reachable from the router and the clients."
            ),
        )

        def form_callback(data):
            enabled = data['enabled']
            network, prefix = data['network'].split("/")
            mask = prefix_to_mask_4(int(prefix))

            if enabled:
                # get ca status
                ca = get_openvpn_ca()
                if not ca or not ca.ca_ready:
                    messages.error(_("Can't apply the configuration. Certificates are missing."))
                    # ca is missing or generating, can't apply the configuration
                    return "none", None
                # when ca is ready it should contain at least one server certicate
                cert_path, key_path = ca.get_paths('server')[0]
                paths = dict(cert_path=cert_path, key_path=key_path)
            else:
                paths = dict()  # use default paths

            if update_configs(enabled, network, mask, **paths):
                messages.success(
                    _('OpenVPN server configuration was successfully %s.') % (
                        _('enabled') if enabled else _('disabled')
                    )
                )
            else:
                messages.error(
                    _('Failed to %s OpenVPN server configuration.') % (
                        _('enable') if enabled else _('disable')
                    )
                )

            return "none", None

        form.add_callback(form_callback)
        return form


class OpenvpnConfigPage(ConfigPageMixin, OpenvpnConfigHandler):
    template = "openvpn/openvpn.tpl"

    def _prepare_render_args(self, arguments, client_form=None, ca=None):
        """ Prepare the arguments for the template.
        :param arguments: target variable
        :type arguments: dict
        """
        arguments['PLUGIN_NAME'] = OpenvpnPlugin.PLUGIN_NAME
        arguments['PLUGIN_STYLES'] = OpenvpnPlugin.PLUGIN_STYLES
        arguments['ca'] = ca if ca else get_openvpn_ca()
        arguments['config_form'] = self.form
        arguments['client_form'] = client_form if client_form else self.get_client_form()
        arguments['client_certs'] = [
            e for e in arguments['ca'].data.get('certs', []) if e['type'] == 'client'
        ] if arguments['ca'] else []

        # set the session for ubus
        session = create_session() or ""
        granted = grant_listen(session)
        arguments['ubus_session'] = session
        arguments['ubus_ready'] = granted

        # prepare current settings to display
        current = {}
        if self.form.data['enabled']:
            current['network'] = openvpn.Config.network_preproc(self.form.nuci_config)
            current['device'] = self.form.nuci_config.find_child(
                'uci.openvpn.server_turris.dev').value
            current['protocol'] = self.form.nuci_config.find_child(
                'uci.openvpn.server_turris.proto').value
            current['port'] = self.form.nuci_config.find_child(
                'uci.openvpn.server_turris.port').value
            arguments['current'] = current

    def _action_download_config_or_revoke(self):
        if 'revoke-client' in self.data:
            return self._action_revoke()
        elif 'download-config' in self.data:
            return self._action_download_config()
        raise bottle.HTTPError(404, "Invalid action.")

    def _action_revoke(self):
        """Handle POST requesting revoking client certificate config

        :return: response with token with appropriate HTTP headers
        """
        if revoke_client(self.data['revoke-client']):
            messages.success(_("The client certificate was successfully revoked."))
        else:
            messages.error(_("Failed to revoke the client certificate."))
        return bottle.redirect(reverse("config_page", page_name="openvpn"))

    def _action_download_config(self):
        """Handle POST requesting download of the openvpn client config

        :return: response with token with appropriate HTTP headers
        """
        openvpn_config = get_client_config(self.data['download-config'])
        if not openvpn_config:
            messages.error(_("Unable to get OpenVPN client config."))
            bottle.redirect(reverse("config_page", page_name="openvpn"))

        bottle.response.set_header("Content-Type", "text/plain")
        # TODO .ovpn for windows
        bottle.response.set_header("Content-Disposition", 'attachment; filename="turris.conf"')
        bottle.response.set_header("Content-Length", len(openvpn_config))
        return openvpn_config

    def _action_generate_ca(self):
        """Call RPC to generate CA for openvpn server

        :return: redirect to plugin's main page
        """
        if generate_ca():
            messages.success(_("Started to generate CA for the OpenVPN server."))
        else:
            messages.error(_("Failed to generate CA for the OpenVPN server."))

        return bottle.redirect(reverse("config_page", page_name="openvpn"))

    def _action_generate_client(self):
        """Call RPC to generate a client for openvpn server

        :return: redirect to plugin's main page
        """
        form = self.get_client_form(bottle.request.POST)
        if form.save():
            messages.success(_("Started to generate client certificate for the OpenVPN server."))
            return bottle.redirect(reverse("config_page", page_name="openvpn"))
        else:
            kwargs = {}
            self._prepare_render_args(kwargs, client_form=form)
            return super(OpenvpnConfigPage, self).render(**kwargs)

    def _action_delete_ca(self):
        """Call RPC to delete the CA of the openvpn server

        :return: redirect to plugin's main page
        """
        if delete_ca():
            messages.success(_("The OpenVPN CA was successfully deleted."))
        else:
            messages.success(_("Failed to detete the OpenVPN CA."))

        return bottle.redirect(reverse("config_page", page_name="openvpn"))

    def call_action(self, action):
        if bottle.request.method != 'POST':
            # all actions here require POST
            messages.error("Wrong HTTP method.")
            bottle.redirect(reverse("config_page", page_name="openvpn"))
        if action == "download-config":
            return self._action_download_config_or_revoke()
        elif action == "generate-ca":
            return self._action_generate_ca()
        elif action == "generate-client":
            return self._action_generate_client()
        elif action == "delete-ca":
            return self._action_delete_ca()
        raise bottle.HTTPError(404, "Unknown action.")

    def call_ajax_action(self, action):
        if action == "update-clients":
            bottle.response.set_header("Content-Type", "text/html")
            ca = get_openvpn_ca()
            client_certs = [
                e for e in ca.data.get('certs', []) if e['type'] == 'client'
            ] if ca else []
            return bottle.template("openvpn/_clients", client_certs=client_certs)
        raise ValueError("Unknown AJAX action.")

    def get_client_form(self, data=None):
        client_form = ForisForm("openvpn", data)
        main_section = client_form.add_section(
            name="name", title=None,
        )
        main_section.add_field(
            Textbox, name="client_name", label=_("Client name"), required=True,
            hint=_("The display name for the client. It must be shorter than 64 characters "
                   "and must contain only alphanumeric characters, dots, dashes and "
                   "underscores."),
            validators=[
                RegExp(_("Client name is invalid."), r'[a-zA-Z0-9_.-]+'), LenRange(1, 63)]
        )

        def form_callback(data):
            if generate_client(data['client_name']):
                messages.success(
                    _("Started to generate client '%(name)s' for the OpenVPN server.")
                    % dict(name=data['client_name'])
                )
            else:
                messages.error(
                    _("Failed to generate client '%s(name)s' for the OpenVPN server.")
                    % dict(name=data['client_name'])
                )
            return bottle.redirect(reverse("config_page", page_name="openvpn"))

        client_form.add_callback(form_callback)
        return client_form

    def render(self, **kwargs):
        self._prepare_render_args(kwargs)
        return super(OpenvpnConfigPage, self).render(**kwargs)

    def save(self, *args, **kwargs):
        kwargs['no_messages'] = True  # handle messages in methods of OpenvpnConfigPage
        return super(OpenvpnConfigPage, self).save(*args, **kwargs)


class OpenvpnPlugin(ForisPlugin):
    PLUGIN_NAME = "openvpn"
    DIRNAME = os.path.dirname(os.path.abspath(__file__))
    PLUGIN_STYLES = [
        "css/screen.css",
    ]

    def __init__(self, app):
        super(OpenvpnPlugin, self).__init__(app)
        add_config_page("openvpn", OpenvpnConfigPage, top_level=True)
