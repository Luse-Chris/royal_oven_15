# Part of Odoo. See LICENSE file for full copyright and licensing details.
import uuid
import logging
import json
import pprint
from odoo import _, http
from odoo.exceptions import ValidationError
from odoo.http import request
from odoo.addons.payment import utils as payment_utils

_logger = logging.getLogger(__name__)

class PaymentMpesaController(http.Controller):
    _callbackurl = "/payment/mpesa/callback"
    @http.route("/payment/mpesa/payment", type='json', auth='public')
    def mpesa_payment(self,acquirer_id, reference, partner_id,amount, mpesa_number, access_token):
        """ Make a payment request and handle the response.

        :param str reference: The reference of the transaction
        :param int partner_id: The partner making the transaction, as a `res.partner` id
        :param str access_token: The access token used to verify the provided values
        :param float amount: The payment amount
        :param str phone_number: Phone number to use for mpesa transaction
        :return: None
        """
        # Check that the transaction details have not been altered
        if not payment_utils.check_access_token(access_token, reference, partner_id):
            raise ValidationError("Mpesa: " + _("Received tampered payment request data."))

        # Make the payment request to Swish
        transaction_reference = reference.replace("/", "").replace("-", "")
        acquirer_sudo = request.env['payment.acquirer'].sudo().browse(acquirer_id).exists()
        tx_sudo = request.env['payment.transaction'].sudo().search([('reference', '=', reference)])
        response_content = acquirer_sudo._mpesa_c2b(
            mpesa_number,
            amount,
            transaction_reference,
            tx_sudo.currency_id
        )
        tx_sudo.sudo().write({
            "mpesa_transaction_id": response_content["output_TransactionID"],
            "mpesa_conversation_id": response_content["output_ConversationID"],
            "mpesa_third_party_conversation_id": response_content["output_ThirdPartyConversationID"],
        })
        # Handle the payment request response
        _logger.info("make payment response:\n%s", pprint.pformat(response_content))
        # As the API has no redirection flow, we always know the reference of the transaction.
        # Still, we prefer to simulate the matching of the transaction by crafting dummy feedback
        # data in order to go through the centralized `_handle_feedback_data` method.
        # feedback_data = {'reference': tx_sudo.reference, 'response': response_content}
        request.env['payment.transaction'].sudo()._handle_feedback_data(
            'mpesa', response_content
        )

    @http.route(_callbackurl, type='json', auth='public', methods=['POST'], csrf=False)
    def mpesa_callback(self, **data): 
        """ Process the data returned by Mpesa callback.

        :param dict data: The feedback data
        """
        data = json.loads(request.httprequest.data)
        _logger.info(f"received notification data from {PaymentSwishController._callbackurl}:\n{pprint.pformat(data)}")
        request.env['payment.transaction'].sudo()._handle_feedback_data('mpesa', data)
        return ''