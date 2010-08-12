# -*- coding: UTF-8 -*-
# Copyright (C) 2010 Henry Obein <henry@itaapy.com>
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
from warnings import warn

# Import from itools
from itools.core import merge_dicts
from itools.datatypes import Integer, Enumerate
from itools.datatypes import String
from itools.gettext import MSG
from itools.stl import stl, set_prefix
from itools.uri import encode_query
from itools.web import BaseView, STLView
from itools.xapian import AndQuery, PhraseQuery
from itools.xml import XMLParser

# Import from ikaaro
from ikaaro.folder_views import Folder_BrowseContent, Folder_NewResource
from ikaaro.forms import SelectWidget, TextWidget
from ikaaro.forms import stl_namespaces
from ikaaro.future.order import ResourcesOrderedTable_Ordered
from ikaaro.views_new import AddResourceMenu
from ikaaro.webpage import WebPage_View
from ikaaro.website import WebSite

# Import from itws
from tags_views import TagsList
from utils import is_empty, to_box, DualSelectWidget
from views import SmartOrderedTable_Ordered, SmartOrderedTable_Unordered
from views import SmartOrderedTable_View, AutomaticEditView


################################################################################
# Repository views
################################################################################

class Repository_AddResourceMenu(AddResourceMenu):

    is_content = None
    is_side = None

    def __init__(self, **kw):
        for key in kw:
            setattr(self, key, kw[key])


    def get_items(self, resource, context):
        base = '%s/;new_resource' % context.get_link(resource)
        document_types = resource._get_document_types(
                allow_instanciation=True,
                is_content=self.is_content,
                is_side=self.is_side)
        return [
            {'src': '/ui/' + cls.class_icon16,
             'title': cls.class_title.gettext(),
             'href': '%s?type=%s' % (base, quote(cls.class_id))}
            for cls in document_types ]



class Repository_NewResource(Folder_NewResource):

    is_content = None
    is_side = None

    def get_namespace(self, resource, context):
        items = [
            {'icon': '/ui/' + cls.class_icon48,
             'title': cls.class_title.gettext(),
             'description': cls.class_description.gettext(),
             'url': ';new_resource?type=%s' % quote(cls.class_id)
            }
            for cls in resource._get_document_types(
                allow_instanciation=True,
                is_content=self.is_content,
                is_side=self.is_side) ]

        return {
            'batch': None,
            'items': items}



class Repository_BrowseContent(Folder_BrowseContent):

    query_schema = merge_dicts(Folder_BrowseContent.query_schema,
                               sort_by=String(default='format'))

    context_menus = [ Repository_AddResourceMenu(is_side=True,
                          title=MSG(u'Add Sidebar Box')),
                      Repository_AddResourceMenu(is_content=True,
                          title=MSG(u'Add Central Part Box'))]

    links_template = list(XMLParser("""
        <stl:block stl:repeat="item items">
            <a href="${item/path}" title="${item/title}">${item/name}</a>
            <span stl:if="not repeat/item/end">,</span>
        </stl:block>
        """, stl_namespaces))

    def get_table_columns(self, resource, context):
        columns = Folder_BrowseContent.get_table_columns(self, resource,
                                                         context)
        columns = list(columns) # create a new list
        columns.append(('links', MSG(u'Referenced by'), False))
        return columns


    def get_item_value(self, resource, context, item, column):
        if column == 'links':
            brain, item_resource = item
            root = context.root
            path = str(item_resource.get_canonical_path())
            results = root.search(links=path)
            if len(results) == 0:
                return 0
            links = []
            for index, doc in enumerate(results.get_documents()):
                links_resource = root.get_resource(doc.abspath)
                parent_resource = links_resource.parent
                # links_resource should be an ordered table
                links.append({'name': (index + 1),
                              'title': parent_resource.get_title(),
                              'path': context.get_link(links_resource)})

            events = self.links_template
            return stl(events=events, namespace={'items': links})

        return Folder_BrowseContent.get_item_value(self, resource, context,
                                                   item, column)



class BoxesOrderedTable_Ordered(SmartOrderedTable_Ordered):

    query_schema = {}

    def sort_and_batch(self, resource, context, items):
        # Sort by order regardless query
        reverse = False
        ordered_ids = list(resource.handler.get_record_ids_in_order())
        f = lambda x: ordered_ids.index(x.id)
        items.sort(cmp=lambda x,y: cmp(f(x), f(y)), reverse=reverse)

        # Always display all items
        return items


    def get_table_columns(self, resource, context):
        columns = SmartOrderedTable_Ordered.get_table_columns(self,
                resource, context)

        # Column to remove
        indexes = [ x for x, column in enumerate(columns)
                    if column[0] in ('name', 'order') ]
        indexes.sort(reverse=True)
        for index in indexes:
            columns.pop(index)

        return columns



