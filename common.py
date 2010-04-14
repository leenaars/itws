# -*- coding: UTF-8 -*-
# Copyright (C) 2008-2009 Nicolas Deram <nicolas@itaapy.com>
# Copyright (C) 2008-2010 Henry Obein <henry@itaapy.com>
# Copyright (C) 2009 Dumont Sébastien <sebastien.dumont@itaapy.com>
# Copyright (C) 2009 J. David Ibanez <jdavid@itaapy.com>
# Copyright (C) 2009 Taverne Sylvain <sylvain@itaapy.com>
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
from itools.core import get_abspath
from itools.datatypes import Unicode
from itools.gettext import get_domain
from itools.i18n import get_language_name
from itools.stl import stl, set_prefix

# Import from ikaaro
from ikaaro.forms import HTMLBody
from ikaaro.future.menu import get_menu_namespace
from ikaaro.resource_ import DBResource
from ikaaro.skins import Skin, register_skin
from ikaaro.skins_views import LocationTemplate, LanguagesTemplate
from ikaaro.utils import reduce_string


def get_breadcrumb_short_name(resource):
    if isinstance(resource, DBResource):
        if resource.has_property('breadcrumb_title'):
            return resource.get_property('breadcrumb_title')
        return reduce_string(resource.get_title(), 15, 30)
    return ''


class LocationTemplateWithoutTab(LocationTemplate):

    template = '/ui/common/location.xml'
    bc_prefix = None
    bc_separator = '>'
    tabs_separator = '|'
    # breadcrumbs configuration
    excluded = []
    skip_breadcrumb_in_homepage = False
    homepage_name = None
    # tabs comfiguration
    tabs_hidden_roles = None
    tabs_hide_if_only_one_item = True

    def get_breadcrumb(self, context):
        here = context.resource
        site_root = here.get_site_root()
        if self.skip_breadcrumb_in_homepage:
            # Hide the breadcrumb in the Home Page
            # FIXME homepage name should dynamic (first section in the menu)
            home_path = site_root.get_abspath().resolve2(self.homepage_name)
            # Case 1: /index
            if here.get_abspath() == home_path:
                return []
            # Case 2: /
            if type(here) is type(site_root) and \
                    context.view_name in ('view', None):
                ac = here.get_access_control()
                allowed = ac.is_allowed_to_edit(context.user, here)
                if not allowed:
                    return []

        excluded = self.excluded

        # Initialize the breadcrumb with the root resource
        path = '/'
        title = site_root.get_title()
        breadcrumb = [{
            'url': path,
            'name': title,
            'short_name': get_breadcrumb_short_name(site_root),
            }]

        # Complete the breadcrumb
        resource = site_root
        for name in context.uri.path:
            path = path + ('%s/' % name)
            resource = resource.get_resource(name, soft=True)
            if path in excluded:
                continue
            if resource is None:
                break
            # Append
            title = resource.get_title()
            breadcrumb.append({
                'url': path,
                'name': title,
                'short_name': get_breadcrumb_short_name(resource),
            })

        # Hide breadcrumb if there is only one item
        if len(breadcrumb) == 1:
            return []

        return breadcrumb


    def get_tabs(self, context):
        user = context.user
        if user is None:
            return []
        excluded_roles = self.tabs_hidden_roles
        if excluded_roles:
            user_name = user.name
            site_root = context.site_root
            for role in excluded_roles:
                if site_root.has_user_role(user_name, role):
                    return []

        tabs = LocationTemplate.get_tabs(self, context)
        if self.tabs_hide_if_only_one_item and len(tabs) == 1:
            return []
        return tabs


    def get_namespace(self):
        namespace = LocationTemplate.get_namespace(self)
        namespace['bc_prefix'] = (self.bc_prefix.gettext() if self.bc_prefix
                                     else None)
        namespace['bc_separator'] = self.bc_separator
        namespace['tabs_separator'] = self.tabs_separator
        # Hide/Show location div
        tabs = namespace['tabs']
        breadcrumb = namespace['breadcrumb']
        namespace['display'] = len(tabs) or len(breadcrumb)

        return namespace



