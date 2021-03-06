# -*- coding: UTF-8 -*-
# Copyright (C) 2008, 2010 Nicolas Deram <nicolas@itaapy.com>
# Copyright (C) 2008-2011 Henry Obein <henry@itaapy.com>
# Copyright (C) 2010 Taverne Sylvain <sylvain@itaapy.com>
# Copyright (C) 2010-2011 Hervé Cauwelier <herve@itaapy.com>
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

# Import from standard Library
from math import ceil
from random import shuffle

# Import from itools
from itools.core import freeze
from itools.datatypes import String
from itools.gettext import MSG
from itools.html import stream_to_str_as_xhtml
from itools.stl import set_prefix
from itools.uri import encode_query
from itools.web import get_context, STLView
from itools.database import AndQuery, PhraseQuery

# Import from ikaaro
from ikaaro.file_views import File_Edit
from ikaaro.folder_views import Folder_BrowseContent
from ikaaro.autoform import title_widget, description_widget, subject_widget
from ikaaro.autoform import timestamp_widget
from ikaaro.workflow import state_widget

# Import from itws
from itws.feed_views import Details_View
from itws.rss import BaseRSS
from itws.utils import is_navigation_mode



class Tag_Edit(File_Edit):

    widgets = freeze([
        timestamp_widget, title_widget, state_widget,
        description_widget, subject_widget])



############################################################
# Views
############################################################
class Tag_RSS(BaseRSS):
    """RSS export of a tag's results.
    """

    def get_base_query(self, resource, context):
        query = BaseRSS.get_base_query(self, resource, context)
        tags_query = resource.parent.get_tags_query_terms(state='public',
                tags=[resource.name])
        query.extend(tags_query)
        return query


    def get_item_value(self, resource, context, item, column, site_root):
        brain, item_resource = item
        if column == 'description':
            view = getattr(item_resource, 'tag_view',
                           getattr(item_resource, 'view'))
            if view:
                content = view.GET(item_resource, context)
                # set prefix
                prefix = site_root.get_pathto(item_resource)
                content = set_prefix(content, '%s/' % prefix, uri=context.uri)
                content = stream_to_str_as_xhtml(content)
                return content.decode('utf-8')
            else:
                return item_resource.get_property('description')

        return BaseRSS.get_item_value(self, resource, context, item,
                                      column, site_root)



class Tag_View(Details_View):

    # Configuration
    view_name = 'tag-view'
    batch_size = 20
    sort_by = 'pub_datetime'
    reverse = True
    search_on_current_folder = False
    search_on_current_folder_recursive = True
    # Display sidebar
    display_sidebar = True


    def get_items(self, resource, context, *args):
        # Build the query
        args = list(args)
        tag = resource.name
        get_query_value = context.get_query_value
        formats = get_query_value('format', type=String(multiple=True),
                                  default=[])
        query = resource.parent.get_tags_query_terms(tags=[tag],
                formats=formats)
        args.append(AndQuery(*query))
        return Details_View.get_items(self, resource, context, *args)



class TagsFolder_TagCloud(STLView):
    """Public view of the tags folder.
    """
    title = MSG(u'Tag Cloud Preview')
    access = 'is_allowed_to_view'
    template = '/ui/common/Tags_tagcloud.xml'

    formats = []
    show_number = False
    random_tags = False
    tags_to_show = 0
    show_description = True
    # Css class from tag-1 to tag-css_index_max
    css_index_max = 5


    def _get_tags_folder(self, resource, context):
        return resource


    def get_namespace(self, resource, context):
        tags_folder = self._get_tags_folder(resource, context)

        # description (help text)
        bo_description = False
        ac = tags_folder.get_access_control()
        if ac.is_allowed_to_edit(context.user, tags_folder):
            if is_navigation_mode(context) is False and \
                    self.show_description and \
                    type(context.resource) is type(tags_folder):
                bo_description = True

        tag_brains = tags_folder.get_tag_brains(context, states=[])
        tag_base_link = '%s/%%s' % context.get_link(tags_folder)
        if self.formats:
            query = {'format': self.formats}
            tag_base_link = '%s?%s' % (tag_base_link, encode_query(query))

        # query
        root = context.root
        tags_query = tags_folder.get_tags_query_terms(formats=self.formats)
        tags_results = root.search(AndQuery(*tags_query))

        items_nb = []
        tags = []
        ac = tags_folder.get_access_control()
        for brain in tag_brains:
            # Check ACL
            # FIXME To improve, use catalog instead resource
            tag = tags_folder.get_resource(brain.name)
            if ac.is_allowed_to_view(context.user, tag) is False:
                continue
            if self.tags_to_show and len(items_nb) == self.tags_to_show:
                break
            sub_results = tags_results.search(PhraseQuery('tags', brain.name))
            nb_items = len(sub_results)
            if nb_items:
                d = {}
                title = brain.title or brain.name
                if self.show_number:
                    title = u'%s (%s)' % (title, nb_items)
                d['title'] = title
                d['xml_title'] = title.replace(u' ', u'\u00A0')
                d['link'] = tag_base_link % brain.name
                d['css'] = None
                items_nb.append(nb_items)
                d['nb_items'] = nb_items
                tags.append(d)

        if not tags:
            return {'tags': [], 'bo_description': bo_description}

        max_items_nb = max(items_nb) if items_nb else 0
        min_items_nb = min(items_nb) if items_nb else 0

        css_index_max = self.css_index_max
        delta = (max_items_nb - min_items_nb) or 1
        percentage_per_item = float(css_index_max - 1) / delta

        # Special case of there is only one item
        default_css = 'tag-1'

        for tag in tags:
            if min_items_nb == max_items_nb:
                tag['css'] = default_css
            else:
                nb_items = tag['nb_items']
                css_index = int(ceil(nb_items) * percentage_per_item) or 1
                # FIXME sometimes css_index = 0, this should never append
                # set css_index to 1
                css_index = abs(css_index_max - css_index + 1) or 1
                tag['css'] = 'tag-%s' % css_index

        # Random
        if self.random_tags:
            shuffle(tags)

        return {'tags': tags, 'bo_description': bo_description}



class TagsFolder_BrowseContent(Folder_BrowseContent):
    """Browse content with preview of tagged items number. Used in the
    Tags_ManageView composite.
    """
    access = 'is_allowed_to_edit'

    # Table
    table_columns = [
        ('checkbox', None),
        ('name', MSG(u'Name')),
        ('title', MSG(u'Title')),
        ('items_nb', MSG(u'Items number')),
        ('mtime', MSG(u'Last Modified')),
        ('last_author', MSG(u'Last Author')),
        ('workflow_state', MSG(u'State'))]


    def _get_nb_resource_with_tag(self, resource, context, tag_name):
        # Build the search query
        query = resource.get_tags_query_terms()
        query.append(PhraseQuery('tags', tag_name))
        query = AndQuery(*query)

        # Search
        return len(context.root.search(query))


    def get_key_sorted_by_items_nb(self):
        def key(item):
            context = get_context()
            return self._get_nb_resource_with_tag(context.resource, context,
                                                  item.name)
        return key


    def get_item_value(self, resource, context, item, column):
        brain, item_resource = item
        if column == 'items_nb':
            nb = self._get_nb_resource_with_tag(resource, context, brain.name)
            return nb, './%s' % brain.name
        elif column == 'name':
            return brain.name

        return Folder_BrowseContent.get_item_value(self, resource, context,
                                                   item, column)