class BoxesOrderedTable_Unordered(SmartOrderedTable_Unordered):

    query_schema = merge_dicts(ResourcesOrderedTable_Ordered.query_schema,
                               batch_size=Integer(default=0),
                               format=String)
    search_template = '/ui/bar_items/browse_search.xml'

    def get_query_schema(self):
        return self.query_schema


    def get_query(self, resource, context):
        query = SmartOrderedTable_Unordered.get_query(self, resource, context)
        # Add format filter
        format = context.query['format']
        if format:
            query = AndQuery(query, PhraseQuery('format', format))

        return query


    def get_table_columns(self, resource, context):
        columns = SmartOrderedTable_Unordered.get_table_columns(self, resource,
                                                                context)

        columns = list(columns) # create a new list
        column = ('format', MSG(u'Type'), False)
        columns.insert(3, column)

        # Column to remove
        indexes = [ x for x, column in enumerate(columns)
                    if column[0] == 'path' ]
        indexes.sort(reverse=True)
        for index in indexes:
            columns.pop(index)

        return columns


    def get_search_namespace(self, resource, context):
        orderable_classes = resource.orderable_classes
        enum = Enumerate()
        options = []
        for cls in orderable_classes:
            options.append({'name': cls.class_id, 'value': cls.class_title})
        enum.options = options

        format = context.query['format']
        widget = SelectWidget('format')
        namespace = {}
        namespace['format_widget'] = widget.to_html(enum, format)

        return namespace



class BoxesOrderedTable_View(SmartOrderedTable_View):

    subviews = [BoxesOrderedTable_Ordered(),
                BoxesOrderedTable_Unordered()]



################################################################################
# Bar edit views
################################################################################
class BoxSectionNews_Edit(AutomaticEditView):

    def _get_news_folder(self, resource, context):
        site_root = resource.get_site_root()
        news_folder = site_root.get_news_folder(context)
        return news_folder


    def get_schema(self, resource, context):
        # Base schema
        schema = AutomaticEditView.get_schema(self, resource, context)
        # News folder
        newsfolder = self._get_news_folder(resource, context)
        if newsfolder:
            # Count is already defined in resource.edit_schema
            # Do not add it but override 'tags' definition
            site_root = resource.get_site_root()
            # tags
            tags = site_root.get_resource('tags')
            sub_schema = {}
            if len(tags.get_tag_brains(context)):
                tags = TagsList(news_folder=newsfolder, multiple=True,
                                site_root=site_root)
                sub_schema['tags'] = tags

            return merge_dicts(schema, sub_schema)
        return schema


    def get_widgets(self, resource, context):
        # base widgets
        widgets = AutomaticEditView.get_widgets(self, resource, context)[:]

        # News folder
        newsfolder = self._get_news_folder(resource, context)
        if newsfolder:
            widgets.append(TextWidget('count', title=MSG(u'News to show'),
                                      size=3))
            # tags
            tags = resource.get_site_root().get_resource('tags')
            if len(tags.get_tag_brains(context)):
                widget = DualSelectWidget('tags', title=MSG(u'News TAGS'),
                        is_inline=True, has_empty_option=False)
                widgets.append(widget)

        return widgets


    def action(self, resource, context, form):
        AutomaticEditView.action(self, resource, context, form)
        # Check edit conflict
        if context.edit_conflict:
            return

        # Save changes
        for key in ('count', 'tags'):
            if key in form:
                resource.set_property(key, form[key])



################################################################################
# Base classes preview views
################################################################################
class Box_Preview(STLView):

    template = list(XMLParser(
        """
        <p>${title}</p>
        <ul stl:if="details">
            <li stl:repeat="detail details">${detail}</li>
        </ul>
        """, stl_namespaces))


    def get_template(self):
        return self.template


    def get_details(self, resource, context):
        return []


    def GET(self, resource, context):
        title = resource.class_description
        details = self.get_details(resource, context)
        template = self.get_template()
        namespace = {'title': title,
                     'details': details}
        return stl(events=template, namespace=namespace)



################################################################################
# Bar preview views
################################################################################
class BoxSectionNews_Preview(Box_Preview):

    def get_details(self, resource, context):
        details = []
        for key in ('count', 'tags'):
            value = resource.get_property(key)
            details.append(u'%s: %s' % (key, value))
        return details



