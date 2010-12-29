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
from itools.core import merge_dicts
from itools.database import PhraseQuery
from itools.datatypes import Boolean, Integer
from itools.gettext import MSG

# Import from ikaaro
from ikaaro.autoform import RadioWidget, SelectWidget, TextWidget
from ikaaro.folder import Folder

# Import from itws
from base import BaseSectionView_Configuration
from itws.datatypes import SortBy_Enumerate
from itws.feed_views.base import Feed_View


class ImagesView_Configuration(BaseSectionView_Configuration):

    class_id = 'images_view_configuration'
    class_title = MSG(u'Images view')
    class_schema = merge_dicts(
        Folder.class_schema,
        # View properties
        view_sort_by=SortBy_Enumerate(source='metadata'),
        view_reverse=Boolean(source='metadata'),
        view_batch_size=Integer(source='metadata', default=20),
        # Thumb size
        thumb_width=Integer(default=128, source='metadata'),
        thumb_height=Integer(default=128, source='metadata'))

    edit_schema = {
        'view_sort_by': SortBy_Enumerate,
        'view_reverse': Boolean,
        'view_batch_size': Integer,
        'thumb_width': Integer,
        'thumb_height': Integer}

    edit_widgets = [
        SelectWidget('view_sort_by', title=MSG(u'View sort by'),
                     has_empty_option=False),
        RadioWidget('view_reverse', title=MSG(u'View reverse')),
        TextWidget('view_batch_size', title=MSG(u'View batch size')),
        TextWidget('thumb_width', title=MSG(u'Thumb width')),
        TextWidget('thumb_height', title=MSG(u'Thumb height'))]



class ImagesView_View(Feed_View):

    content_template = '/ui/feed_views/images_view.xml'
    search_template = None
    styles = ['/ui/feed_views/images_view.css',
              '/ui/common/js/fancybox/jquery.fancybox-1.3.1.css']
    scripts = ['/ui/common/js/fancybox/jquery.fancybox-1.3.1.pack.js']

    # Section view properties
    view_name = 'images-view'
    view_title = MSG(u'Images view')
    view_configuration_cls = ImagesView_Configuration

    def get_items(self, resource, context, *args):
        args = list(args)
        args.append(PhraseQuery('is_image', True))
        return Feed_View.get_items(self, resource, context, *args)


    def get_content_namespace(self, resource, context, items):
        conf_resource = resource.get_resource('section_view')
        namespace = Feed_View.get_content_namespace(self, resource, context, items)
        for key in ['thumb_width', 'thumb_height']:
            namespace[key] = conf_resource.get_property(key)
        return namespace
