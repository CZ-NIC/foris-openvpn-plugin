%# Foris - web administration interface for OpenWrt based on NETCONF
%# Copyright (C) 2017 CZ.NIC, z. s. p. o. <https://www.nic.cz>
%#
%# Foris is distributed under the terms of GNU General Public License v3.
%# You should have received a copy of the GNU General Public License
%# along with this program.  If not, see <https://www.gnu.org/licenses/>.

    <table id="openvpn-clients">
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
        <tr id="serial-{{ cert["id"] }}-name-{{ cert["name"] }}">
          <td>{{ cert["name"] }}</td>
          %if cert['status'] == 'revoked':
            <td title="{{ trans(cert['status']) }}"><i class="fas fa-times"></td>
          %elif cert['status'] == 'generating':
            <td title="{{ trans(cert['status']) }}"><i class="fas fa-clock"></td>
          %elif cert['status'] == 'valid':
            <td title="{{ trans(cert['status']) }}"><i class="fas fa-check"></td>
          %else:
            <td>{{ trans(cert['status']) }}</td>
          %end
          <td>
            %if cert['status'] == 'valid':
            <button name="download-config" value="{{ cert["id"] }}" type="submit"><i class="fas fa-download"></i> {{ trans("Get Config") }}</button>
            %end
            %if cert['status'] not in ['revoked', 'generating']:
            <button name="revoke-client" value="{{ cert["id"] }}" type="submit"><i class="fas fa-times"></i> {{ trans("Revoke") }}</button>
            %end
          </td>
        </tr>
    %end
      </tbody>
    </table>