class BoxTags_Preview(Box_Preview):

    def get_details(self, resource, context):
        count = resource.get_property('count')
        show_number = resource.get_property('show_number')
        random = resource.get_property('random')
        formats = resource.get_property('formats')
        details = []
        details.append(u'Tags to show (0 for all tags): %s' % count)
        details.append(u'Show number of items for each tag: %s' % show_number)
        details.append(u'This tag cloud will display only the tags '
                       u'from: %s' % ', '.join(formats))

        return details



class BoxNewsSiblingsToc_Preview(Box_Preview):

    def get_details(self, resource, context):
        return [u'Useful in a news folder, show a Table of Content '
                u'with all news.']



class HTMLContent_Edit(AutomaticEditView):


    def get_value(self, resource, context, name, datatype):
        if name == 'data':
            language = resource.get_content_language(context)
            return resource.get_html_data(language=language)
        return AutomaticEditView.get_value(self, resource, context, name,
                                           datatype)


    def action(self, resource, context, form):
        AutomaticEditView.action(self, resource, context, form)
        if context.edit_conflict:
            return
        new_body = form['data']
        language = resource.get_content_language(context)
        handler = resource.get_handler(language=language)
        handler.set_body(new_body)



################################################################################
# Sidebar preview views
################################################################################
class HTMLContent_ViewBoth():

    title = MSG(u'View with preview')
    template = '/ui/bar_items/HTMLContent_viewboth.xml'


    def get_namespace(self, resource, context):
        namespace = {}
        namespace['content'] = resource.view.GET(resource, context)
        namespace['right_rendered'] = resource.preview.GET(resource, context)
        return namespace



class SidebarBox_Preview(BaseView):
    title = MSG(u'Preview')

    def GET(self, resource, context):
        return to_box(resource, WebPage_View().GET(resource, context))



################################################################################
# Base classes views
################################################################################
class Box_View(STLView):

    def get_view_is_empty(self):
        return getattr(self, '_view_is_empty', False)


    def set_view_is_empty(self, value):
        setattr(self, '_view_is_empty', value)


    def is_admin(self, resource, context):
        ac = resource.get_access_control()
        return ac.is_allowed_to_edit(context.user, resource)



################################################################################
# Bar views
################################################################################
class BoxSectionNews_View(Box_View):

    access = 'is_allowed_to_edit'
    template = '/ui/bar_items/SectionNews_view.xml'
    title = MSG(u'View')
    more_title = MSG(u'Show all')

    def _get_news_item_view(self):
        from news_views import NewsItem_Preview
        return NewsItem_Preview()


    def _get_news_folder(self, resource, context):
        site_root = resource.get_site_root()
        news_folder = site_root.get_news_folder(context)
        return news_folder


    def _get_items(self, resource, context, news_folder):
        count = resource.get_property('count')
        tags = resource.get_property('tags')
        return news_folder.get_news(context, number=count, tags=tags)


    def _get_items_ns(self, resource, context, render=True):
        news_folder = self._get_news_folder(resource, context)
        items = self._get_items(resource, context, news_folder)

        view = self._get_news_item_view()
        ns_items = []
        for item in items:
            if render:
                ns_items.append(view.GET(item, context))
            else:
                ns_items.append(view.get_namespace(item, context))

        return ns_items


    def get_namespace(self, resource, context):
        namespace = {}

        # News title and items
        news_folder = self._get_news_folder(resource, context)
        # no news folder
        title = resource.get_property('title')
        items = []
        items_number = 0
        if news_folder:
            news_count = resource.get_property('count')
            # if news_count == 0, do not display all news
            if news_count:
                items = self._get_items_ns(resource, context, render=False)
                items_number = len(items)
                if items:
                    # Add 'first' and 'last' css classes
                    for i in xrange(items_number):
                        items[i]['css'] = ''
                    items[0]['css'] += ' first'
                    items[-1]['css'] += ' last'

        if items_number == 0 and self.is_admin(resource, context) is False:
            # Hide the box if there is no news and
            # if the user cannot edit the box
            self.set_view_is_empty(True)

        namespace['title'] = title
        namespace['items'] = items
        namespace['display'] = items_number != 0
        # more link
        more_title = self.more_title.gettext().encode('utf-8')
        tags = resource.get_property('tags')
        link = context.get_link(news_folder)
        if tags:
            # FIXME Do not add tags to query if all tags are selected
            query =  {'tags': tags}
            link = '%s?%s' % (link, encode_query(query))
        namespace['more'] = {'href': link, 'title': more_title}

        return namespace



