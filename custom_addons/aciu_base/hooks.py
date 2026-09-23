# Part of ACIU Odoo customization.

import base64
import logging

from odoo import SUPERUSER_ID, api
from odoo.tools.misc import file_open

_logger = logging.getLogger(__name__)

_LOGO_RELPATH = 'aciu_base/static/img/aciu_logo.jpeg'


def _load_aciu_logo_b64():
    with file_open(_LOGO_RELPATH, 'rb') as logo_file:
        return base64.b64encode(logo_file.read())


def apply_aciu_branding(env):
    """Set ACIU logo on companies (login / platform logo)."""
    logo = _load_aciu_logo_b64()
    companies = env['res.company'].search([('is_aciu_company', '=', True)])
    if companies:
        companies.write({'logo': logo})
        _logger.info('ACIU branding: logo set on %s companies', len(companies))

    # Login logo uses the superuser's company when no session company is set.
    main_company = env.ref('base.main_company', raise_if_not_found=False)
    if main_company and main_company not in companies:
        main_company.logo = logo


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    apply_aciu_branding(env)
