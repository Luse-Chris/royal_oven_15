# Part of Odoo. See LICENSE file for full copyright and licensing details.
import hmac, hashlib, sys
import logging
import requests 
from werkzeug import urls
from odoo import _, api, models, fields
from odoo.exceptions import UserError, ValidationError
from odoo.addons.payment import utils as payment_utils

_logger = logging.getLogger(__name__)

class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'
    mpesa_transaction_id = fields.Char("TransactionID",help="The transaction identifier that gets generated on the Mobile Money platform. This is used to query transactions on the Mobile Money Platform")
    mpesa_conversation_id = fields.Char("ConversationID",help="The OpenAPI platform generates this as a reference to the transaction.")
    mpesa_third_party_conversation_id = fields.Char("ThirdPartyConversationID", help="The incoming reference from the third party system. When there are queries about transactions, this will usually be used to track a transaction.")
    def _get_specific_processing_values(self, processing_values):
        """ Override of payment to return an access token as acquirer-specific processing values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic processing values of the transaction
        :return: The dict of acquirer-specific processing values
        :rtype: dict
        """
        res = super()._get_specific_processing_values(processing_values)
        if self.provider != 'mpesa':
            return res

        return {
            'access_token': payment_utils.generate_access_token(
                processing_values['reference'], processing_values['partner_id']
            )
        }
    @api.model
    def _get_tx_from_feedback_data(self, provider, data):
        """ Override of payment to find the transaction based on Quickpay data.

        :param str provider: The provider of the acquirer that handled the transaction
        :param dict data: The feedback data sent by the provider
        :return: The transaction if found
        :rtype: recordset of `payment.transaction`
        :raise: ValidationError if inconsistent data were received
        :raise: ValidationError if the data match no transaction
        """
        tx = super()._get_tx_from_feedback_data(provider, data)
        if provider != 'mpesa':
            return tx

        reference = data.get('output_ConversationID')
        if not reference:
            raise ValidationError("Mpesa: " + _("Received data with missing reference"))

        tx = self.search([('mpesa_conversation_id', '=', reference), ('provider', '=', 'mpesa')])
        if not tx:
            raise ValidationError(
                "Mpesa: " + _("No transaction found matching reference %s.", reference)
            )
        return tx
    
    def _process_feedback_data(self, data):
        """ Override of payment to process the transaction based on Ogone data.

        Note: self.ensure_one()

        :param dict data: The feedback data sent by the provider
        :return: None
        """
        self.ensure_one()
        super()._process_feedback_data(data)
        if self.provider != 'mpesa':
            return
        payment_status = data.get("output_ResponseCode")
        if payment_status == 'INS-0':
            self._set_done()
        else:
            _logger.info("Received data with invalid payment status: %s", payment_status)
            self._set_error(
                "Mpesa: " + _("Received data with invalid payment status: %s", payment_status)
            )