# -*- coding: UTF-8 -*-
# Copyright (C) 2010 Sylvain Taverne <sylvain@itaapy.com>
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
from itools.gettext import MSG

# Import from ikaaro
from ikaaro.folder import Folder
from ikaaro.folder_views import Folder_BrowseContent

# Import from itws
from base import Feed_View


class Browse_Navigator(Feed_View):

    access = 'is_allowed_to_edit'
    search_template = None
    batch_size = 25
    sort_by = 'mtime'

    template = '/ui/feed_views/base_feed_view_div.xml'
    content_template = '/ui/feed_views/browse_navigator.xml'

    search_on_current_folder = True
    ignore_internal_resources = True

    table_columns = [
        ('checkbox', None),
        ('icon', None),
        ('title', MSG(u'Title')),
        ('format', MSG(u'Type')),
        ('mtime', MSG(u'Last Modified')),
        ('last_author', MSG(u'Last Author')),
        ('workflow_state', MSG(u'State'))]


    def get_content_namespace(self, resource, context, items):
        # Get namespace
        namespace = Folder_BrowseContent.get_table_namespace(self,
                        resource, context, items)
        # The breadcrumb
        breadcrumb = []
        node = resource
        while node != context.root:
            if node.has_property('breadcrumb_title'):
                title = node.get_property('breadcrumb_title')
            else:
                title = node.get_title()
            link = context.get_link(node)
            breadcrumb.insert(0, {'name': node.name,
                                  'title': title,
                                  'url':  link})
            node = node.parent
        namespace['breadcrumb'] = breadcrumb
        return namespace


    def get_item_value(self, resource, context, item, column):
        item_brain, item_resource = item
        if column == 'title':
            title = item_resource.get_title()
            link = context.get_link(item_resource)
            if isinstance(item_resource, Folder):
                link += '/;manage_content'
            return (title, link)
        return Feed_View.get_item_value(self, resource, context, item, column)