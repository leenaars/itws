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

# Import from itools
from itools.core import merge_dicts
from itools.datatypes import Boolean
from itools.gettext import MSG
from itools.web import STLView

# Import from ikaaro
from ikaaro.forms import RTEWidget, BooleanCheckBox
from ikaaro.webpage import HTMLEditView, WebPage_View as BaseWebPage_View
from ikaaro.workflow import WorkflowAware

# Import from itws
from tags import TagsAware_Edit
from utils import get_admin_bar



class WebPage_Edit(HTMLEditView, TagsAware_Edit):

    def get_schema(self, resource, context):
        return merge_dicts(HTMLEditView.get_schema(self, resource, context),
                           TagsAware_Edit.get_schema(self, resource, context),
                           display_title=Boolean)


    def get_widgets(self, resource, context):
        widgets = HTMLEditView.get_widgets(self, resource, context)[:]
        display_title_widget = BooleanCheckBox('display_title',
                title=MSG(u'Display on webpage view'))
        widgets.insert(2, display_title_widget)
        widgets.extend(TagsAware_Edit.widgets)
        new_widgets = []
        eve = "iframe[src|name|id|class|style|frameborder|width|height]"
        for widget in widgets:
            if isinstance(widget, RTEWidget):
                toolbar2 = '%s,|,%s' % (widget.toolbar2, 'attribs')
                plugins = '%s,%s' % (widget.plugins, 'xhtmlxtras')
                new_widgets.append(RTEWidget('data', title=MSG(u'Body'),
                                   extended_valid_elements=eve,
                                   toolbar2=toolbar2, plugins=plugins))
            else:
                new_widgets.append(widget)

        return new_widgets


    def get_value(self, resource, context, name, datatype):
        if name == 'display_title':
            return resource.get_property('display_title')
        if name in TagsAware_Edit.get_schema(self, resource, context):
            # TODO To improve
            return TagsAware_Edit.get_value(self, resource, context, name,
                                           datatype)
        return HTMLEditView.get_value(self, resource, context, name, datatype)


    def action(self, resource, context, form):
        HTMLEditView.action(self, resource, context, form)
        TagsAware_Edit.action(self, resource, context, form)
        # Check edit conflict
        if context.edit_conflict:
            return
        display_title = form['display_title']
        resource.set_property('display_title', display_title)



class WebPage_View(BaseWebPage_View, STLView):

    template = '/ui/common/WebPage_view.xml'

    def GET(self, resource, context):
        return STLView.GET(self, resource, context)


    def get_manage_buttons(self, resource, context, name=None):
        manage_buttons = []
        ac = resource.get_access_control()
        if ac.is_allowed_to_edit(context.user, resource):
            resource_path = context.get_link(resource)
            if isinstance(resource, WorkflowAware):
                state = resource.get_state()
                new_button = {
                    'path': '%s/;edit_state' % resource_path,
                    'label': state['title'].gettext().encode('utf-8'),
                    'class': 'wf-%s' % resource.get_statename()}
                manage_buttons.append(new_button)
            new_button = {
                'path': '%s/;edit' % resource_path,
                'label': MSG(u'Edit content'),
                'class': None}
            manage_buttons.append(new_button)
        return manage_buttons


    def get_namespace(self, resource, context):
        title = resource.get_property('display_title')
        if title:
            title = resource.get_title()

        manage_buttons = []
        if context.user is not None:
            site_root = resource.get_site_root()
            repository = site_root.get_repository()
            # Show buttons only when outside of repository
            if context.resource != repository:
                manage_buttons = self.get_manage_buttons(resource, context)

        namespace = {}
        namespace['name'] = resource.name
        namespace['title'] = title
        namespace['content'] = BaseWebPage_View.GET(self, resource, context)
        namespace['admin_bar'] = get_admin_bar(manage_buttons,
                                      resource.name, MSG(u'A WebPage'))

        return namespace

