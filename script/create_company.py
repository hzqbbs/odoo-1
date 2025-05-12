import xmlrpc.client
import logging
from typing import Dict, Any


class OdooException(Exception):
    pass


class OdooManager:
    def __init__(self, url: str, db: str, admin_user: str, admin_password: str):
        self.config = {
            'url': url,
            'db': db,
            'admin_user': admin_user,
            'admin_password': admin_password
        }
        self.logger = self._setup_logger()
        self.common, self.models = self._connect()
        self.uid = self._authenticate()

        # 使用超级管理员权限
        self.sudo_uid = 2  # 超级管理员的固定ID

    def _setup_logger(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)

    def _connect(self):
        try:
            common = xmlrpc.client.ServerProxy(f"{self.config['url']}/xmlrpc/2/common")
            models = xmlrpc.client.ServerProxy(f"{self.config['url']}/xmlrpc/2/object")
            return common, models
        except Exception as e:
            raise OdooException(f"连接Odoo服务器失败: {str(e)}")

    def _authenticate(self):
        try:
            uid = self.common.authenticate(
                self.config['db'],
                self.config['admin_user'],
                self.config['admin_password'],
                {}
            )
            if not uid:
                raise OdooException("管理员认证失败")

            # 验证管理员权限
            self.logger.info("验证管理员权限...")
            admin_access = self.models.execute_kw(
                self.config['db'],
                uid,
                self.config['admin_password'],
                'res.users',
                'has_group',
                ['base.group_system']
            )

            if not admin_access:
                raise OdooException("当前用户没有系统管理员权限")

            return uid
        except Exception as e:
            raise OdooException(f"认证失败: {str(e)}")

    def execute_kw(self, model: str, method: str, args: list, context: Dict = None, sudo: bool = False):
        """
        执行模型方法，支持 sudo 模式。
        :param sudo: 是否使用超级管理员权限
        """
        try:
            if context is None:
                context = {}
            # 如果 sudo 为 True，则使用超级管理员 ID
            uid = self.sudo_uid if sudo else self.uid
            return self.models.execute_kw(
                self.config['db'],
                uid,
                self.config['admin_password'],
                model,
                method,
                args,
                context
            )
        except Exception as e:
            self.logger.error(f"执行{model}.{method}失败: {str(e)}")
            raise OdooException(f"操作执行失败: {str(e)}")

    def create_company_first(self, company_data: Dict[str, Any]) -> int:
        """先创建公司"""
        try:
            self.logger.info("开始创建公司...")

            # 1. 确保必要字段存在
            base_company_data = {
                "name": company_data["name"],
                "email": company_data.get("email", False),
                "phone": company_data.get("phone", False),
                "website": company_data.get("website", False),
            }

            # 2. 获取可用货币
            currency = self.execute_kw(
                'res.currency',
                'search_read',
                [[['active', '=', True]]],
                {'fields': ['id', 'name'], 'limit': 1},
                sudo=True  # 使用超级管理员权限
            )
            if currency:
                base_company_data['currency_id'] = currency[0]['id']

            # 3. 创建公司
            company_id = self.execute_kw('res.company', 'create', [base_company_data], sudo=True)

            # 4. 如果有其他额外字段，在公司创建后更新
            additional_fields = {k: v for k, v in company_data.items()
                                 if k not in base_company_data and k != 'currency_id'}
            if additional_fields:
                self.execute_kw(
                    'res.company',
                    'write',
                    [[company_id], additional_fields],
                    sudo=True
                )

            return company_id
        except Exception as e:
            raise OdooException(f"创建公司失败: {str(e)}")

    def create_user_and_company(
            self,
            user_data: Dict[str, Any],
            company_data: Dict[str, Any]
    ) -> Dict[str, int]:
        try:
            # 1. 先创建公司
            company_id = self.create_company_first(company_data)
            self.logger.info(f"公司创建成功，ID: {company_id}")

            # 2. 获取指定的权限组
            group_ids = []
            external_ids = [
                'my_company_member_management.group_single_company_admin',
                'my_company_member_management.group_single_company_user',
                'base.group_multi_company',
            ]
            for ext_id in external_ids:
                module, xml_id = ext_id.split('.')
                group_data = self.execute_kw(
                    'ir.model.data',
                    'search_read',
                    [[
                        ('module', '=', module),
                        ('name', '=', xml_id),
                        ('model', '=', 'res.groups')
                    ]],
                    {'fields': ['res_id']},
                    sudo=True
                )
                if group_data:
                    group_ids.append(group_data[0]['res_id'])

            if not group_ids:
                raise OdooException("无法获取必要的权限组")

            # 3. 先创建没有任何组的用户
            base_user_data = {
                'name': user_data['name'],
                'login': user_data['login'],
                'password': user_data['password'],
                'email': user_data.get('email'),
                'company_id': company_id,
                'company_ids': [(6, 0, [company_id])],
                'groups_id': [(6, 0, [])]  # 清空所有组
            }

            # 4. 创建用户
            self.logger.info("开始创建用户...")
            user_id = self.execute_kw(
                'res.users',
                'create',
                [base_user_data],
                {
                    'context': {
                        'no_reset_password': True,
                        'no_default_access_rights': True
                    }
                },
                sudo=True
            )

            # 5. 移除所有默认组并只添加指定的组
            self.execute_kw(
                'res.users',
                'write',
                [[user_id], {
                    'groups_id': [
                        (5, 0, 0),  # 清除所有现有组
                        (6, 0, group_ids)  # 只添加指定的组
                    ]
                }],
                sudo=True
            )

            # 6. 验证用户组设置
            user_groups = self.execute_kw(
                'res.users',
                'read',
                [[user_id]],
                {'fields': ['groups_id']},
                sudo=True
            )

            actual_groups = set(user_groups[0]['groups_id'])
            expected_groups = set(group_ids)

            if actual_groups != expected_groups:
                self.logger.warning(f"用户组不匹配。预期: {expected_groups}, 实际: {actual_groups}")
                # 再次尝试强制设置正确的组
                self.execute_kw(
                    'res.users',
                    'write',
                    [[user_id], {
                        'groups_id': [
                            (5, 0, 0),  # 清除所有组
                            (6, 0, group_ids)  # 重新设置指定的组
                        ]
                    }],
                    sudo=True
                )

            return {
                'user_id': user_id,
                'company_id': company_id
            }

        except Exception as e:
            self.logger.error(f"创建失败: {str(e)}")
            raise OdooException(f"创建用户和公司失败: {str(e)}")


# 使用示例
if __name__ == "__main__":
    try:
        # 初始化管理器
        odoo = OdooManager(
            url="http://localhost:8069",
            db="odoo_db",
            admin_user="admin",
            admin_password="admin"
        )

        uname = "4@example.com"

        # 准备公司数据
        company_data = {
            "name": uname,
            "email": "company@example.com",
            "phone": "+1234567890",
            "website": "http://www.example.com",
        }

        # 准备用户数据
        user_data = {
            "name": uname,
            "login": uname,
            "password": uname,
            "email": uname,  # 添加email字段
        }

        # 执行创建
        result = odoo.create_user_and_company(user_data, company_data)
        print(f"创建成功! 用户ID: {result['user_id']}, 公司ID: {result['company_id']}")

    except OdooException as e:
        print(f"操作失败: {str(e)}")
    except Exception as e:
        print(f"未知错误: {str(e)}")