################################################################################
# Sidebar views
################################################################################
class HTMLContent_View(Box_View, WebPage_View):

    template = '/ui/bar_items/HTMLContent_view.xml'

    def GET(self, resource, context):
        return Box_View.GET(self, resource, context)


    def get_namespace(self, resource, context):
        title = resource.get_property('display_title')
        if title:
            title = resource.get_title()
        content = list(WebPage_View.GET(self, resource, context))
        if is_empty(content):
            content = None
        if content is None and self.is_admin(resource, context) is False:
            # Hide the box if the content is empty
            self.set_view_is_empty(True)

        return {
            'name': resource.name,
            'title':title,
            'title_link': resource.get_property('title_link'),
            'title_link_target': resource.get_property('title_link_target'),
            'content': content}



class BoxTags_View(Box_View):

    access = 'is_allowed_to_view'
    title = MSG(u'View')
    template = '/ui/bar_items/Tags_view.xml'

    def _get_tags_folder(self, resource, context):
        site_root = resource.get_site_root()
        return site_root.get_resource('tags')


    def get_namespace(self, resource, context):
        tags_folder = self._get_tags_folder(resource, context)
        has_tags = tags_folder.is_empty(context) is False

        title = resource.get_property('display_title')
        if title:
            title = resource.get_title()

        # tag cloud
        box = None
        if has_tags:
            tags_to_show = resource.get_property('count')
            random = resource.get_property('random')
            show_number = resource.get_property('show_number')
            formats = resource.get_property('formats') or []
            # FIXME
            cls = tags_folder.tag_cloud.__class__
            view = cls(formats=formats, show_number=show_number,
                       random_tags=random, tags_to_show=tags_to_show,
                       show_description=False)
            box = view.GET(tags_folder, context)
        elif self.is_admin(resource, context) is False:
            # Hide the box if there is no tags and
            # if the user cannot edit the box
            self.set_view_is_empty(True)

        return {'title': title, 'box': box}



class BoxSectionChildrenTree_View(Box_View):

    template = '/ui/bar_items/SectionChildrenTree_view.xml'

    def GET(self, resource, context):
        from section import Section

        section = context._section
        if isinstance(section, Section) is False:
            self.set_view_is_empty(True)
            return None

        section_class = section.get_subsection_class()
        base_section = self._get_base_section(section, section_class)
        if isinstance(base_section, section_class) is False:
            # Strange
            self.set_view_is_empty(True)
            return None

        return STLView.GET(self, base_section, context)


    def _get_base_section(self, section, section_cls):
        # FIXME section_cls may change
        resource = section
        while isinstance(resource.parent, section_cls):
            resource = resource.parent
        return resource


    def _get_items(self, section, context, here_abspath):
        user = context.user
        section_link = context.get_link(section)
        show_one_article = section.get_property('show_one_article')
        section_class = section.get_subsection_class()
        items = []

        for name in section.get_ordered_names():
            item = section.get_resource(name, soft=True)
            sub_items = []
            if item is None:
                warn(u'resource "%s" not found' % name)
                continue

            # Check security
            ac = item.get_access_control()
            if ac.is_allowed_to_view(user, item) is False:
                continue

            item_abspath = item.get_abspath()
            # css
            css = None
            if item_abspath == here_abspath:
                css = 'active'
            elif here_abspath.get_prefix(item_abspath) ==  item_abspath:
                css = 'in-path'
            # link
            is_section = type(item) == section_class
            if show_one_article or is_section:
                path = context.get_link(item)
            else:
                path = '%s#%s' % (section_link, item.name)
            # subsections
            if is_section:
                if item_abspath.get_prefix(here_abspath) == item_abspath:
                    # deploy sub sections
                    sub_items = self._get_items(item, context, here_abspath)
                    # If there's only one sub item
                    # and section do not show article one by one we hide subitem
                    one_by_one = item.get_property('show_one_article')
                    if one_by_one is False and len(sub_items) == 1:
                        sub_items = []
            items.append({'path': path, 'title': item.get_title(),
                'class': css, 'sub_items': sub_items})

        return items


    def get_toc_title(self, resource, context):
        return resource.get_property('title')


    def get_items(self, resource, context):
        here = context.resource
        # resource is the base section
        section_class = resource.get_subsection_class()
        items = self._get_items(resource, context, here.get_abspath())

        return items


    def get_namespace(self, resource, context):
        namespace = {}
        allowed_to_edit = self.is_admin(resource, context)

        # Subsections (siblings)
        items = self.get_items(resource, context)
        namespace['items'] = items
        namespace['title'] = self.get_toc_title(resource, context)

        # Hide siblings box if the user is not authenticated and
        # submenu is empty
        min_limit = 1 if resource.get_property('hide_if_only_one_item') else 0
        hide_if_not_enough_items = len(items) <= min_limit
        if allowed_to_edit is False and hide_if_not_enough_items:
            self.set_view_is_empty(True)

        namespace['hide_if_not_enough_items'] = hide_if_not_enough_items
        namespace['limit'] = min_limit

        return namespace



