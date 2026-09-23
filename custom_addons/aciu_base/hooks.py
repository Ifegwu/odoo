# Part of ACIU Odoo customization.

import base64
import logging

from odoo import SUPERUSER_ID, api
from odoo.tools.misc import file_open

from .brand_colors import (
    ACIU_INK,
    ACIU_ON_PRIMARY,
    ACIU_PRIMARY,
)

_logger = logging.getLogger(__name__)

_LOGO_RELPATH = 'aciu_base/static/img/aciu_logo.png'


def _load_aciu_logo_b64():
    with file_open(_LOGO_RELPATH, 'rb') as logo_file:
        return base64.b64encode(logo_file.read())


def _aciu_color_vals():
    vals = {
        'primary_color': ACIU_PRIMARY,
        'secondary_color': ACIU_INK,
    }
    # mail adds email button colors when installed
    return vals


def apply_aciu_branding(env):
    """Set ACIU logo and website-aligned colors on companies."""
    logo = _load_aciu_logo_b64()
    color_vals = _aciu_color_vals()
    if 'email_secondary_color' in env['res.company']._fields:
        color_vals['email_secondary_color'] = ACIU_PRIMARY
        color_vals['email_primary_color'] = ACIU_ON_PRIMARY

    companies = env['res.company'].search([('is_aciu_company', '=', True)])
    write_vals = {'logo': logo, **color_vals}
    if companies:
        companies.write(write_vals)
        _logger.info(
            'ACIU branding: logo + colors set on %s companies (primary=%s)',
            len(companies), ACIU_PRIMARY,
        )

    main_company = env.ref('base.main_company', raise_if_not_found=False)
    if main_company and main_company not in companies:
        main_company.write(write_vals)


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    apply_aciu_branding(env)