class CommonLanguagesTemplate(LanguagesTemplate):

    template = '/ui/common/languages.xml'

    def get_namespace(self):
        context = self.context
        # Website languages
        site_root = context.site_root
        ws_languages = site_root.get_property('website_languages')
        if len(ws_languages) == 1:
            return {'languages': []}

        here = context.resource
        ac = here.get_access_control()
        allowed = ac.is_allowed_to_edit(context.user, here)

        # Select language
        accept = context.accept_language
        current_language = accept.select_language(ws_languages)
        # Sort the available languages
        ws_languages = list(ws_languages)
        ws_languages.sort()

        available_langs = ws_languages
        # If the user can edit the resource, we display all the languages
        if allowed is False:
            get_available_languages = getattr(here, 'get_available_languages',
                                              None)
            if context.user is None and get_available_languages is not None:
                available_langs = get_available_languages(ws_languages)

        languages = []
        gettext = get_domain('itools').gettext
        for language in available_langs:
            href = context.uri.replace(language=language)
            selected = (language == current_language)
            css_class = 'selected' if selected else None
            value = get_language_name(language)
            languages.append({
                'name': language,
                'value': gettext(value, language),
                'href': href,
                'selected': selected,
                'class': css_class})

        return {'languages': languages}



class FoBoFooterAwareSkin(Skin):

    nav_data = {'template': None, 'depth': 1, 'show_first_child': False}
    add_common_nav_css = True
    footer_data = {
        'template': '/ui/common/template_footer.xml', 'depth': 1,
        'src': 'footer', 'show_first_child': False, 'separator': '|' }

    location_template = LocationTemplateWithoutTab
    languages_template = CommonLanguagesTemplate

    def get_styles(self, context):
        styles = Skin.get_styles(self, context)
        styles.insert(0, '/ui/common/style.css')
        if self.add_common_nav_css:
            styles.append('/ui/common/menu.css')
        styles.append('/ui/common/js/jquery.multiselect2side/css/jquery.multiselect2side.css')
        # Add a specific style
        styles.append('/style/;download')
        return styles


    def get_scripts(self, context):
        scripts = Skin.get_scripts(self, context)
        scripts.append('/ui/common/js/javascript.js')
        scripts.append('/ui/common/js/jquery.multiselect2side/js/jquery.multiselect2side.js')
        return scripts


    def build_nav_namespace(self, context, data=None):
        if data is None:
            data = self.nav_data
        if data:
            depth = data['depth']
            sfc = data['show_first_child']
            src = data.get('src', None)
            flat = data.get('flat', None)

            nav = get_menu_namespace(context, depth, sfc, flat=flat, src=src)
            # HOOK the namespace
            for item in nav.get('items', []):
                if item['class'] == 'in_path':
                    item['in_path'] = True
                else:
                    item['in_path'] = False

            return nav

        return None


    def build_footer_namespace(self, context, data=None):
        if data is None:
            data = self.footer_data
        ns = self.build_nav_namespace(context, data)
        if ns is None:
            return ns
        here = context.resource
        site_root = here.get_site_root()
        footer = site_root.get_resource('%s/menu' % data['src'])
        handler = footer.handler
        records = list(handler.get_records_in_order())
        get_value = handler.get_record_value
        prefix = here.get_pathto(footer)
        # HOOK the namespace
        for index, item in enumerate(ns.get('items', [])):
            record = records[index]
            title = get_value(record, 'title')
            path = get_value(record, 'path')
            html_content = get_value(record, 'html_content')
            item['html'] = None
            if not path and not title and html_content:
                html = HTMLBody.decode(Unicode.encode(html_content))
                html = set_prefix(html, prefix)
                item['html'] = html
        ns['separator'] = data.get('separator', '|')
        return ns


    def build_namespace(self, context):
        namespace = Skin.build_namespace(self, context)

        # Nav
        # If there is no template specify we simply return the namespace
        nav = self.build_nav_namespace(context)
        namespace['nav'] = nav
        namespace['nav_length'] = len(nav['items'])
        nav_template = self.nav_data['template']
        if nav_template is not None:
            nav_template = self.get_resource(nav_template)
            namespace['nav'] = stl(nav_template, {'items': nav['items']})

        # Footer
        footer_template = self.footer_data['template']
        if footer_template is not None:
            ns_footer = self.build_footer_namespace(context)
            footer_template = self.get_resource(footer_template)
            namespace['footer'] = stl(footer_template, ns_footer)

        # Hide context menus if no user authenticated
        if context.user is None:
            namespace['context_menus'] = []

        # Allow to hide the menu if there is only one item
        namespace['display_menu'] = (namespace['nav_length'] > 1)

        return namespace


# Register common skin
path = get_abspath('ui/common')
register_skin('common', path)