class BoxNewsSiblingsToc_View(BoxSectionNews_View):

    template = '/ui/bar_items/NewsSiblingsToc_view.xml'
    more_title = MSG(u'Show all')

    def _get_items(self, resource, context, news_folder, brain_only=False):
        return news_folder.get_news(context, brain_only=brain_only)


    def get_namespace(self, resource, context):
        namespace = {'items': {'displayed': [], 'hidden': []},
                     'title': resource.get_property('title'),
                     'class': None}
        site_root = resource.get_site_root()
        newsfolder_cls = site_root.newsfolder_class
        if newsfolder_cls is None:
            self.set_view_is_empty(True)
            return namespace

        allowed_to_edit = self.is_admin(resource, context)
        here = context.resource
        here_is_newsfolder = isinstance(here, newsfolder_cls)
        if here_is_newsfolder:
            news_folder = here
            news = None
        else:
            news_folder = here.parent
            news = here

        if isinstance(news_folder, newsfolder_cls) is False:
            self.set_view_is_empty(True)
            return namespace

        # News (siblings)
        news_count = resource.get_property('count')
        title = resource.get_property('title')
        displayed_items = self._get_items_ns(resource, context, render=True)
        displayed_items = list(displayed_items)
        items_number = len(displayed_items)
        hidden_items = []
        if news_count:
            if not here_is_newsfolder:
                if news:
                    news_brains = self._get_items(resource, context,
                                                  news_folder, brain_only=True)
                    news_abspath = news.get_abspath()
                    news_index = 0
                    # Do not hide current news
                    for index, brain in enumerate(news_brains):
                        if brain.abspath == news_abspath:
                            news_index = index + 1
                            break
                    news_count = max(news_count, news_index)

                hidden_items = displayed_items[news_count:]
            displayed_items = displayed_items[:news_count]
        namespace['items'] = {'displayed': displayed_items,
                              'hidden': hidden_items}
        namespace['more_title'] = self.more_title.gettext().encode('utf-8')

        # Hide siblings box if the user is not authenticated and
        # there is not other items
        min_limit = 1 if news_count else 0
        hide_if_not_enough_items = len(displayed_items) <= min_limit
        if allowed_to_edit is False and hide_if_not_enough_items:
            self.set_view_is_empty(True)

        namespace['hide_if_not_enough_items'] = hide_if_not_enough_items
        namespace['limit'] = min_limit

        return namespace



