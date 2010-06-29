# -*- coding: UTF-8 -*-
# Copyright (C) 2008, 2010 Nicolas Deram <nicolas@itaapy.com>
# Copyright (C) 2008-2010 Henry Obein <henry@itaapy.com>
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

# Import from standard Library
from math import ceil
from random import shuffle

# Import from itools
from itools.datatypes import Enumerate
from itools.datatypes import String, Date
from itools.gettext import MSG
from itools.html import stream_to_str_as_xhtml
from itools.stl import set_prefix
from itools.uri import encode_query
from itools.web import STLView, get_context
from itools.xapian import AndQuery, PhraseQuery
from itools.xapian import RangeQuery, NotQuery, split_unicode

# Import from ikaaro
from ikaaro.buttons import Button
from ikaaro.folder_views import Folder_BrowseContent
from ikaaro.forms import DateWidget
from ikaaro.views import CompositeForm

# Import from itws
from utils import set_prefix_with_hostname, DualSelectWidget
from utils import is_navigation_mode
from views import BaseRSS, ProxyContainerNewInstance


class TagsList(Enumerate):

    site_root = None

    @staticmethod
    def decode(value):
        if not value:
            return None
        return str(value)


    @staticmethod
    def encode(value):
        if value is None:
            return ''
        return str(value)


    @classmethod
    def get_options(cls):
        tags_folder = cls.site_root.get_resource('tags')
        context = get_context()
        options = [ {'name': brain.name,
                     'value': brain.m_title or brain.name}
                    for brain in tags_folder.get_tag_brains(context) ]

        return options



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


    def get_if_modified_since_query(self, resource, context, if_modified_since):
        if not if_modified_since:
            return []
        return AndQuery(RangeQuery('date_of_writing', if_modified_since,
                                   None),
                        NotQuery(PhraseQuery('date_of_writing',
                                             if_modified_since)))


    def _sort_and_batch(self, resource, context, results):
        size = self.get_max_items_number(resource, context)
        items = results.get_documents(sort_by='date_of_writing',
                                      reverse=True, size=size)
        return items


    def get_excluded_container_paths(self, resource, context):
        site_root = resource.get_site_root()
        site_root_abspath = site_root.get_abspath()
        excluded = []
        for name in ('./menu/', './repository/', './ws-data/'):
            excluded.append(site_root_abspath.resolve2(name))
        return excluded


    def get_item_value(self, resource, context, item, column, site_root):
        brain, item_resource = item
        if column == 'pubDate':
            return brain.date_of_writing
        elif column == 'description':
            view = getattr(item_resource, 'tag_view',
                           getattr(item_resource, 'view'))
            if view:
                content = view.GET(item_resource, context)
                # set prefix
                prefix = site_root.get_pathto(item_resource)
                content = set_prefix_with_hostname(content, '%s/' % prefix,
                                                   uri=context.uri)
                content = stream_to_str_as_xhtml(content)
                return content.decode('utf-8')
            else:
                return item_resource.get_property('description')

        return BaseRSS.get_item_value(self, resource, context, item,
                                      column, site_root)



class TagItem_View(STLView):
    """Preview of the resource in a tag view.
    """
    access = 'is_allowed_to_view'
    template = '/ui/common/Tag_item_view.xml'

    def get_content(self, resource, context):
        return resource.get_html_data()


    def get_namespace(self, resource, context):
        title = resource.get_title()
        link = context.get_link(resource)
        content = self.get_content(resource, context)
        namespace =  {'title': title, 'link': link, 'content': content}
        return namespace



class Tag_View(STLView):
    """View of a tag.
    """
    title = MSG(u'View')
    access = 'is_allowed_to_view'
    template = '/ui/common/Tag_view.xml'
    query_schema = {'formats': String(default=[], multiple=True)}

    def get_namespace(self, resource, context):
        root = context.root
        here = context.resource # equal to resource
        tag = resource.name
        query = self.get_query(context)
        formats = query['formats']
        query = resource.parent.get_tags_query_terms(state='public',
                tags=[tag], formats=formats)
        results = root.search(AndQuery(*query))

        items = []
        for doc in results.get_documents(sort_by='date_of_writing',
                                         reverse=True):
            item = root.get_resource(doc.abspath)
            view = getattr(item, 'tag_view', getattr(item, 'view'))
            if view:
                content = view.GET(item, context)
                # set prefix
                prefix = here.get_pathto(item)
                content = set_prefix(content, '%s/' % prefix)
                items.append({'content': content, 'format': doc.format})

        tag_title = resource.get_title()
        return {'items': items, 'tag_title': tag_title}



