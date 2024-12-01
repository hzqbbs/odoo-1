from odoo import models, fields, api, exceptions


class OdooException(Exception):
    """Custom Exception for Odoo Manager."""
    pass


class OdooManager(models.Model):
    _name = "custom.odoo.manager"
    _description = "Custom Odoo Manager"

    @api.model
    def create_company(self, company_data):
        try:
            base_company_data = {
                "name": company_data["name"],
                "email": company_data.get("email", False),
                "phone": company_data.get("phone", False),
                "website": company_data.get("website", False),
            }

            # Get active currency
            currency = self.env["res.currency"].search_read(
                [("active", "=", True)], ["id"], limit=1
            )
            if currency:
                base_company_data["currency_id"] = currency[0]["id"]

            company = self.env["res.company"].create(base_company_data)
            return company.id
        except Exception as e:
            raise exceptions.UserError(f"创建公司失败: {str(e)}")

    @api.model
    def create_user_and_company(self, user_data, company_data):
        try:
            # Step 1: Create company
            company_id = self.create_company(company_data)

            # Step 2: Get required groups
            external_ids = [
                "base.group_user",
                "base.group_multi_company",
            ]

            group_ids = []
            for ext_id in external_ids:
                group = self.env.ref(ext_id, False)
                if group:
                    group_ids.append(group.id)
                else:
                    self.env.cr.rollback()
                    raise exceptions.UserError(f"权限组 {ext_id} 不存在")

            # Step 3: Create user without company
            user_vals = {
                "name": user_data["name"],
                "login": user_data["login"],
                "password": user_data["password"],
                "email": user_data.get("email"),
                "groups_id": [(6, 0, group_ids)],
            }

            user = self.env["res.users"].create(user_vals)

            # Step 4: Update user's company information
            user.write(
                {
                    "company_id": company_id,
                    "company_ids": [(6, 0, [company_id])],
                }
            )

            # Step 5: Assign sales module Administrator group
            sales_admin_group = self.env.ref("sales_team.group_sale_manager", False)
            if sales_admin_group:
                user.groups_id = [(4, sales_admin_group.id)]

            # Verify user information
            user_info = self.env["res.users"].search_read(
                [("id", "=", user.id)],
                ["company_id", "company_ids", "groups_id"],
            )
            if user_info:
                self.env.cr.commit()
                return {"user_id": user.id, "company_id": company_id}
            else:
                raise exceptions.UserError("用户创建失败，无法验证用户信息")

        except Exception as e:
            raise exceptions.UserError(f"创建用户和公司失败: {str(e)}")