################################################################################
# Contentbar views
################################################################################
class BoxSectionWebpages_View(Box_View):

    template = '/ui/bar_items/SectionWebpages_view.xml'

    def GET(self, resource, context):
        site_root = resource.get_site_root()
        section_cls = site_root.section_class
        here = context.resource
        parent = here.parent
        section = context._section
        article_cls = section.get_article_class()
        one_by_one = self.is_article_one_by_one(resource, context)
        if (isinstance(here, section_cls) or
            issubclass(here.__class__, WebSite)):
            # Section
            # Case (1)
            if one_by_one is True:
                # Articles are show one by one
                # Do not display the box
                self.set_view_is_empty(True)
                return None

            # Case (2)
            return Box_View.GET(self, resource, context)

        if isinstance(here, article_cls):
            if one_by_one is True:
                return Box_View.GET(self, resource, context)

            # This case should not append
            # Article view with all articles displayed in the section view
            self.set_view_is_empty(True)
            return None

        # Default case, Bad resource not a section or an article
        self.set_view_is_empty(True)
        return None


    def get_articles_container(self, resource, context):
        return context._section


    def get_article_class(self, resource, context):
        section = context._section
        return section.get_article_class()


    def is_article_one_by_one(self, resource, context):
        site_root = resource.get_site_root()
        section_cls = site_root.section_class
        section = context._section
        if isinstance(section, section_cls):
            # XXX
            return section.get_property('show_one_article')
        return False


    def get_items(self, resource, context):
        user = context.user
        here = context.resource
        article_container = self.get_articles_container(resource, context)
        one_by_one = self.is_article_one_by_one(resource, context)
        article_cls = self.get_article_class(resource, context)

        items = []
        if one_by_one is False:
            names = list(article_container.get_ordered_names())
            for name in names:
                article = article_container.get_resource(name, soft=True)
                if not article:
                    continue
                # Ignore subsections
                if not isinstance(article, article_cls):
                    continue
                # Check security
                ac = article.get_access_control()
                if ac.is_allowed_to_view(user, article):
                    items.append(article)
        else:
            items = [ context.resource ]

        return items


    def get_namespace(self, resource, context):
        namespace = {}
        # Articles
        user = context.user
        article_container = self.get_articles_container(resource, context)
        article_cls = self.get_article_class(resource, context)
        articles = list(self.get_items(resource, context))
        articles_view = []
        article_view = article_cls.view
        if len(articles):
            # All articles are in the same folder
            # Compute the prefix with the first one
            prefix = resource.get_pathto(articles[0])

            for article in articles:
                stream = set_prefix(article_view.GET(article, context),
                                    '%s/' % prefix)
                articles_view.append(stream)
        namespace['articles'] = articles_view

        if len(articles) == 0 and self.is_admin(resource, context) is False:
            # Hide the box if there is no articles and
            # if the user cannot edit the box
            self.set_view_is_empty(True)

        return namespace



class ContentBoxSectionChildrenToc_View(BoxSectionWebpages_View):

    template = '/ui/bar_items/ContentBoxSectionChildrenToc_view.xml'

    def GET(self, resource, context):
        site_root = resource.get_site_root()
        section_cls = site_root.section_class
        here = context.resource
        parent = here.parent
        section = context._section
        article_cls = section.get_article_class()
        one_by_one = self.is_article_one_by_one(resource, context)

        if isinstance(here, section_cls):
            return Box_View.GET(self, resource, context)

        if isinstance(here, article_cls):
            if one_by_one is False:
                return Box_View.GET(self, resource, context)

            # This case should not append
            self.set_view_is_empty(True)
            return None

        # Default case, Bad resource not a section or an article
        self.set_view_is_empty(True)
        return None


    def get_items(self, resource, context):
        user = context.user
        here = context.resource
        section = context._section

        items = []
        names = list(section.get_ordered_names())
        for name in names:
            item = section.get_resource(name, soft=True)
            if not item:
                continue
            # Check security
            ac = item.get_access_control()
            if ac.is_allowed_to_view(user, item):
                items.append(item)

        return items


    def get_namespace(self, resource, context):
        namespace = {}
        # Items
        here = context.resource
        user = context.user
        section = context._section
        article_cls = section.get_article_class()
        one_by_one = self.is_article_one_by_one(resource, context)
        items = list(self.get_items(resource, context))
        items_ns = []
        if len(items):
            for item in items:
                if one_by_one is True:
                    path = context.get_link(item)
                else:
                    if type(item) == article_cls:
                        path = '%s#%s' % (context.get_link(item.parent),
                                          item.name)
                    else:
                        path = context.get_link(item)

                ns = {'title': item.get_title(),
                      'path': path}
                items_ns.append(ns)

        allowed_to_edit = self.is_admin(resource, context)
        min_limit = 1 if resource.get_property('hide_if_only_one_item') else 0
        hide_if_not_enough_items = False
        if allowed_to_edit is False:
            if len(items) <= min_limit:
                # Hide the box if there is no articles and
                # if the user cannot edit the box
                self.set_view_is_empty(True)
        elif len(items) <= min_limit:
            # If the user can edit the item and there is there is
            # not enough items reset items entry
            items_ns = []
            hide_if_not_enough_items = True

        namespace['items'] = items_ns
        namespace['title'] = section.get_title()
        namespace['hide_if_not_enough_items'] = hide_if_not_enough_items
        namespace['limit'] = min_limit

        return namespace



class BoxWebsiteWebpages_View(BoxSectionWebpages_View):


    def get_articles_container(self, resource, context):
        site_root = resource.get_site_root()
        return site_root.get_resource('ws-data')


    def get_article_class(self, resource, context):
        site_root = resource.get_site_root()
        return site_root.get_article_class()


    def is_article_one_by_one(self, resource, context):
        return False
