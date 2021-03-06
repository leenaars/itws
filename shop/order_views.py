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

# Import from standard library
from datetime import datetime, time

# Import from itools
from itools.core import freeze
from itools.csv import CSVFile
from itools.database import AndQuery, PhraseQuery, RangeQuery
from itools.datatypes import Date, Decimal, Enumerate, Integer
from itools.gettext import MSG
from itools.web import INFO, ERROR, STLForm, STLView
from itools.xml import XMLParser

# Import from ikaaro
from ikaaro.autoform import AutoForm, DateWidget, SelectWidget, TextWidget
from ikaaro.buttons import Button
from ikaaro.file import PDF
from ikaaro.utils import CMSTemplate, get_base_path_query
from ikaaro.views import CompositeForm, CompositeView

# Import from itws
from itws.views import FieldsAdvance_NewInstance
from itws.feed_views import TableFeed_View, FieldsTableFeed_View
from itws.utils import bool_to_img

# Import from shop
from devises import Devises
from payments_views import PaymentWays_Enumerate
from product import Product_List
from utils import join_pdfs, get_arrondi, get_orders, get_payments
from widgets import PaymentWays_Widget
from workflows import OrderStateEnumerate



class Order_AddLine(AutoForm):

    access = 'is_admin'
    title = MSG(u'Add a line')
    schema = {'product': Product_List,
              'quantity': Integer}
    widgets = [SelectWidget('product', title=MSG(u'Line')),
               TextWidget('quantity', title=MSG(u'Quantity'))]

    def action(self, resource, context, form):
        r = resource.get_resource(form['product'])
        resource.add_lines([(form['quantity'], r)])
        message = INFO(u'This product has been added to your order')
        return context.come_back(message, goto='./;manage')



class Order_ViewBills(FieldsTableFeed_View):

    access = 'is_admin'
    title = MSG(u'Bills')

    table_actions = []
    show_resource_title = False
    query_suffix = 'order-bill'

    batch_template = None
    batch_msg1 = MSG(u"There is 1 bill.")
    batch_msg2 = MSG(u"There are {n} bills.")

    table_fields = ['title', 'mtime']

    search_class_id = 'application/pdf'
    search_cls = PDF

    def get_item_value(self, resource, context, item, column):
        if column == 'title':
            brain, item_resource = item
            title = item_resource.get_property('title')
            link = context.get_link(item_resource)
            return title, '%s/;download' % link
        proxy = super(Order_ViewBills, self)
        return proxy.get_item_value(resource, context, item, column)


class Order_ViewPayments(TableFeed_View):

    access = 'is_allowed_to_view'
    title = MSG(u'Payments')

    show_resource_title = False
    query_suffix = 'payments'
    table_actions = []

    batch_template = None
    batch_msg1 = MSG(u"There is 1 payment.")
    batch_msg2 = MSG(u"There are {n} payments.")

    admin_view = False
    table_columns = freeze([
        ('reference', MSG(u'Reference')),
        ('payment_way', MSG(u'Payment Way')),
        ('amount', MSG(u'Amount')),
        ('is_payment_validated', MSG(u'Validated ?'))])

    def get_table_columns(self, resource, context):
        if self.admin_view is False:
            return self.table_columns
        return self.table_columns + [
            ('advanced_state', MSG(u'Advanced state'))]


    def get_items(self, resource, context):
        return resource.get_payments(as_results=True)


    def get_item_value(self, resource, context, item, column):
        brain, item_resource = item
        if column == 'reference':
            if self.admin_view is False:
                return brain.name
            return (brain.name, brain.name)
        elif column == 'payment_way':
            return item_resource.get_payment_way().get_title()
        elif column == 'amount':
            devise = item_resource.get_property('devise')
            symbol = Devises.symbols[devise]
            amount = item_resource.get_property('amount')
            return u'%s %s' % (amount, symbol)
        elif column == 'advanced_state':
            return item_resource.get_advanced_state()
        elif column  == 'is_payment_validated':
            value = item_resource.is_payment_validated()
            if value:
                return bool_to_img(value)
            return u'Régler', '%s/;payment_form' % brain.name
        raise NotImplementedError



class Order_AddPayment(AutoForm):

    access = 'is_admin'
    title = MSG(u'Add a payment')
    return_message = INFO(u"Please follow the payment procedure below.")

    schema = freeze({
        'amount': Decimal,
        'mode': PaymentWays_Enumerate})
    widgets = freeze([
        TextWidget('amount', title=MSG(u'Amount')),
        PaymentWays_Widget('mode', title=MSG(u"Payment Way"))])


    def action(self, resource, context, form):
        payments_module = get_payments(resource)
        devise = resource.get_property('devise')
        payment = payments_module.make_payment(
                      resource, form['mode'], form['amount'],
                      context.user, devise, order=resource)
        goto = '%s/;payment_form' % context.get_link(payment)
        return context.come_back(self.return_message, goto=goto)



