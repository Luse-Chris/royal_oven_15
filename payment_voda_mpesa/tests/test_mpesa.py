# Part of Odoo. See LICENSE file for full copyright and licensing details.
from .common import MpesaCommon


@tagged('post_install', '-at_install')
class MpesaTest(MpesaCommon):
    pass





