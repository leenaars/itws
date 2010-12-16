# -*- coding: UTF-8 -*-
# Copyright (C) 2010 Henry Obein <henry@itaapy.com>
# Copyright (C) 2010 Hervé Cauwelier <herve@itaapy.com>
# Copyright (C) 2010 Taverne Sylvain <sylvain@itaapy.com>
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
from urllib import quote

# Import from itools
from itools.core import freeze, merge_dicts
from itools.datatypes import Boolean, DateTime, String, Unicode
from itools.gettext import MSG
from itools.uri import get_reference

# Import from ikaaro
from ikaaro import messages
from ikaaro.autoform import TextWidget
from ikaaro.autoform import description_widget, subject_widget
from ikaaro.autoform import title_widget, timestamp_widget
from ikaaro.buttons import RemoveButton, RenameButton, PublishButton
from ikaaro.buttons import RetireButton, CopyButton, CutButton, PasteButton
from ikaaro.datatypes import Multilingual
from ikaaro.file import File
from ikaaro.folder import Folder
from ikaaro.folder_views import Folder_BrowseContent, GoToSpecificDocument
from ikaaro.folder_views import Folder_NewResource as BaseFolder_NewResource
from ikaaro.registry import get_resource_class
from ikaaro.resource_views import DBResource_Edit, EditLanguageMenu
from ikaaro.utils import get_content_containers
from ikaaro.views_new import NewInstance



############################################################
# NewInstance
############################################################

class EasyNewInstance(NewInstance):
    """ ikaaro.views_new.NewInstance without field name.
    """

    query_schema = freeze({'type': String, 'title': Unicode})
    widgets = freeze([
        TextWidget('title', title=MSG(u'Title', mandatory=True))])

    goto_method = None

    def get_new_resource_name(self, form):
        # As we have no name, always return the title
        title = form['title'].strip()
        return title


    def _get_goto_method(self, resource, context, form):
        return self.goto_method


    def _get_goto(self, resource, context, form):
        name = form['name']
        goto_method = self._get_goto_method(resource, context, form)
        if goto_method:
            return './%s/;%s' % (name, goto_method)
        return './%s/' % name


    def action_default(self, resource, context, form):
        name = form['name']
        title = form['title']

        # Create the resource
        class_id = context.query['type']
        cls = get_resource_class(class_id)
        child = cls.make_resource(cls, resource, name)
        # The metadata
        metadata = child.metadata
        language = resource.get_content_language(context)
        metadata.set_property('title', title, language=language)

        goto = self._get_goto(resource, context, form)
        return context.come_back(messages.MSG_NEW_RESOURCE, goto=goto)



############################################################
# GoToSpecificItem
############################################################

class AdvanceGoToSpecificDocument(GoToSpecificDocument):

    title = MSG(u'View')
    keep_query = False
    keep_message = False

    def GET(self, resource, context):
        specific_document = self.get_specific_document(resource, context)
        specific_view = self.get_specific_view(resource, context)
        goto = '%s/%s' % (context.get_link(resource), specific_document)
        if specific_view:
            goto = '%s/;%s' % (goto, specific_view)
        goto = get_reference(goto)

        # Keep the query
        if self.keep_query and context.uri.query:
            goto.query = context.uri.query.copy()

        # Keep the message
        if self.keep_message:
            message = context.get_form_value('message')
            if message:
                goto = goto.replace(message=message)

        return goto



############################################################
# Manage Content
############################################################