class Order_AdminTop(STLForm):
    """Display order main information with state and products."""
    access = 'is_admin'
    title = MSG(u'Manage order')
    template = '/ui/shop/orders/order_manage.xml'


    def get_namespace(self, resource, context):
        orders = get_orders(resource)
        namespace = resource.get_namespace(context)
        namespace['orders_link'] = context.get_link(orders)
        namespace['order'] = {'id': resource.name}
        #namespace['state'] = SelectWidget('state', has_empty_option=False,
        #    datatype=OrderStateEnumerate, value=resource.get_statename()).render()
        return namespace


    #action_change_order_state_schema = {'state': OrderStateEnumerate}
    #def action_change_order_state(self, resource, context, form):
    #    resource.generate_bill(context)
    #    resource.set_workflow_state(form['state'])


class Order_Top(STLView):

    access = 'is_allowed_to_view'
    template = '/ui/shop/orders/order_top.xml'

    def get_namespace(self, resource, context):
        bill = resource.get_bill()
        return {'name': resource.name,
                'bill': context.get_link(bill) if bill else None,
                'is_paid': resource.get_property('is_paid')}



class Order_ViewProducts(STLView):

    access = 'is_allowed_to_view'
    title = MSG(u'Products')
    template = '/ui/shop/orders/order_view_products.xml'

    def get_namespace(self, resource, context):
        namespace = {}
        namespace['products'] = resource.get_products_namespace(context)
        total = resource.get_property('total_price')
        namespace['total_price'] = resource.format_price(total)
        return namespace



class Order_RegenerateBill(AutoForm):

    access = 'is_admin'
    title = MSG(u'Bill')
    actions = [Button(access=True, css='button-ok',
        title=MSG(u'Generate bill again (overwrite previous one)'))]

    def action(self, resource, context, form):
        bill = resource.generate_bill(context)
        goto = './;manage'
        if bill is None:
            return context.come_back(MSG(u'Impossible action.'), goto=goto)
        return context.come_back(MSG(u'Bill generated again.'), goto=goto)



class Order_View(CompositeView):

    access = 'is_allowed_to_view'
    title = MSG(u'View')

    subviews = [Order_Top(),
                Order_ViewProducts(),
                Order_ViewPayments(admin_view=False)]



class Order_Manage(CompositeForm):
    """Display order main information with state and products
       and below a list of payments and bills.
    """
    access = 'is_admin'
    title = MSG(u'Manage order')

    subviews = [Order_AdminTop(),
                Order_ViewProducts(),
                Order_ViewPayments(admin_view=True),
                Order_ViewBills()]


class Order_NewInstance(FieldsAdvance_NewInstance):

    access = 'is_admin'
    title = MSG(u'Create a new order')
    fields = ['customer_id']

    def _get_form(self, resource, context):
        # Skip checking name as we use make_reference
        return super(AutoForm, self)._get_form(resource, context)


    def action(self, resource, context, form):
        orders_module = get_orders(resource)
        order = orders_module.make_order(resource, context.user, lines=[])
        goto = context.get_link(order)
        message = MSG(u'Order has been created')
        return context.come_back(message, goto=goto)


class OrderState_Template(CMSTemplate):

    template = '/ui/shop/orders/order_state.xml'

    title = None
    link = None
    color = None


class ExportFormats(Enumerate):

    options = [{'name': 'csv', 'value': MSG(u'CSV')},
               {'name': 'pdf', 'value': MSG(u'PDF')}]


class OrderModule_Export(AutoForm):

    access = 'is_admin'
    title = MSG(u'Export')

    schema = {'format': ExportFormats(mandatory=True),
              'since': Date(mandatory=True)}
    widgets = [
        SelectWidget('format', title=MSG(u'Format'), has_empty_option=False),
        DateWidget('since', title=MSG(u'Since'))]

    def export_pdf(self, resource, context, form):
        list_pdf = []
        site_root = resource.get_site_root()
        since = datetime.combine(form['since'], time(0,0))
        orders = context.root.search(AndQuery(PhraseQuery('is_order', True),
            get_base_path_query(site_root.get_canonical_path()),
            RangeQuery('ctime', since, None)))
        for brain in orders.get_documents(sort_by='ctime'):
            order = resource.get_resource(brain.abspath)
            pdf = order.get_bill()
            if pdf is None:
                continue
            path = context.database.fs.get_absolute_path(pdf.handler.key)
            list_pdf.append(path)
        # Join pdf
        pdf = join_pdfs(list_pdf)
        if pdf is None:
            context.message = ERROR(u"Error: Can't merge PDF")
            return
        context.set_content_type('application/pdf')
        context.set_content_disposition('attachment; filename="Orders.pdf"')
        return pdf


    def get_csv_value(self, resource, context, item, column):
        brain, item_resource = item
        if column == 'name':
            return brain.name
        elif column == 'customer_id':
            return item_resource.get_property('customer_id')
        elif column == 'workflow_state':
            value = item_resource.get_statename()
            title = OrderStateEnumerate.get_value(value)
            return title.gettext()
        elif column in ('total_price', 'total_paid'):
            value = item_resource.get_property(column)
            return value
        elif column in ('total_pre_vat', 'total_vat'):
            total_pre_vat, total_vat = item_resource.get_vat_details(context)
            return get_arrondi(eval(column))
        elif column in ('ctime',):
            value = brain.ctime
            return context.format_datetime(value)
        return ''


    def export_csv(self, resource, context, form):
        columns = ['name', 'customer_id', 'workflow_state', 'total_pre_vat',
                   'total_vat', 'total_price', 'total_paid', 'ctime']
        header = [MSG(u'Order ref.'), MSG(u'Customer ref.'), MSG(u'State'),
                  MSG(u'Total VAT not inc.'), MSG(u'VAT'),
                  MSG(u'Total VAT inc.'), MSG(u'Total paid'), MSG(u'Date')]
        header = [x.gettext().encode('utf-8') for x in header]
        csv = CSVFile()
        csv.add_row(header)
        lines = []
        site_root = resource.get_site_root()
        since = datetime.combine(form['since'], time(0,0))
        orders = context.root.search(AndQuery(PhraseQuery('is_order', True),
            get_base_path_query(site_root.get_canonical_path()),
            RangeQuery('ctime', since, None)))
        for brain in orders.get_documents(sort_by='ctime'):
            item_resource = resource.get_resource(brain.abspath)
            item = brain, item_resource
            row = []
            for c in columns:
                value = self.get_csv_value(resource, context, item, c)
                if isinstance(value, unicode):
                    value = value.encode('utf-8')
                else:
                    value = str(value)
                row.append(value)
            csv.add_row(row)
        separator = ','
        context.set_content_type('text/comma-separated-values')
        context.set_content_disposition('attachment; filename="Orders.csv"')
        return csv.to_str(separator=separator)


    def action(self, resource, context, form):
        export_format  = form['format']
        if export_format == 'pdf':
            return self.export_pdf(resource, context, form)
        elif export_format == 'csv':
            return self.export_csv(resource, context, form)
        context.message = ERROR(u'Invalid format')



class OrderModule_ViewOrders(FieldsTableFeed_View):

    access = 'is_admin'
    title = MSG(u'Orders')

    sort_by = 'ctime'
    reverse = True
    batch_msg1 = MSG(u"There is 1 order")
    batch_msg2 = MSG(u"There are {n} orders")
    table_actions = []

    styles = ['/ui/shop/style.css']

    search_on_current_folder = False
    search_on_current_folder_recursive = True

    search_fields = ['name', 'customer_id']
    table_fields = ['checkbox', 'name', 'customer_id', 'workflow_state',
                    'total_price', 'total_paid', 'ctime', 'bill']

    def get_item_value(self, resource, context, item, column):
        brain, item_resource = item
        if column in ('total_price', 'total_paid'):
            value = item_resource.get_property(column)
            return item_resource.format_price(value)
        elif column == 'name':
            return OrderState_Template(title=brain.name,
                link=context.get_link(item_resource), color='#BF0000')
        elif column == 'workflow_state':
            value = item_resource.get_statename()
            title = OrderStateEnumerate.get_value(value)
            return OrderState_Template(title=title,
                link=context.get_link(item_resource), color='#BF0000')
        elif column == 'bill':
            bill = item_resource.get_bill()
            if bill is None:
                return None
            return XMLParser("""
                    <a href="%s/;download">
                      <img src="/ui/icons/16x16/pdf.png"/>
                    </a>""" % context.get_link(bill))
        proxy = super(OrderModule_ViewOrders, self)
        return proxy.get_item_value(resource, context, item, column)


    @property
    def search_cls(self):
        from orders import Order
        return Order


    def get_items(self, resource, context, *args):
        query = PhraseQuery('is_order', True)
        return FieldsTableFeed_View.get_items(self, resource, context, query)
