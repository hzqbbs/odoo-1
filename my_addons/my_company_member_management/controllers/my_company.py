from odoo import http, _
from odoo.exceptions import UserError
from odoo.http import request


class MyCompany(http.Controller):

    @http.route('/company/select', type='http', auth='user', website=True)
    def company_select_form(self, **kw):
        companies = request.env['res.company'].sudo().search([])
        return request.render('my_company_member_management.company_select_form', {'companies': companies})

    @http.route('/company/select/submit', type='http', auth='user', methods=['POST'], website=True)
    def company_select_submit(self, **kw):
        user = request.env.user
        company_id = kw.get('company_id')
        company_name = kw.get('company_name')

        if company_id:
            # 用户选择加入现有公司
            user.sudo().join_company(company_id=int(company_id))
        elif company_name:
            # 用户选择创建新公司
            user.sudo().create_and_join_company(company_name=company_name)
        else:
            raise UserError(_("Please provide either company_id or company_name."))

        return request.redirect('/my/home')