class BaseManageContent(Folder_BrowseContent):

    access = 'is_allowed_to_edit'

    search_template = None

    table_actions = [
        RemoveButton, RenameButton, CopyButton, CutButton, PasteButton,
        PublishButton, RetireButton]

    table_columns = [
        ('checkbox', None),
        ('icon', None),
        ('name', MSG(u'Name')),
        ('title', MSG(u'Title')),
        ('format', MSG(u'Format')),
        ('mtime', MSG(u'Last Modified')),
        ('workflow_state', MSG(u'State')),
        ]

    def get_query_schema(self):
        return merge_dicts(Folder_BrowseContent.get_query_schema(self),
                           sort_by=String(default='mtime'),
                           reverse=Boolean(default=True))


    def get_items(self, resource, context, *args):
        return Folder_BrowseContent.get_items(self, resource, context, *args)


    def get_item_value(self, resource, context, item, column):
        brain, item_resource = item
        if column == 'name':
            return brain.name, context.get_link(item_resource)
        return Folder_BrowseContent.get_item_value(self, resource,
                  context, item, column)



############################################################
# AutomaticEditView
############################################################

class AutomaticEditView(DBResource_Edit):

    base_schema = {'title': Multilingual,
                   'timestamp': DateTime(readonly=True, ignore=True)}

    # Add timestamp_widget in get_widgets method
    base_widgets = [title_widget]


    def _get_query_to_keep(self, resource, context):
        """Forward is_admin_popup if defined"""
        to_keep = DBResource_Edit._get_query_to_keep(self, resource, context)
        is_admin_popup = context.get_query_value('is_admin_popup')
        if is_admin_popup:
            to_keep.append({'name': 'is_admin_popup', 'value': '1'})
        return to_keep


    def _get_schema(self, resource, context):
        schema = {}
        if getattr(resource, 'edit_show_meta', False) is True:
            schema['description'] = Unicode(multilingual=True)
            schema['subject'] = Unicode(multilingual=True)
        schema = merge_dicts(self.base_schema, schema, resource.edit_schema)
        # FIXME Hide/Show title
        if getattr(resource, 'display_title', True) is False:
            del schema['title']
        return schema


    def _get_widgets(self, resource, context):
        widgets = []
        if getattr(resource, 'edit_show_meta', False) is True:
            widgets.extend([description_widget, subject_widget])
        widgets = self.base_widgets + widgets + resource.edit_widgets
        # Add timestamp_widget
        widgets.append(timestamp_widget)
        # FIXME Hide/Show title
        if getattr(resource, 'display_title', True) is False:
            to_remove = [ w for w in widgets if w.name == 'title' ]
            if to_remove:
                widgets.remove(to_remove[0])
        return widgets


    def get_value(self, resource, context, name, datatype):
        if name == 'state':
            return resource.get_workflow_state()
        return DBResource_Edit.get_value(self, resource, context, name,
                                         datatype)



############################################################
# EditLanguageMenu (Only language selection)
############################################################

class EditOnlyLanguageMenu(EditLanguageMenu):
    """Only display form to select language
    fields selection are not displayed
    """

    def get_fields(self):
        return []



############################################################
# NEW RESOURCE VIEWS
############################################################

class Folder_NewResource(BaseFolder_NewResource):

    def get_document_types(self, resource, context):
        from webpage import WebPage
        from bar import Section

        return [ WebPage, Section, File ]


    def get_namespace(self, resource, context):
        # 1. Find out the resource classes we can add
        document_types = self.get_document_types(resource, context)

        # 2. Build the namespace
        items = [
            {'icon': '/ui/' + cls.class_icon48,
             'title': cls.class_title.gettext(),
             'description': cls.class_description.gettext(),
             'url': ';new_resource?type=%s' % quote(cls.class_id)}
            for cls in document_types ]

        return {
            'batch': None,
            'items': items}



class Folder_AdvanceNewResource(Folder_NewResource):

    def get_document_types(self, resource, context):
        base_type = Folder.new_resource.get_document_types(resource, context)

        document_types = []
        skip_formats = set()
        for resource in get_content_containers(context, skip_formats):
            skip_formats.add(resource.class_id)
            for cls in resource.get_document_types():
                if cls in base_type:
                    continue
                if cls not in document_types:
                    document_types.append(cls)
        return document_types



# Monkey patch
Folder.new_resource = Folder_NewResource()
Folder.advance_new_resource = Folder_AdvanceNewResource()
