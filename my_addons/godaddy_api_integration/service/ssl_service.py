import logging
import subprocess

_logger = logging.getLogger(__name__)

class SSLService:
    @staticmethod
    def request_ssl_certificate(domain):
        """
        Request SSL certificate for a single domain using Certbot in WSL.
        """
        try:
            wsl_command = [
                'wsl', 'sudo', 'certbot', 'certonly', '--webroot',
                '-w', '/var/www/html',  # Replace with your WSL webroot directory
                '-d', domain,
                '--non-interactive', '--agree-tos',
                '--email', 'hzqz@yeah.net'  # Replace with your email
            ]
            subprocess.run(wsl_command, check=True)
            _logger.info("Certbot successfully requested SSL certificate for domain: %s", domain)
        except Exception as e:
            _logger.error("Certbot command failed in WSL: %s", e)
            raise

    @staticmethod
    def generate_nginx_config(domain):
        """
        Generate a separate Nginx configuration for the given domain.
        """
        try:
            # Nginx configuration content for the domain
            nginx_config = f"""
            server {{
                listen 443 ssl;
                server_name {domain};

                ssl_certificate /etc/letsencrypt/live/{domain}/fullchain.pem;
                ssl_certificate_key /etc/letsencrypt/live/{domain}/privkey.pem;

                location / {{
                    proxy_pass http://127.0.0.1:8069;
                    proxy_set_header Host $host;
                    proxy_set_header X-Real-IP $remote_addr;
                    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
                    proxy_set_header X-Forwarded-Proto $scheme;
                }}
            }}
            """

            # Path to Nginx configuration file
            config_path = f'/etc/nginx/sites-available/{domain}'
            wsl_path = f'\\\\wsl$\\Ubuntu\\etc\\nginx\\sites-available\\{domain}'

            # Write the configuration file directly in WSL
            with open(wsl_path, 'w') as config_file:
                config_file.write(nginx_config)

            # Enable the site in Nginx
            subprocess.run(['wsl', 'sudo', 'ln', '-s', config_path, f'/etc/nginx/sites-enabled/{domain}'], check=True)
            _logger.info("Nginx configuration generated and enabled for domain: %s", domain)

        except Exception as e:
            _logger.error("Failed to generate Nginx configuration in WSL: %s", e)
            raise

    @staticmethod
    def reload_nginx():
        """
        Reload Nginx to apply new configurations.
        """
        try:
            subprocess.run(['wsl', 'sudo', 'systemctl', 'reload', 'nginx'], check=True)
            _logger.info("Nginx reloaded successfully.")
        except subprocess.CalledProcessError as e:
            _logger.error("Failed to reload Nginx: %s", e)
            raise

    @staticmethod
    def setup_ssl(domain):
        """
        Automates the SSL setup process for a single domain using WSL Certbot and Nginx.
        """
        domain = domain.strip()  # Remove any extra spaces
        try:
            _logger.info("Requesting SSL certificate for domain: %s", domain)

            # Step 1: Request SSL certificate
            SSLService.request_ssl_certificate(domain)

            # Step 2: Generate Nginx configuration
            SSLService.generate_nginx_config(domain)

            # Step 3: Reload Nginx
            SSLService.reload_nginx()

            _logger.info("SSL setup completed successfully for domain: %s", domain)
            return {'status': 'success', 'message': f"SSL setup completed for domain: {domain}"}

        except subprocess.CalledProcessError as e:
            _logger.error("Command failed: %s", e)
            return {'status': 'failed', 'message': str(e)}

        except Exception as e:
            _logger.error("Failed to set up SSL: %s", e)
            return {'status': 'failed', 'message': str(e)}