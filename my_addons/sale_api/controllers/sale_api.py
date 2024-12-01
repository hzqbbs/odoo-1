# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import json
from datetime import datetime, timedelta


class SaleOrderAPIController(http.Controller):

    @http.route('/api/create_sale_order', type='json', auth='user', methods=['POST'], csrf=False)
    def create_sale_order(self, **kwargs):
        """
        创建销售订单的 REST API

        JSON 请求参数:
            - partner_name (str): 客户名称
            - company_name (str): 公司名称
            - order_lines_data (list): 订单行数据，每项为字典:
                {
                    "product_name": str,
                    "quantity": float,
                    "price": float
                }
            - delivery_address (str): 送货地址
            - delivery_date (str): 送货日期 (格式: YYYY-MM-DD)
            - shipping_weight (float): 运输重量
            - customer_reference (str): 客户参考信息

        返回:
            JSON 响应:
                {
                    "success": True,
                    "sale_order_id": int,
                    "name": str,
                    "state": str
                }
        """
        try:
            # 获取请求参数
            partner_name = kwargs.get('partner_name')
            company_name = kwargs.get('company_name')
            order_lines_data = kwargs.get('order_lines_data', [])
            delivery_address = kwargs.get('delivery_address')
            delivery_date = kwargs.get('delivery_date')
            shipping_weight = kwargs.get('shipping_weight', 0.0)
            customer_reference = kwargs.get('customer_reference')

            # 调用已有的 `sale.order.api` 模型方法
            sale_order_api = request.env['sale.order.api'].sudo()
            result = sale_order_api.create_sale_order(
                partner_name,
                company_name,
                order_lines_data,
                delivery_address,
                delivery_date,
                shipping_weight,
                customer_reference
            )
            return result

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }