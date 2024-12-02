from datetime import datetime, timezone

import requests
from odoo import models, api, fields
from odoo.tools import json


class GodaddyAPI(models.AbstractModel):
    _name = 'godaddy.api'
    _description = 'GoDaddy API Integration'

    @api.model
    def check_domain_availability(self, domain_name, api_key, api_secret):
        """
        检查域名是否可用
        :param domain_name: 要检查的域名
        :param api_key: GoDaddy API 密钥
        :param api_secret: GoDaddy API 密钥
        :return: 域名可用性信息
        """
        base_url = "https://api.ote-godaddy.com"
        endpoint = f"{base_url}/v1/domains/available"
        headers = {
            "Authorization": f"sso-key {api_key}:{api_secret}",
            "Content-Type": "application/json"
        }
        params = {"domain": domain_name, "checkType": "FULL"}

        response = requests.get(endpoint, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            return {
                "domain_name": domain_name,
                "available": data.get('available', False),
                "price": data.get('price', 0) / 1000000,  # 通常价格以微单位返回
                "currency": data.get('currency', 'USD')
            }
        else:
            raise ValueError(f"API请求失败: {response.status_code}, {response.text}")

    @api.model
    def register_domain(self, domain_name, years, contact_info, api_key, api_secret):
        """
        注册域名
        :param domain_name: 要注册的域名
        :param years: 注册年限
        :param contact_info: 域名注册联系人信息
        :param api_key: GoDaddy API 密钥
        :param api_secret: GoDaddy API 密钥
        :return: 注册结果
        """
        base_url = "https://api.ote-godaddy.com"
        endpoint = f"{base_url}/v1/domains/purchase"
        headers = {
            "Authorization": f"sso-key {api_key}:{api_secret}",
            "Content-Type": "application/json"
        }
        payload = {
            "domain": domain_name,
            "period": years,
            "nameServers": ["ns1.godaddy.com", "ns2.godaddy.com"],
            "renewAuto": True,
            "privacy": False,
            "contactAdmin": contact_info,
            "contactBilling": contact_info,
            "contactRegistrant": contact_info,
            "contactTech": contact_info,
            "consent": {
                "agreementKeys": ["DNRA"],
                "agreedAt": datetime.now(timezone.utc).isoformat(timespec='seconds').replace("+00:00", "Z"),# 转换为 UTC 时间并添加 Z
                "agreedBy": contact_info.get("email")
            }
        }

        response = requests.post(endpoint, headers=headers, json=payload)
        if response.status_code in [200, 201]:
            return response.json()
        else:
            raise ValueError(f"域名注册失败: {response.status_code}, {response.text}")