# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging
import random
from datetime import timedelta, datetime

_logger = logging.getLogger(__name__)


class SaleOrderAPI(models.TransientModel):
    _name = 'sale.order.api'
    _description = 'Sale Order API Interface'

    @api.model
    def create_sale_order(self, partner_name, company_name, order_lines_data,
                          delivery_address, delivery_date, shipping_weight,
                          customer_reference):
        """
        创建销售订单的API接口

        Args:
            partner_name (str): 客户名称
            company_name (str): 公司名称
            order_lines_data (list): 订单行数据列表，每个元素为字典:
                {
                    'product_name': str,  # 产品名称
                    'quantity': float,    # 数量
                    'price': float        # 单价
                }
            delivery_address (str): 送货地址
            delivery_date (str): 送货日期，格式 'YYYY-MM-DD'
            shipping_weight (float): 运输重量
            customer_reference (str): 客户参考信息

        Returns:
            dict: 包含订单创建结果的字典
        """
        try:
            # 获取或创建客户
            partner = self._get_or_create_partner(partner_name)

            # 获取公司
            company = self._get_company(company_name)

            # 获取销售员
            user = self._get_company_salesperson(company)

            # 获取默认价格表和支付条款
            pricelist = self._get_default_pricelist(company)
            payment_term = self._get_default_payment_term(company)

            # 处理订单行
            order_lines = []
            for line in order_lines_data:
                product = self._get_or_create_product(
                    line['product_name'],
                    line['price'],
                    company
                )
                order_lines.append((0, 0, {
                    'product_id': product.id,
                    'product_uom_qty': line['quantity'],
                    'price_unit': line['price'],
                    'tax_id': [(6, 0, [])],  # 设置税为0
                }))

            # 计算订单日期 (Delivery Date 往前推 3~15 天)
            delivery_date_obj = datetime.strptime(delivery_date, '%Y-%m-%d')
            order_date = delivery_date_obj - timedelta(days=random.randint(3, 15))

            # 创建订单
            values = {
                'partner_id': partner.id,
                'date_order': order_date,
                'commitment_date': delivery_date,  # 设置送货日期
                'order_line': order_lines,
                'pricelist_id': pricelist.id if pricelist else False,
                'payment_term_id': payment_term.id if payment_term else False,
                'user_id': user.id,
                'company_id': company.id,
                'state': 'draft',
                'partner_shipping_id': self._get_or_create_partner(delivery_address).id,  # 送货地址
                'client_order_ref': customer_reference,  # 客户参考
                'shipping_weight': shipping_weight,  # 运输重量
            }

            sale_order = self.env['sale.order'].create(values)

            # 确认订单
            sale_order.action_confirm()

            return {
                'success': True,
                'sale_order_id': sale_order.id,
                'name': sale_order.name,
                'state': sale_order.state
            }

        except Exception as e:
            _logger.error("创建销售订单失败: %s", str(e))
            return {
                'success': False,
                'error': str(e)
            }

    def _get_or_create_partner(self, partner_name):
        """获取或创建客户，并默认设置为公司类型"""
        Partner = self.env['res.partner']
        partner = Partner.search([('name', '=', partner_name)], limit=1)

        if not partner:
            partner = Partner.create({
                'name': partner_name,
                'customer_rank': 1,  # 设置为客户
                'is_company': True,  # 默认设置为公司类型
            })

        return partner

    def _get_company(self, company_name):
        """获取公司"""
        company = self.env['res.company'].search([
            ('name', '=', company_name)
        ], limit=1)

        if not company:
            raise ValidationError(f'未找到公司: {company_name}')

        return company

    def _get_company_salesperson(self, company):
        """获取公司销售员"""
        user = self.env['res.users'].search([
            ('company_id', '=', company.id),
            ('share', '=', False)
        ], limit=1)

        if not user:
            raise ValidationError(f'公司 {company.name} 未找到销售员')

        return user

    def _get_default_pricelist(self, company):
        """获取默认价格表"""
        return self.env['product.pricelist'].search([
            ('company_id', '=', company.id),
            ('active', '=', True)
        ], limit=1)

    def _get_default_payment_term(self, company):
        """获取默认支付条款 (设置为 End of Following Month)"""
        payment_term = self.env['account.payment.term'].search([
            ('name', 'ilike', 'End of Following Month'),
            ('active', '=', True),
        ], limit=1)

        if not payment_term:
            raise ValidationError('未找到默认支付条款 End of Following Month')

        return payment_term

    def _get_or_create_product(self, product_name, price, company):
        """获取或创建产品"""
        ProductTemplate = self.env['product.template']
        Product = self.env['product.product']

        # 查找产品模板
        template = ProductTemplate.search([
            ('name', '=', product_name)
        ], limit=1)

        if not template:
            # 获取默认计量单位
            uom = self.env['uom.uom'].search([
                ('category_id.name', '=', 'Unit'),
                ('uom_type', '=', 'reference')
            ], limit=1)

            if not uom:
                raise ValidationError('默认计量单位不存在')

            # 创建产品模板
            template = ProductTemplate.create({
                'name': product_name,
                'type': 'consu',
                'list_price': float(price),
                'sale_ok': True,
                'purchase_ok': True,
                'uom_id': uom.id,
                'uom_po_id': uom.id,
                'invoice_policy': 'order',
                'company_id': company.id,
            })

        # 获取产品变体
        product = Product.search([
            ('product_tmpl_id', '=', template.id)
        ], limit=1)

        if not product:
            raise ValidationError(f'无法找到产品 {product_name} 的变体')

        return product