class TagsFolder_TagCloud(STLView):
    """Public view of the tags folder.
    """
    title = MSG(u'Tag Cloud')
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
        namespace = {}
        tags_folder = self._get_tags_folder(resource, context)

        # description (help text)
        bo_description = False
        ac = tags_folder.get_access_control()
        if ac.is_allowed_to_edit(context.user, tags_folder):
            if is_navigation_mode(context) is False and \
                    self.show_description and \
                    type(context.resource) is type(tags_folder):
                bo_description = True

        tag_brains = tags_folder.get_tag_brains(context)
        tag_base_link = '%s/%%s' % context.get_link(tags_folder)
        if self.formats:
            query = {'formats': self.formats}
            tag_base_link = '%s?%s' % (tag_base_link, encode_query(query))

        # query
        root = context.root
        tags_query = tags_folder.get_tags_query_terms(state='public',
                                                      formats=self.formats)
        tags_results = root.search(AndQuery(*tags_query))

        items_nb = []
        tags = []
        for brain in tag_brains:
            if self.tags_to_show and len(items_nb) == self.tags_to_show:
                break
            sub_results = tags_results.search(PhraseQuery('tags', brain.name))
            nb_items = len(sub_results)
            if nb_items:
                d = {}
                title = brain.m_title or brain.name
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



class TagsAware_Edit(object):
    """Mixin to merge with the TagsAware edit view.
    """
    # Little optimisation not to compute the schema too often
    keys = ['tags', 'date_of_writing']


    def get_schema(self, resource, context):
        site_root = resource.get_site_root()
        return {'tags': TagsList(site_root=site_root, multiple=True),
                'date_of_writing': Date}


    def get_widgets(self, resource, context):
        return [DualSelectWidget('tags', title=MSG(u'TAGS'), is_inline=True,
            has_empty_option=False),
            DateWidget('date_of_writing', title=MSG(u'Date of writing'))]


    def get_value(self, resource, context, name, datatype):
        if name == 'tags':
            tags = resource.get_property('tags')
            # tuple -> list (enumerate.get_namespace expects list)
            return list(tags)
        elif name == 'date_of_writing':
            return resource.get_property('date_of_writing')


    def action(self, resource, context, form):
        resource.set_property('tags', form['tags'])
        resource.set_property('date_of_writing', form['date_of_writing'])



class TagsFolder_BrowseContent(Folder_BrowseContent):
    """Browse content with preview of tagged items number. Used in the
    Tags_ManageView composite.
    """
    # Table
    table_columns = [
        ('checkbox', None),
        ('name', MSG(u'Name')),
        ('title', MSG(u'Title')),
        ('items_nb', MSG(u'Items number')),
        ('mtime', MSG(u'Last Modified')),
        ('last_author', MSG(u'Last Author')),
        ('workflow_state', MSG(u'State'))]

    def get_items(self, resource, context, *args):
        # Get the parameters from the query
        query = context.query
        search_term = query['search_term'].strip()
        field = query['search_field']

        abspath = resource.get_abspath()
        query = [PhraseQuery('parent_path', str(abspath)),
                 PhraseQuery('format', resource.tag_class.class_id)]
        if search_term:
            language = resource.get_content_language(context)
            terms_query = [ PhraseQuery(field, term)
                            for term in split_unicode(search_term, language) ]
            query.append(AndQuery(*terms_query))
        query = AndQuery(*query)

        return context.root.search(query)


    def get_item_value(self, resource, context, item, column):
        brain, item_resource = item
        if column == 'items_nb':
            # Build the search query
            query = resource.get_tags_query_terms()
            query.append(PhraseQuery('tags', brain.name))
            query = AndQuery(*query)

            # Search
            results = context.root.search(query)
            return len(results), './%s' % brain.name

        return Folder_BrowseContent.get_item_value(self, resource, context,
                                                   item, column)



class TagsFolder_TagNewInstance(ProxyContainerNewInstance):
    """Simple form to create a tag. Used in the Tags_ManageView composite.
    """
    actions = [Button(access='is_allowed_to_edit',
                      name='new_tag', title=MSG(u'Add'))]

    def _get_resource_cls(self, resource, context):
        return resource.tag_class


    def _get_container(self, resource, context):
        return resource


    def _get_goto(self, resource, context, form):
        referrer = context.get_referrer()
        if referrer:
            return referrer
        return '.'


    def action_new_tag(self, resource, context, form):
        return ProxyContainerNewInstance.action_default(self, resource,
                context, form)



class Tags_ManageView(CompositeForm):
    """Create+browse form.
    """

    access = 'is_allowed_to_edit'
    title = MSG(u'Manage view')

    subviews = [ TagsFolder_TagNewInstance(),
                 TagsFolder_BrowseContent() ]


    def _get_form(self, resource, context):
        for view in self.subviews:
            method = getattr(view, context.form_action, None)
            if method is not None:
                form_method = getattr(view, '_get_form')
                return form_method(resource, context)
        return None