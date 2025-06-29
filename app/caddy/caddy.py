import os
import re
import logging

from dotenv import load_dotenv
from fastapi import HTTPException
import validators

from app.caddy.caddy_config import CaddyAPIConfigurator

HTTPS_PORT = 443

DEFAULT_ADMIN_URL = 'http://localhost:2019'
DEFAULT_CADDY_FILE = "domains/caddy.json"
DEFAULT_SAAS_UPSTREAM = "example.com:443"
DEFAULT_LOCAL_PORT = f"{HTTPS_PORT}"

# Default domains to configure on startup
DEFAULT_DOMAINS = [
    "*.bytesites.ai",
    "cname.bytesites.ai"
]

# Renderix upstream for default domains
RENDERIX_UPSTREAM = "localhost:3001"

# Namecheap DNS configuration
NAMECHEAP_API_KEY = ""
NAMECHEAP_USER = ""
NAMECHEAP_CLIENT_IP = ""

load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)


def is_valid_domain(domain):
    """Validate domain including wildcard domains"""
    if domain.startswith('*.'):
        # Handle wildcard domains
        base_domain = domain[2:]  # Remove '*.'
        return validators.domain(base_domain)
    else:
        # Handle regular domains
        return validators.domain(domain)


class Caddy:

    def __init__(self):
        self.admin_url = os.environ.get('CADDY_ADMIN_URL', DEFAULT_ADMIN_URL)
        self.config_json_file = os.environ.get(
            'CADDY_CONFIG_FILE', DEFAULT_CADDY_FILE)
        self.saas_upstream = os.environ.get(
            'SAAS_UPSTREAM', DEFAULT_SAAS_UPSTREAM)
        self.local_port = os.environ.get('LOCAL_PORT', DEFAULT_LOCAL_PORT)
        self.disable_https = os.environ.get(
            'DISABLE_HTTPS', 'False').upper() == "TRUE"
        self.renderix_upstream = os.environ.get(
            'RENDERIX_UPSTREAM', RENDERIX_UPSTREAM)

        # Namecheap DNS configuration from environment
        self.namecheap_api_key = os.environ.get(
            'NAMECHEAP_API_KEY', NAMECHEAP_API_KEY)
        self.namecheap_user = os.environ.get('NAMECHEAP_USER', NAMECHEAP_USER)
        self.namecheap_client_ip = os.environ.get(
            'NAMECHEAP_CLIENT_IP', NAMECHEAP_CLIENT_IP)

        logger.info(
            f"Initializing Caddy with renderix upstream: {self.renderix_upstream}")

        self.configurator = CaddyAPIConfigurator(
            api_url=self.admin_url,
            https_port=self.local_port,
            disable_https=self.disable_https
        )

        # Try to load existing config, if not available, initialize with defaults
        if not self.configurator.load_config_from_file(self.config_json_file):
            logger.info(
                "No existing configuration found, initializing with defaults")
            self.configurator.init_config()
            # Add default domains to the initial configuration
            self._add_default_domains()
            # Save the configuration with default domains
            self.configurator.save_config(self.config_json_file)
        else:
            logger.info(
                "Existing configuration found, ensuring default domains are present")
            # If config exists, ensure default domains are present
            self._ensure_default_domains()

    def _add_default_domains(self):
        """Add default domains to the configuration"""
        logger.info(f"Adding default domains: {DEFAULT_DOMAINS}")
        for domain in DEFAULT_DOMAINS:
            try:
                logger.info(
                    f"Adding default domain: {domain} -> {self.renderix_upstream}")
                # Use special method for wildcard domains with TLS
                if domain.startswith('*.'):
                    self.configurator.add_domain_with_tls(
                        domain, self.renderix_upstream, self._get_namecheap_tls_config())
                else:
                    self.configurator.add_domain(
                        domain, self.renderix_upstream)
                logger.info(f"Successfully added default domain: {domain}")
            except Exception as e:
                # Log the error but don't fail the startup
                logger.error(
                    f"Warning: Failed to add default domain {domain}: {e}")

    def _ensure_default_domains(self):
        """Ensure default domains are present in existing configuration"""
        logger.info(
            "Ensuring default domains are present in existing configuration")
        existing_domains = self.configurator.list_domains()
        logger.info(f"Existing domains: {existing_domains}")

        for domain in DEFAULT_DOMAINS:
            if domain not in existing_domains:
                try:
                    logger.info(
                        f"Adding missing default domain: {domain} -> {self.renderix_upstream}")
                    # Use special method for wildcard domains with TLS
                    if domain.startswith('*.'):
                        self.configurator.add_domain_with_tls(
                            domain, self.renderix_upstream, self._get_namecheap_tls_config())
                    else:
                        self.configurator.add_domain(
                            domain, self.renderix_upstream)
                    logger.info(
                        f"Successfully added missing default domain: {domain}")
                except Exception as e:
                    # Log the error but don't fail the startup
                    logger.error(
                        f"Warning: Failed to add missing default domain {domain}: {e}")
            else:
                logger.info(f"Default domain already exists: {domain}")

        # Save the updated configuration
        self.configurator.save_config(self.config_json_file)

    def _get_namecheap_tls_config(self):
        """Get Namecheap DNS TLS configuration"""
        return {
            "dns": {
                "namecheap": {
                    "api_key": self.namecheap_api_key,
                    "user": self.namecheap_user,
                    "api_endpoint": "https://api.namecheap.com/xml.response",
                    "client_ip": self.namecheap_client_ip
                }
            }
        }

    def add_custom_domain(self, domain, upstream):
        if not is_valid_domain(domain):
            raise HTTPException(
                status_code=400, detail=f"{domain} is not a valid domain")

        upstream = upstream or self.saas_upstream
        if not self.configurator.add_domain(domain, upstream):
            raise HTTPException(
                status_code=400, detail=f"Failed to add domain: {domain}")

        self.configurator.save_config(self.config_json_file)

    def remove_custom_domain(self, domain):
        if not is_valid_domain(domain):
            raise HTTPException(
                status_code=400, detail=f"{domain} is not a valid domain")

        if not self.configurator.delete_domain(domain):
            raise HTTPException(
                status_code=400, detail=f"Failed to remove domain: {domain}. Might not be exist.")

        self.configurator.save_config(self.config_json_file)

    def deployed_config(self):
        return self.configurator.config

    def list_domains(self):
        return self.configurator.list_domains()


caddy_server = Caddy()
