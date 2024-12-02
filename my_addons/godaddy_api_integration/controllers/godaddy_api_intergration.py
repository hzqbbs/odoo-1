import json
from odoo import http
from odoo.http import request


class GoDaddyAPIController(http.Controller):

    @http.route('/api/godaddy/check_domain', type='json', auth='public', methods=['POST'], csrf=False)
    def check_domain_availability(self, **kwargs):
        """
        检查域名是否可用
        请求体示例：
        {
            "domain_name": "example.com",
            "api_key": "your_api_key",
            "api_secret": "your_api_secret"
        }
        """
        domain_name = kwargs.get('domain_name')
        api_key = kwargs.get('api_key')
        api_secret = kwargs.get('api_secret')

        if not domain_name or not api_key or not api_secret:
            return {
                "error": "缺少必要参数 (domain_name, api_key 或 api_secret)"
            }

        try:
            # 调用模型方法
            result = request.env['godaddy.api'].sudo().check_domain_availability(domain_name, api_key, api_secret)
            return result
        except Exception as e:
            return {
                "error": f"检查域名失败: {str(e)}"
            }

    @http.route('/api/godaddy/register_domain', type='json', auth='public', methods=['POST'], csrf=False)
    def register_domain(self, **kwargs):
        """
        注册域名
        请求体示例：
        {
            "domain_name": "example.com",
            "api_key": "your_api_key",
            "api_secret": "your_api_secret",
            "years": 1,
            "contact_info": { ... }
        }
        """
        domain_name = kwargs.get('domain_name')
        api_key = kwargs.get('api_key')
        api_secret = kwargs.get('api_secret')
        years = kwargs.get('years', 1)
        contact_info = kwargs.get('contact_info')

        if not domain_name or not api_key or not api_secret or not contact_info:
            return {
                "error": "缺少必要参数 (domain_name, api_key, api_secret 或 contact_info)"
            }

        try:
            # 调用模型方法
            result = request.env['godaddy.api'].sudo().register_domain(
                domain_name, years, contact_info, api_key, api_secret
            )
            return result
        except Exception as e:
            return {
                "error": f"域名注册失败: {str(e)}"
            }