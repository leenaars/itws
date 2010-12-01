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
from itools.core import merge_dicts, thingy_property
from itools.database import PhraseQuery, NotQuery, OrQuery, TextQuery, AndQuery
from itools.datatypes import Integer, String, Boolean
from itools.gettext import MSG

# Import from ikaaro
from ikaaro.folder_views import Folder_BrowseContent
from ikaaro.utils import get_base_path_query

###########################################
# See bug:
# http://bugs.hforge.org/show_bug.cgi?id=1100
###########################################

class Feed_View(Folder_BrowseContent):

    title = MSG(u'View')
    access = 'is_allowed_to_view'
    table_template = None

    # View configuration
    template = '/ui/feed_views/base_feed_view_div.xml'
    search_template = '/ui/folder/browse_search.xml'
    content_template = '/ui/feed_views/Tag_item_viewbox.xml'
    context_menus = []
    styles = []
    show_first_batch = False
    show_second_batch = True
    show_title = True
    batch_size = 25
    sort_by = 'title'
    reverse = False
    search_on_current_folder = True
    content_keys = ('pub_datetime', 'title', 'long_title',
                    'link', 'preview', 'tags',
                    'image', 'css', 'class_icon16', 'type', 'abspath')


    def get_query_schema(self):
        """ We allow to define 2 variable (sort_by and batch_size)"""
        return merge_dicts(Folder_BrowseContent.get_query_schema(self),
                batch_size=Integer(default=self.batch_size),
                sort_by=String(default=self.sort_by),
                reverse=Boolean(default=self.reverse))


    @thingy_property
    def table_template(self):
        return self.content_template


    # XXX to do in ikaaro
    def get_items(self, resource, context, *args):
        """ Same that Folder_BrowseContent but we allow to
            define var 'search_on_current_folder'"""
        # Query
        args = list(args)

        # Search only on current folder ?
        if self.search_on_current_folder is True:
            path = resource.get_canonical_path()
            query = get_base_path_query(str(path))
            args.append(query)
            # Exclude '/theme/'
            if resource.get_abspath() == '/':
                theme_path = path.resolve_name('theme')
                theme = get_base_path_query(str(theme_path), True)
                args.append(NotQuery(theme))

        # Filter by type
        search_type = context.query['search_type']
        if search_type:
            if ',' in search_type:
                search_type = search_type.split(',')
                search_type = [ PhraseQuery('format', x) for x in search_type ]
                search_type = OrQuery(*search_type)
            else:
                search_type = PhraseQuery('format', search_type)
            args.append(search_type)

        # Text search
        search_text = context.query['search_text'].strip()
        if search_text:
            args.append(OrQuery(TextQuery('title', search_text),
                                TextQuery('text', search_text),
                                PhraseQuery('name', search_text)))

        # Ok
        if len(args) == 1:
            query = args[0]
        else:
            query = AndQuery(*args)

        return context.root.search(query)

    ###############################################
    ## Namespace
    ###############################################

    def get_namespace(self, resource, context):
        namespace = Folder_BrowseContent.get_namespace(self, resource, context)
        namespace['id'] = 'section-%s' % resource.name
        namespace['css'] = self.view_name
        namespace['title'] = resource.get_property('title')
        namespace['show_title'] = self.show_title
        namespace['show_first_batch'] = self.show_first_batch
        namespace['show_second_batch'] = self.show_second_batch
        namespace['content'] = namespace['table']
        return namespace


    def get_table_namespace(self, resource, context, items):
        return self.get_content_namespace(resource, context, items)


    def get_content_namespace(self, resource, context, items):
        namespace = {'items': []}
        for item in items:
            kw = {}
            for key in self.content_keys:
                kw[key] = self.get_item_value(resource, context, item, key)
            namespace['items'].append(kw)
        return namespace


    def get_item_value(self, resource, context, item, column):
        item_brain, item_resource = item
        is_tags_aware = False# brain.is_tagsaware
        if column == 'class_icon16':
            return item_resource.get_class_icon()
        elif column == 'class_icon48':
            return item_resource.get_class_icon(size='48')
        elif column == 'pub_datetime':
            if is_tags_aware:
                return item_resource.get_pub_datetime_formatted()
            return None
        elif column == 'title':
            return item_resource.get_title()
        elif column == 'long_title':
            if is_tags_aware:
                return item_resource.get_long_title()
            return item_resource.get_title()
        elif column == 'link':
            return context.get_link(item_resource)
        elif column == 'abspath':
            site_root = item_resource.get_site_root()
            return '/%s' % site_root.get_pathto(item_resource)
        elif column == 'type':
            return item_resource.class_title.gettext()
        elif column == 'preview':
            if is_tags_aware:
                return item_brain.preview_content
            return item_resource.get_property('description')
        elif column == 'image':
            if is_tags_aware:
                thumbnail = item_resource.get_preview_thumbnail()
                if thumbnail:
                    return context.get_link(thumbnail)
            elif False:#item_brain.is_image: #XXX
                return context.get_link(item_resource)
            return None
        elif column == 'tags':
            if is_tags_aware:
                return item_resource.get_tags_namespace(context)
            return []
        elif column == 'css':
            # XXX performances (Use Lazy ?)
            current_path = resource.get_abspath()
            if item_resource.get_abspath() == current_path:
                return 'active'
            return None
        return Folder_BrowseContent.get_item_value(self, resource, context,
            item, column)