# Foris - web administration interface for OpenWrt based on NETCONF
# Copyright (C) 2016 CZ.NIC, z. s. p. o. <https://www.nic.cz>
#
# Foris is distributed under the terms of GNU General Public License v3.
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import os

import bottle

from foris.core import gettext_dummy as gettext, ugettext as _
from foris.fapi import ForisForm
from foris.form import Checkbox
from foris.plugins import ForisPlugin
from foris.config import ConfigPageMixin, add_config_page
from foris.config_handlers import BaseConfigHandler
from foris.utils import messages, reverse
from .nuci import openvpn

from .nuci import (
    generate_ca, get_client_config, get_openvpn_ca, update_configs
)


class OpenvpnConfigHandler(BaseConfigHandler):
    userfriendly_title = gettext("Openvpn")

    def get_form(self):

        form = ForisForm(
            "openvpn-configuration", self.data, filter=openvpn.Config.openvpn_filter())
        config_section = form.add_section(name="config", title=_(self.userfriendly_title))
        config_section.add_field(
            Checkbox, name="enabled", label=_("Configuration enabled"),
            nuci_preproc=openvpn.Config.enabled_preproc
        )

        def form_callback(data):
            enabled = data['enabled']
            if update_configs(enabled):
                # get openvpn server config
                ca = get_openvpn_ca()
                if not ca or ca.missing or ca.generating:
                    messages.error(_("Can't apply the configuration. Certificates are missing."))
                    # ca is missing or generating, can't apply the configuration
                else:
                    messages.success(
                        _('Openvpn server configuration was successfully %s.') % (
                            _('enabled') if enabled else 'disabled'
                        )
                    )
            else:
                messages.error(
                    _('Failed to %s openvpn configuration.') % (
                        _('enable') if enabled else 'disable'
                    )
                )
            return "none", None

        form.add_callback(form_callback)
        return form


class OpenvpnConfigPage(ConfigPageMixin, OpenvpnConfigHandler):
    template = "openvpn/openvpn.tpl"

    def _action_download_config(self):
        """Handle POST requesting download of the openvpn client config

        :return: response with token with appropriate HTTP headers
        """
        openvpn_config = get_client_config()
        if not openvpn_config:
            messages.error(_("Unable to get openvpn client config."))
            bottle.redirect(reverse("config_page", page_name="openvpn"))

        bottle.response.set_header("Content-Type", "text/plain")
        # TODO .ovpn for windows
        bottle.response.set_header("Content-Disposition", 'attachment; filename="turris.conf')
        bottle.response.set_header("Content-Length", len(openvpn_config))
        return openvpn_config

    def _action_generate_ca(self):
        """Call RPC to generate CA for openvpn server

        :return: redirect to plugin's main page
        """
        if generate_ca():
            messages.success(_("Started to generate certificates for the openvpn server."))
        else:
            messages.error(_("Failed to generate certificates for the openvpn server."))

        return bottle.redirect(reverse("config_page", page_name="openvpn"))

    def _action_update_configuration(self):
        # get openvpn server config
        ca = get_openvpn_ca()

        if not ca or ca.missing or ca.generating:
            messages.error(_("Can't apply the configuration. Certificates are missing."))
            # ca is missing or generating, can't apply the configuration
        else:
            enabled = True if bottle.request.POST.get('enabled') == "1" else False
            if update_configs(enabled):
                messages.success(
                    _('Openvpn server configuration was successfully %s.') % (
                        _('enabled') if enabled else 'disabled'
                    )
                )
            else:
                messages.success(
                    _('Failed to %s openvpn configuration.') % (
                        _('enable') if enabled else 'disable'
                    )
                )

        return bottle.redirect(reverse("config_page", page_name="openvpn"))

    def call_action(self, action):
        if bottle.request.method != 'POST':
            # all actions here require POST
            messages.error("Wrong HTTP method.")
            bottle.redirect(reverse("config_page", page_name="openvpn"))
        if action == "download-config":
            return self._action_download_config()
        elif action == "generate-ca":
            return self._action_generate_ca()
        elif action == "update-configuration":
            return self._action_update_configuration()
        raise bottle.HTTPError(404, "Unknown action.")

    def render(self, **kwargs):
        kwargs['PLUGIN_NAME'] = OpenvpnPlugin.PLUGIN_NAME
        kwargs['PLUGIN_STYLES'] = OpenvpnPlugin.PLUGIN_STYLES
        kwargs['ca'] = get_openvpn_ca()
        kwargs['config_form'] = self.form
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
