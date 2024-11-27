from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CompanyMemberApproval(models.Model):
    _name = 'company.member.approval'
    _description = 'Company Member Approval'
    _rec_name = 'user_id'
    _order = 'create_date desc'

    user_id = fields.Many2one('res.users', required=True, string="User")
    company_id = fields.Many2one('res.company', required=True, string="Company")
    state = fields.Selection([
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], default='pending', string="Status", required=True)
    approved_by = fields.Many2one('res.users', string="Approved By", readonly=True)
    create_date = fields.Datetime("Created On", readonly=True)

    @api.model
    def request_join_company(self, user_id, company_id):

        # 检查用户是否已经在该公司中
        user = self.env['res.users'].browse(user_id)
        if company_id in user.company_ids.ids:
            raise UserError(_("You are already a member of this company."))

        # 检查公司管理员是否存在
        company_admins = self.env['res.users'].search([
            ('company_id', '=', company_id),
            ('groups_id', 'in', self.env.ref('my_company_member_management.group_single_company_admin').id)
        ])

        if not company_admins:
            raise UserError(_("No admin found for this company. Cannot process join request."))

        # 检查是否存在处理中的申请
        existing_request = self.search([
            ('user_id', '=', user_id),
            ('company_id', '=', company_id),
            ('state', '=', 'pending')
        ], limit=1)

        if existing_request:
            raise UserError(_("You already have a pending join request for this company."))

        return self.create({
            'user_id': user_id,
            'company_id': company_id,
            'state': 'pending',
        })

    @api.model
    def get_pending_approvals(self):
        return self.search([
            ('company_id', '=', self.env.company.id),
            ('state', '=', 'pending')
        ])

    def action_approve(self):
        self.ensure_one()
        if self.state != 'pending':
            raise UserError(_("You can only approve pending requests."))
        if not self.env.user.has_group('my_company_member_management.group_single_company_admin'):
            raise UserError(_("You don't have the rights to approve this request."))
        if self.company_id != self.env.company:
            raise UserError(_("You can only approve requests for your own company."))

        self.write({
            'state': 'approved',
            'approved_by': self.env.user.id
        })
        self.user_id.sudo().write({
            'company_id': self.company_id.id,
            'company_ids': [(4, self.company_id.id)]
        })

    def action_reject(self):
        self.ensure_one()
        if self.state != 'pending':
            raise UserError(_("You can only reject pending requests."))
        if not self.env.user.has_group('my_company_member_management.group_single_company_admin'):
            raise UserError(_("You don't have the rights to reject this request."))
        if self.company_id != self.env.company:
            raise UserError(_("You can only reject requests for your own company."))

        self.write({
            'state': 'rejected',
        })