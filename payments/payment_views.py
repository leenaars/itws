# -*- coding: UTF-8 -*-
# Copyright (C) 2009 Sylvain Taverne <sylvain@itaapy.com>
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
from itools.web import STLView, get_context
from itools.xml import XMLParser

# Import from ikaaro
from ikaaro.autoform import ReadOnlyWidget
from ikaaro.workflow import get_workflow_preview

# Import from payments
from utils import format_price
from itws.views import FieldsAutomaticEditView


class Payment_Edit(FieldsAutomaticEditView):

    access = 'is_allowed_to_edit'
    title = MSG(u'Edit')

    base_edit_fields = ['name', 'amount']

    @property
    def edit_fields(self):
        resource = get_context().resource
        return self.base_edit_fields + resource.payment_fields


    def get_widget(self, name, datatype):
        if name == 'name':
            return ReadOnlyWidget('name', title=MSG(u"Payment ID"))
        elif name == 'amount':
            return ReadOnlyWidget('amount', title=MSG(u"Amount"))
        proxy = super(Payment_Edit, self)
        return proxy.get_widget(name, datatype)


    def get_value(self, resource, context, name, datatype):
        if name == 'name':
            payment_way = resource.get_payment_way()
            payment_way_title = payment_way.get_title().encode('utf-8')
            payment_way_link = context.get_link(payment_way)
            events = XMLParser('Payment #%s via <a href="%s">%s</a>' %
                        (resource.name, payment_way_link, payment_way_title))
            return list(events)
        elif name == 'amount':
            return u'%s' % resource.get_property('amount')
        proxy = super(Payment_Edit, self)
        return proxy.get_value(resource, context, name, datatype)


    def set_value(self, resource, context, name, datatype):
        if name in ['name', 'amount']:
            return
        proxy = super(Payment_Edit, self)
        return proxy.set_value(resource, context, name, datatype)


    def action(self, resource, context, form):
        workflow_state = form['state']
        if workflow_state == 'validated':
            resource.set_payment_as_validated(resource, context)
        else:
            resource.set_workflow_state(workflow_state)
        # Action
        proxy = super(Payment_Edit, self)
        return proxy.action(resource, context, form)



class Payment_End(STLView):

    access = 'is_authenticated'
    template = '/ui/payments/payment_end.xml'

    def get_namespace(self, resource, context):
        payment_way = resource.get_payment_way()
        return {
            'payment_end_msg': payment_way.get_property('payment_end_msg'),
            'payment_way': payment_way.get_title(),
            'amount': format_price(resource.get_property('amount'), unit=u"€"),
            'state': get_workflow_preview(resource, context)}
