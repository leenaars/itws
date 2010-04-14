# -*- coding: UTF-8 -*-
# Copyright (C) 2010 Henry Obein <henry@itaapy.com>
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

# Import from the Standard Library
from random import choice

# Import from itools
from itools.core import merge_dicts
from itools.datatypes import Unicode, Integer, Boolean
from itools.gettext import MSG
from itools.stl import set_prefix
from itools.web import STLView

# Import from ikaaro
from ikaaro.forms import BooleanCheckBox
from ikaaro.forms import XHTMLBody, HTMLBody
from ikaaro.table import OrderedTable_View
from ikaaro.table import Table_EditRecord

# Import from itws
from diaporama_views import Diaporama_Edit
from utils import get_admin_bar



class TurningFooterFile_View(OrderedTable_View):

    schema = {
        'ids': Integer(multiple=True, mandatory=True),
    }

    def get_table_columns(self, resource, context):
        columns = [
            ('checkbox', None),
            ('id', MSG(u'id'))]
        # From the schema
        for widget in self.get_widgets(resource, context):
            column = (widget.name, getattr(widget, 'title', widget.name))
            columns.append(column)
        return columns


    def get_item_value(self, resource, context, item, column):
        value = OrderedTable_View.get_item_value(self, resource, context,
                                                 item, column)
        if column == 'data':
            return XHTMLBody.decode(Unicode.encode(value))
        return OrderedTable_View.get_item_value(self, resource, context, item,
                                                column)



class TurningFooterFile_EditRecord(Table_EditRecord):

    def get_value(self, resource, context, name, datatype):
        if name == 'data':
            handler = resource.get_handler()
            id = context.query['id']
            record = handler.get_record(id)
            language = resource.get_content_language(context)
            value = handler.get_record_value(record, name, language=language)
            # HTML for Tiny MCE
            return HTMLBody.decode(value)
        return Table_EditRecord.get_value(self, resource, context, name,
                                          datatype)



class TurningFooterFolder_Edit(Diaporama_Edit):

    def get_schema(self, resource, context):
        schema = Diaporama_Edit.get_schema(self, resource, context)
        return merge_dicts(schema, random=Boolean, active=Boolean)


    def get_widgets(self, resource, context):
        widgets = Diaporama_Edit.get_widgets(self, resource, context)[:]
        # Random
        title = MSG(u'Random selection')
        widgets.insert(3, BooleanCheckBox('random', title=title))
        title = MSG(u'Is active')
        widgets.insert(3, BooleanCheckBox('active', title=title))

        return widgets


    def action(self, resource, context, form):
        Diaporama_Edit.action(self, resource, context, form)
        # Check edit conflict
        if context.edit_conflict:
            return
        resource.set_property('random', form['random'])
        resource.set_property('active', form['active'])



class TurningFooterFolder_View(STLView):

    access = 'is_allowed_to_edit'
    title = MSG(u'View')
    template = '/ui/common/TurningFooterFolder_view.xml'


    def get_manage_buttons(self, resource, context):
        resource_path = context.get_link(resource)
        table_path = '%s/%s' % (resource_path, resource.order_path)
        return [{'label': MSG(u'Edit the items'), 'path': table_path},
                {'label': MSG(u'Configure the footer'),
                 'path': '%s/;edit' % resource_path}]


    def get_namespace(self, resource, context):
        namespace = {}
        # Manage buttons and highlight
        highlight = None
        manage_buttons = []
        ac = resource.get_access_control()
        if ac.is_allowed_to_edit(context.user, resource):
            manage_buttons = self.get_manage_buttons(resource, context)
            highlight = 'highlight'
        admin_bar = get_admin_bar(manage_buttons, 'turning-footer',
                        title=MSG(u'Turning footer'))

        # title and title_image
        title = resource.get_title(fallback=False)
        title_image_path = resource.get_property('title_image')
        if title_image_path:
            # NOTE title image multilingual -> Unicode => String
            title_image = resource.get_resource(str(title_image_path),
                                                soft=True)
            if title_image:
                title_image_path = context.get_link(title_image)
                title_image_path = '%s/;download' % title_image_path

        is_active = resource.get_property('active')
        menu = resource.get_resource(resource.order_path)
        handler = menu.handler

        ids = list(handler.get_record_ids_in_order())
        if not ids or is_active is False:
            display = True if highlight else False
            return {'content': None,
                    'highlight': 'highlight-empty',
                    'admin_bar': admin_bar,
                    'title': title,
                    'title_image_path': title_image_path,
                    'display': display,
                    'is_active': is_active}

        if resource.get_property('random'):
            id = choice(ids)
        else:
            id = ids[0]

        record = handler.get_record(id)
        data = handler.get_record_value(record, 'data')
        data = Unicode.encode(data)
        data = XHTMLBody(sanitize_html=False).decode(data)
        here = context.resource
        content = set_prefix(data, prefix='%s/' % here.get_pathto(menu))
        return {'content': content,
                'highlight': highlight,
                'admin_bar': admin_bar,
                'title': title,
                'title_image_path': title_image_path,
                'display': True,
                'is_active': is_active}
