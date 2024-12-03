from datetime import datetime, timezone

import requests
import logging
from odoo import models, api, fields
from odoo.addons.godaddy_api_integration.service.ssl_service import SSLService
from odoo.tools import json

_logger = logging.getLogger(__name__)

def _configure_dns(domain_name, target_ip, api_key, api_secret):
    """
    配置域名的 DNS 记录
    :param domain_name: 要配置的域名，例如 "example.com"
    :param api_key: GoDaddy API 的密钥
    :param api_secret: GoDaddy API 的密钥密文
    """
    # 检查域名是否合法
    if not domain_name:
        raise ValueError("Domain name cannot be empty.")

    # 设置 API 请求的基本信息
    base_url = "https://api.godaddy.com"
    endpoint = f"{base_url}/v1/domains/{domain_name}/records"
    headers = {
        "Authorization": f"sso-key {api_key}:{api_secret}",
        "Content-Type": "application/json"
    }

    # 配置 DNS 记录
    payload = [
        {
            "type": "CNAME",
            "name": "@",  # 将根域名指向 ngrok 地址
            "data": "7c78-113-89-235-115.ngrok-free.app",  # 将根域名指向目标 IP
            "ttl": 600
        },
        {
            "type": "CNAME",
            "name": "www",  # 将 www 子域指向根域名
            "data": "@",
            "ttl": 600
        }
    ]

    # 发送 API 请求
    try:
        response = requests.put(endpoint, headers=headers, json=payload)
        if response.status_code in [200, 201]:
            _logger.info(f"DNS configured successfully for domain: {domain_name}")
            return response.json()
        else:
            _logger.error(f"Failed to configure DNS: {response.status_code}, {response.text}")
            _logger.error(f"Request payload: {payload}")
            raise ValueError(f"DNS configuration failed: {response.status_code}, {response.text}")
    except requests.RequestException as e:
        _logger.exception("An error occurred while making the API request.")
        raise ValueError(f"An error occurred while configuring DNS: {str(e)}")

def _register_domain(domain_name, years, contact_info, api_key, api_secret):
    """
    使用 GoDaddy API 注册域名
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
            "agreedAt": datetime.now(timezone.utc).isoformat(timespec='seconds').replace("+00:00", "Z"),
            "agreedBy": contact_info.get("email")
        }
    }

    response = requests.post(endpoint, headers=headers, json=payload)
    if response.status_code in [200, 201]:
        return response.json()
    else:
        raise ValueError(f"域名注册失败: {response.status_code}, {response.text}")


def configure_ssl(domain_name):
    """
    调用 SSL Service 为域名配置 SSL
    """
    # 测试用
    domain_name = domain_name.strip() or "globexb2b.co"  # 确保域名没有多余空格

    try:
        # 调用 SSLService 的 setup_ssl 方法
        result = SSLService.setup_ssl(domain_name)

        if result['status'] == 'success':
            _logger.info(f"SSL configured successfully for domain: {domain_name}")
        else:
            _logger.error(f"Failed to configure SSL for domain: {domain_name}. Reason: {result['message']}")

        return result  # 返回结果供调用者使用

    except Exception as e:
        _logger.error(f"An error occurred while configuring SSL for domain: {domain_name}: {e}")
        raise


class GodaddyAPI(models.AbstractModel):
    _name = 'godaddy.api'
    _description = 'GoDaddy API Integration'

    @api.model
    def check_domain_availability(self, domain_name, api_key, api_secret):
        """
        检查域名是否可用
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

            _logger.info(f"域名检查完毕: {data}")
            return {
                "domain_name": domain_name,
                "available": data.get('available', False),
                "price": data.get('price', 0) / 1000000,  # 通常价格以为单位返回
                "currency": data.get('currency', 'USD')
            }
        else:
            raise ValueError(f"API请求失败: {response.status_code}, {response.text}")

    @api.model
    def register_domain(self, domain_name, years, contact_info, api_key, api_secret, target_ip):
        """
        注册域名并配置 DNS
        """
        # Step 1: 注册域名
        _register_domain(domain_name, years, contact_info, api_key, api_secret)

        # Step 2: 配置 DNS
        # 在生产环境中访问部分域 API 可能需要满足某些条件：可用性 API：仅限于拥有 50 个或更多域的帐户。
        # 管理和 DNS API：仅限于拥有 10 个或更多域和/或活跃的折扣域俱乐部 - 高级会员计划的帐户。
        # _configure_dns(domain_name, target_ip, api_key, api_secret)

        # Step 3: 调用 SSL 自动注册模块
        _logger.info(f"Configuring SSL for domain: {domain_name}")
        configure_ssl(domain_name)

