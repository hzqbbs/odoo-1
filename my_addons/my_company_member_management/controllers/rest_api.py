import json
from odoo import http
from odoo.http import request, Response

class OdooManagerRestAPI(http.Controller):

    @http.route('/api/create_user_and_company', type='json', auth='user', methods=['POST'], csrf=False)
    def create_user_and_company(self, **kwargs):
        """
        REST API Endpoint to create a user and a company.
        Request Payload:
        {
            "user_data": {
                "name": "Username",
                "login": "user_login",
                "password": "user_password",
                "email": "user_email"
            },
            "company_data": {
                "name": "Company Name",
                "email": "company_email",
                "phone": "company_phone",
                "website": "company_website"
            }
        }
        """
        try:
            # Extract data from the request
            user_data = kwargs.get('user_data', {})
            company_data = kwargs.get('company_data', {})

            if not user_data or not company_data:
                return Response(
                    json.dumps({"error": "Missing user_data or company_data"}),
                    status=400,
                    content_type="application/json",
                )

            # Call the model method
            odoo_manager = request.env["custom.odoo.manager"]
            result = odoo_manager.sudo().create_user_and_company(user_data, company_data)

            return {"status": "success", "data": result}

        except Exception as e:
            return Response(
                json.dumps({"status": "error", "message": str(e)}),
                status=500,
                content_type="application/json",
            )