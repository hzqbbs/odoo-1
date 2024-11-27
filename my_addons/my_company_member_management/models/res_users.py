from odoo import models, api, _, fields, SUPERUSER_ID
import logging

from odoo.exceptions import UserError, AccessError

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def get_custom_users_domain(self):
        return [
            '|',
            ('groups_id', 'in', [self.env.ref('base.group_system').id]),
            ('company_id', '=', self.env.user.company_id.id)
        ]

    @api.model
    def action_users_custom(self):
        action = self.env.ref('my_company_member_management.action_users_custom').read()[0]
        action['domain'] = self.get_custom_users_domain()
        return action

    def write(self, vals):
        if 'company_id' in vals or 'company_ids' in vals:
            for user in self:
                # 跳过对超级用户的检查
                if user.id == SUPERUSER_ID:
                    continue
                # 检查是否有待审批的请求
                pending_approval = self.env['company.member.approval'].search([
                    ('user_id', '=', user.id),
                    ('state', '=', 'pending')
                ])
                if pending_approval:
                    # 如果有待审批的请求，阻止直接修改公司
                    raise UserError(_("User %s cannot change company until the request is approved.") % user.name)
        return super(ResUsers, self).write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        # 确保vals_list是列表
        if not vals_list:
            return self.browse()

        # 处理每条记录
        for vals in vals_list:
            # 检查是否已有用户存在
            user_count = self.env['res.users'].search_count([])
            is_first_user = user_count == 0

            # 检查是否存在临时公司
            temporary_company = self.env['res.company'].search([('name', '=', 'Temporary Company')], limit=1)
            if not temporary_company:
                # 创建临时公司
                temporary_company = self.env['res.company'].create({
                    'name': 'Temporary Company',
                })

            # 分配临时公司
            vals['company_id'] = temporary_company.id
            vals['company_ids'] = [(4, temporary_company.id)]

        # 批量创建用户
        users = super(ResUsers, self).create(vals_list)

        # 获取需要的组
        group_single_company_user = self.env.ref('my_company_member_management.group_single_company_user')
        multi_company_group = self.env.ref('base.group_multi_company')

        # 获取所有用户类型组
        user_types = self.env['res.groups'].search(
            [('category_id', '=', self.env.ref('base.module_category_user_type').id)])

        # 为所有新创建的用户更新权限组
        for user in users:
            user.write({
                'groups_id': [
                                 (3, group.id) for group in user_types  # 移除所有用户类型组
                             ] + [
                                 (4, group_single_company_user.id),
                                 (4, multi_company_group.id),
                             ]
            })

        return users

    def create_and_join_company(self, company_name):
        """
        这个方法创建一个新公司，并将当前用户设置为管理员。

        :param company_name: 新公司的名称。
        """
        self.ensure_one()  # 确保只处理一个用户

        # 创建新公司
        company = self.env['res.company'].create({'name': company_name})

        # 将用户添加到管理员组
        admin_group = self.env.ref('my_company_member_management.group_single_company_admin')

        # 查找临时公司
        temporary_company = self.env['res.company'].search([('name', '=', 'Temporary Company')], limit=1)

        # 添加更多必要的权限组
        groups_to_add = [
            admin_group,
        ]

        # 更新用户信息
        vals_to_write = {
            'company_id': company.id,  # 设置新公司为主公司
            'company_ids': [(4, company.id), (3, temporary_company.id)],  # 添加新公司，移除临时公司
            'groups_id': [(4, group.id) for group in groups_to_add]
        }

        self.write(vals_to_write)

        # 刷新用户的访问权限
        self.env.registry.clear_cache()

        return company

    def join_company(self, company_id):
        return self.env['company.member.approval'].request_join_company(self.id, company_id)

    def approve_member(self, approval_id):
        approval = self.env['company.member.approval'].browse(approval_id)
        if approval and approval.state == 'pending':
            if not self.has_group('my_company_member_management.group_single_company_user'):
                raise UserError(_("You don't have the rights to approve this request."))
            if approval.company_id != self.company_id:
                raise UserError(_("You can only approve requests for your own company."))

            approval.write({
                'state': 'approved',
                'approved_by': self.id
            })
            approval.user_id.sudo().write({
                'company_id': approval.company_id.id,
                'company_ids': [(4, approval.company_id.id)]
            })
            # 发送通知给用户，告知其请求已被批准
