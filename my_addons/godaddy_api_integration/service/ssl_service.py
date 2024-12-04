import hashlib
import logging
import os
import subprocess
from datetime import datetime, timezone

from OpenSSL import crypto

_logger = logging.getLogger(__name__)

class SSLService:
    @staticmethod
    def is_certificate_valid(domain):
        """
        Check if the SSL certificate for the given domain exists and is valid.
        """
        cert_path = f"/etc/letsencrypt/live/{domain}/fullchain.pem"
        if not os.path.exists(cert_path):
            return False  # Certificate does not exist, needs creation

        try:
            with open(cert_path, "rb") as cert_file:
                cert_data = crypto.load_certificate(crypto.FILETYPE_PEM, cert_file.read())
                not_after = cert_data.get_notAfter().decode("utf-8")  # Expiration date
                expiration_date = datetime.strptime(not_after, "%Y%m%d%H%M%SZ").replace(tzinfo=timezone.utc)
                return expiration_date > datetime.now(timezone.utc)  # Use timezone-aware UTC datetime
        except Exception as e:
            _logger.error("Failed to validate certificate for domain %s: %s", domain, e)
            return False

    @staticmethod
    def request_ssl_certificate(domain):
        """
        Request an SSL certificate for a single domain using Certbot in Linux.
        """
        if SSLService.is_certificate_valid(domain):
            _logger.info("Certificate for domain %s is already valid. Skipping request.", domain)
            return  # Skip certificate request

        try:
            certbot_command = [
                'sudo', 'certbot', 'certonly', '--webroot',
                '-w', '/var/www/html',
                '-d', domain,
                '--non-interactive', '--agree-tos',
                '--email', 'hzqz@yeah.net'
            ]
            subprocess.run(certbot_command, check=True)
            _logger.info("Certbot successfully requested SSL certificate for domain: %s", domain)
        except Exception as e:
            _logger.error("Certbot command failed: %s", e)
            raise

    @staticmethod
    def is_nginx_config_changed(domain, config_content):
        """
        Check if the Nginx configuration file needs to be updated.
        """
        config_path = f"/etc/nginx/sites-available/{domain}"
        if not os.path.exists(config_path):
            return True  # Configuration file does not exist, needs creation

        try:
            with open(config_path, "rb") as existing_file:
                existing_content = existing_file.read()
                return hashlib.sha256(existing_content).hexdigest() != \
                       hashlib.sha256(config_content.encode("utf-8")).hexdigest()  # Compare hashes
        except Exception as e:
            _logger.error("Failed to check existing Nginx configuration: %s", e)
            return True  # Assume configuration needs to be updated if an error occurs

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

            # Check if configuration needs to be updated
            if not SSLService.is_nginx_config_changed(domain, nginx_config):
                _logger.info("Nginx configuration for domain %s is already up-to-date. Skipping update.", domain)
                return  # Skip configuration update

            # Path to Nginx configuration file
            config_path = f'/etc/nginx/sites-available/{domain}'

            # Write the configuration file
            with open(config_path, 'w') as config_file:
                config_file.write(nginx_config)

            # Enable the site in Nginx
            subprocess.run(['sudo', 'ln', '-sf', config_path, f'/etc/nginx/sites-enabled/{domain}'], check=True)
            _logger.info("Nginx configuration generated and enabled for domain: %s", domain)

        except Exception as e:
            _logger.error("Failed to generate Nginx configuration: %s", e)
            raise

    @staticmethod
    def remove_default_site():
        """
        Remove the default Nginx site configuration if it exists.
        """
        default_site = '/etc/nginx/sites-enabled/default'
        if os.path.islink(default_site):  # Check if the default site is a symbolic link
            try:
                subprocess.run(['sudo', 'unlink', default_site], check=True)
                _logger.info("Default Nginx site configuration removed.")
            except subprocess.CalledProcessError as e:
                _logger.warning("Failed to remove default Nginx site configuration: %s", e)
        else:
            _logger.info("Default Nginx site configuration does not exist. Skipping removal.")

    @staticmethod
    def reload_nginx():
        """
        Reload Nginx to apply new configurations.
        """
        try:
            subprocess.run(['sudo', 'systemctl', 'reload', 'nginx'], check=True)
            _logger.info("Nginx reloaded successfully.")
        except subprocess.CalledProcessError as e:
            _logger.error("Failed to reload Nginx: %s", e)
            raise

    @staticmethod
    def setup_ssl(domain):
        """
        Automates the SSL setup process for a single domain using Certbot and Nginx.
        """
        domain = domain.strip()  # Remove any extra spaces
        try:
            _logger.info("Requesting SSL certificate for domain: %s", domain)

            # Step 1: Request SSL certificate only if needed
            certificate_updated = not SSLService.is_certificate_valid(domain)
            if certificate_updated:
                SSLService.request_ssl_certificate(domain)

            # Step 2: Generate Nginx configuration only if changes are needed
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
            config_updated = SSLService.is_nginx_config_changed(domain, nginx_config)
            if config_updated:
                SSLService.generate_nginx_config(domain)

            # Step 3: Remove default Nginx site configuration (if needed)
            SSLService.remove_default_site()

            # Step 4: Reload Nginx only if there were changes
            if certificate_updated or config_updated:
                SSLService.reload_nginx()

            _logger.info("SSL setup completed successfully for domain: %s", domain)
            return {'status': 'success', 'message': f"SSL setup completed for domain: {domain}"}

        except subprocess.CalledProcessError as e:
            _logger.error("Command failed: %s", e)
            return {'status': 'failed', 'message': str(e)}

        except Exception as e:
            _logger.error("Failed to set up SSL: %s", e)
            return {'status': 'failed', 'message': str(e)}