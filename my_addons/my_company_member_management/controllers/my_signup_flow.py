from odoo.addons.auth_signup.controllers.main import AuthSignupHome
from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


class CustomAuthSignupHome(AuthSignupHome):
    @http.route('/web/signup', type='http', auth='public', website=True, sitemap=False)
    def web_auth_signup(self, *args, **kw):
        response = super().web_auth_signup(*args, **kw)
        if 'error' not in response.qcontext and request.params.get('login'):
            return request.redirect('/company/select')
        return response

    @http.route('/web/login', type='http', auth="public", website=True)
    def web_login(self, redirect=None, **kw):
        _logger.info("Entering web_login with redirect: %s", redirect)  # Use the 'redirect' argument directly

        # Let the base controller handle the login process (includes redirect handling)
        response = super().web_login(redirect=redirect, **kw)

        # Check for POST and successful login
        if request.httprequest.method == 'POST' and request.params.get('login_success', False):
            try:  # Add try-except block for error handling
                if request.session.uid:
                    user = request.env['res.users'].browse(request.session.uid)
                    temporary_company = request.env['res.company'].search([('name', '=', 'Temporary Company')], limit=1)
                    if user.company_id.id == temporary_company.id:
                        return request.redirect('/company/select')
            except Exception as e:  # Catch and log potential errors
                _logger.error("Error checking company after login: %s", e)

        _logger.info("Proceeding with default web_login response")
        return response
