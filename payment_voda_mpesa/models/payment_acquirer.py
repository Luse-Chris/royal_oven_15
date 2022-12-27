# Part of Odoo. See LICENSE file for full copyright and licensing details.
import uuid
import logging
import requests
from werkzeug import urls
from base64 import b64decode, b64encode
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5 as Cipher_PKCS1_v1_5
from requests.auth import HTTPBasicAuth
from requests.exceptions import HTTPError

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.modules.module import get_module_resource
_logger = logging.getLogger(__name__)

MARKET_COUNTRY_MAP = {
    "vodacomTZN": "TZN",
    "vodafoneGHA": "GHA",
    "vodacomLES": "LES",
    "vodacomDRC": "DRC",
}
MARKET_CURRENCY_MAP = {
    "vodacomTZN": "TZS",
    "vodafoneGHA": "GHS",
    "vodacomLES": "LSL",
    "vodacomDRC": "USD",
}

SANDBOX_PUBLIC_KEY = "MIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEArv9yxA69XQKBo24BaF/D+fvlqmGdYjqLQ5WtNBb5tquqGvAvG3WMFETVUSow/LizQalxj2ElMVrUmzu5mGGkxK08bWEXF7a1DEvtVJs6nppIlFJc2SnrU14AOrIrB28ogm58JjAl5BOQawOXD5dfSk7MaAA82pVHoIqEu0FxA8BOKU+RGTihRU+ptw1j4bsAJYiPbSX6i71gfPvwHPYamM0bfI4CmlsUUR3KvCG24rB6FNPcRBhM3jDuv8ae2kC33w9hEq8qNB55uw51vK7hyXoAa+U7IqP1y6nBdlN25gkxEA8yrsl1678cspeXr+3ciRyqoRgj9RD/ONbJhhxFvt1cLBh+qwK2eqISfBb06eRnNeC71oBokDm3zyCnkOtMDGl7IvnMfZfEPFCfg5QgJVk1msPpRvQxmEsrX9MQRyFVzgy2CWNIb7c+jPapyrNwoUbANlN8adU1m6yOuoX7F49x+OjiG2se0EJ6nafeKUXw/+hiJZvELUYgzKUtMAZVTNZfT8jjb58j8GVtuS+6TM2AutbejaCV84ZK58E2CRJqhmjQibEUO6KPdD7oTlEkFy52Y1uOOBXgYpqMzufNPmfdqqqSM4dU70PO8ogyKGiLAIxCetMjjm6FCMEA3Kc8K0Ig7/XtFm9By6VxTJK1Mg36TlHaZKP6VzVLXMtesJECAwEAAQ=="
OPENAPI_PUBLIC_KEY = "MIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEAietPTdEyyoV/wvxRjS5pSn3ZBQH9hnVtQC9SFLgM9IkomEX9Vu9fBg2MzWSSqkQlaYIGFGH3d69Q5NOWkRo+Y8p5a61sc9hZ+ItAiEL9KIbZzhnMwi12jUYCTff0bVTsTGSNUePQ2V42sToOIKCeBpUtwWKhhW3CSpK7S1iJhS9H22/BT/pk21Jd8btwMLUHfVD95iXbHNM8u6vFaYuHczx966T7gpa9RGGXRtiOr3ScJq1515tzOSOsHTPHLTun59nxxJiEjKoI4Lb9h6IlauvcGAQHp5q6/2XmxuqZdGzh39uLac8tMSmY3vC3fiHYC3iMyTb7eXqATIhDUOf9mOSbgZMS19iiVZvz8igDl950IMcelJwcj0qCLoufLE5y8ud5WIw47OCVkD7tcAEPmVWlCQ744SIM5afw+Jg50T1SEtu3q3GiL0UQ6KTLDyDEt5BL9HWXAIXsjFdPDpX1jtxZavVQV+Jd7FXhuPQuDbh12liTROREdzatYWRnrhzeOJ5Se9xeXLvYSj8DmAI4iFf2cVtWCzj/02uK4+iIGXlX7lHP1W+tycLS7Pe2RdtC2+oz5RSSqb5jI4+3iEY/vZjSMBVk69pCDzZy4ZE8LBgyEvSabJ/cddwWmShcRS+21XvGQ1uXYLv0FCTEHHobCfmn2y8bJBb/Hct53BaojWUCAwEAAQ=="

