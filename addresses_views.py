# -*- coding: UTF-8 -*-
# Copyright (C) 2009 Hervé Cauwelier <herve@itaapy.com>
# Copyright (C) 2009 J. David Ibanez <jdavid@itaapy.com>
# Copyright (C) 2009-2010 Henry Obein <henry@itaapy.com>
# Copyright (C) 2009-2010 Taverne Sylvain <sylvain@itaapy.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Import from itools
from itools.core import merge_dicts
from itools.datatypes import Decimal, Enumerate, Integer, String, Unicode
from itools.gettext import MSG
from itools.stl import set_prefix
from itools.web import STLView

# Import from ikaaro
from ikaaro.autoform import SelectWidget, TextWidget
from ikaaro.autoform import title_widget, rte_widget, timestamp_widget
from ikaaro.webpage import HTMLEditView
from ikaaro.workflow import get_workflow_preview

# Import from packages
from widgets import GoogleMapWidget, GoogleGPSWidget
from widgets import OpenStreetMapWidget, OpenStreetMapGPSWidget


class OpenLayerRender(Enumerate):

    options = [{'name': 'osm', 'value': MSG(u'Open Street Map')},
               {'name': 'google', 'value': MSG(u'Google Map')}]


class Addresses_View(STLView):

    access = True
    title = MSG(u'View')
    icon = 'view.png'
    template = '/ui/addresses/Addresses_view.xml'
    styles = ['/ui/addresses/style.css']

    def get_namespace(self, resource, context):
        from addresses import AddressItem

        ac = resource.get_access_control()
        user = context.user
        is_allowed_to_add = ac.is_allowed_to_add(user, resource)
        namespace = {'addresses': [],
                     'is_allowed_to_add': is_allowed_to_add}
        addresses = resource.search_resources(cls=AddressItem)
        for index, address in enumerate(addresses):
            # Check ACLs
            if ac.is_allowed_to_view(user, address) is False:
                continue
            kw = {}
            for key in ['latitude', 'longitude', 'zoom', 'width', 'height']:
                kw[key] = address.get_property(key)
            # FIXME To improve, render
            render = address.get_property('render')
            if render == 'google':
                map_widget_cls = GoogleMapWidget
            else:
                map_widget_cls = OpenStreetMapWidget
            map = map_widget_cls('map_%s' % index, **kw)
            is_allowed_to_edit = ac.is_allowed_to_edit(user, address)
            html_data = address.get_html_data()
            html_data = set_prefix(html_data, prefix='%s/' % address.name)
            an_address = {'name': address.name,
                          'title': address.get_title(),
                          'html': html_data,
                          'map': map.render(),
                          'is_allowed_to_edit': is_allowed_to_edit,
                          'workflow': get_workflow_preview(address, context),
                          }
            namespace['addresses'].append(an_address)
        return namespace



class AddressItem_Edit(HTMLEditView):

    access = 'is_allowed_to_edit'
    title = MSG(u"Edit address")
    submit_value = MSG(u'Edit address')


    def _get_schema(self, resource, context):
        return merge_dicts(HTMLEditView._get_schema(self, resource, context),
                           render=OpenLayerRender(mandatory=True),
                           width=Integer, height=Integer, address=Unicode,
                           latitude=Decimal, longitude=Decimal, zoom=Integer,
                           # Hack
                           gps=String)


    def get_widgets(self, resource, context):
        # What type of map ?
        if resource.get_property('render') == 'google':
            gps_widget_cls = GoogleGPSWidget
        else:
            gps_widget_cls = OpenStreetMapGPSWidget
        # Map configuration
        config_map = {'width': resource.get_property('width'),
                      'height': resource.get_property('height'),
                      'address': resource.get_property('address'),
                      'latitude': resource.get_property('latitude'),
                      'longitude': resource.get_property('longitude'),
                      'zoom': resource.get_property('zoom')}
        # Return widgets
        return [title_widget, rte_widget, timestamp_widget,
                SelectWidget('render', title=MSG(u'Render map with')),
                TextWidget('width', title=MSG(u'Map width'), size=6),
                TextWidget('height', title=MSG(u'Map height'), size=6),
                gps_widget_cls('gps', title=MSG(u'GPS'), resource=resource,
                              **config_map)]


    def action(self, resource, context, form):
        for key in ['zoom', 'latitude', 'longitude', 'address',
                    'width', 'height', 'render']:
            resource.set_property(key, form[key])
        return HTMLEditView.action(self, resource, context, form)
