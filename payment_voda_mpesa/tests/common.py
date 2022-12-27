# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.payment.tests.common import PaymentCommon


class MpesaCommon(PaymentCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.mpesa = cls._prepare_acquirer('stripe', update_values={
            'market': 'vodacomTZN',
            'mpesa_api_key': 'fdfdf22323232322',
            'mpesa_provider_code': '000000',
            'payment_icon_ids': [(5, 0, 0)],
        })

        cls.acquirer = cls.mpesa