class PaymentAcquirerMpesa(models.Model):
    _inherit = 'payment.acquirer'
    provider = fields.Selection(selection_add=[('mpesa', 'Mpesa')],ondelete={'mpesa': 'set default'})
    market = fields.Selection([
        ('vodacomTZN', 'Vodacom Tanzania'),
        ('vodafoneGHA', 'Vodafone Ghana'),
        ('vodacomLES', 'Vodacom Lesotho'),
        ('vodacomDRC', 'Vodacom DR Congo'),
    ])
    mpesa_api_key = fields.Char(required_if_provider='mpesa', groups='base.group_user',string="API key", help="Mpesa API key")
    mpesa_provider_code = fields.Char(required_if_provider='mpesa', groups='base.group_user',string="Provider code", help="Service Provider Code")

    def _get_default_payment_method_id(self):
        self.ensure_one()
        if self.provider != 'mpesa':
            return super()._get_default_payment_method_id()
        return self.env.ref('payment_mpesa.payment_method_mpesa').id
    def _mpesa_get_api_url(self):
        """ Return the API URL according to the acquirer state.

        Note: self.ensure_one()

        :return: The API URL
        :rtype: str
        """
        self.ensure_one()
        if self.state == 'enabled':
            return f'https://openapi.m-pesa.com/production/ipg/v2/{self.market}/'
        else:
            return f'https://openapi.m-pesa.com/sandbox/ipg/v2/{self.market}/'


    def _mpesa_get_default_headers(self):
        return {
            'Content-Type': 'application/json', 
            'Host': 'openapi.m-pesa.com', 
            'Origin': '*'
        } 
    def _mpesa_create_bearer_token(self, key):
        public_key = OPENAPI_PUBLIC_KEY if self.state == "enabled" else  SANDBOX_PUBLIC_KEY
        key_der = b64decode(public_key)
        key_pub = RSA.importKey(key_der)
        cipher = Cipher_PKCS1_v1_5.new(key_pub)
        cipher_text = cipher.encrypt(key.encode('ascii'))
        return  b64encode(cipher_text).decode('utf-8')

    def _mpesa_request_session_key(self):
        try:
            # if cls.session_key:
            #    return Session.session_key
            token = self._mpesa_create_bearer_token(self.mpesa_api_key)
            headers = {**self._mpesa_get_default_headers(), "Authorization": f"Bearer {token}"}
            url = urls.url_join(self._mpesa_get_api_url(), "getSession/")
            response = requests.get(url, headers=headers, verify=True)
            response.raise_for_status()
            response = response.json()
            return response["output_SessionID"]
        except HTTPError as e:
            _logger.exception(e)
            raise Exception(e.response.json())
    def _mpesa_do_request(self,uri, data=None, method="post"):
       try:
            session_key = self._mpesa_request_session_key()
            token = self._mpesa_create_bearer_token(session_key)
            headers = {**self._mpesa_get_default_headers(), "Authorization": f"Bearer {token}"}
            url = urls.url_join(self._mpesa_get_api_url(), uri)
            res = requests.request(method, url, json=data, headers=headers, verify=True)
            res.raise_for_status()
            return res.json()
       except requests.exceptions.HTTPError as http_error:
            ERROR_CODES = [400, 401, 408, 409, 422]
            error_msg = ''
            _logger.exception("invalid API request at %s with data %s", url, data)
            if http_error.response.status_code in ERROR_CODES:
               error_msg = res.json()["output_ResponseDesc"]
            raise ValidationError(
                        "Mpesa: " + _(
                            "The communication with the API failed.\n"
                            "Mpesa gave us the following info about the problem:\n'%s'", error_msg
                        )
                    )
       except requests.exceptions.ConnectionError as conn_err:
            _logger.exception(conn_err)
            raise ValidationError("Mpesa: " + _("Could not establish the connection to the API."))

    def _mpesa_c2b(self, mpesa_number,amount,reference, currency):
        third_party_conversation_id = uuid.uuid4().hex[:32].upper()
        # Auto convert currency to mpesa allowed currency
        # For example for Tanzania Mpesa accepts only TZS
        mpesa_currency = self.env["res.currency"].search([("name","=", MARKET_CURRENCY_MAP[self.market])], limit=1)
        amount = currency._convert(float(amount), mpesa_currency, self.company_id,fields.Date.context_today(self))
        data = {
            "input_Country": MARKET_COUNTRY_MAP.get(self.market),
            "input_Currency": MARKET_CURRENCY_MAP.get(self.market),
            "input_CustomerMSISDN": mpesa_number,
            "input_ServiceProviderCode": self.mpesa_provider_code,
            "input_ThirdPartyConversationID": third_party_conversation_id,
            "input_Amount": amount,
            "input_PurchasedItemsDesc": "Purchase Item desc",
            "input_TransactionReference": reference
        }
        return self._mpesa_do_request("c2bPayment/singleStage/", data=data)
           
    
        