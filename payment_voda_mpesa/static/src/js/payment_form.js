/* global Accept */
odoo.define('payment_voda_mpesa.payment_form', require => {
    'use strict';
     const core = require("web.core");
     const checkoutForm = require("payment.checkout_form");
     const manageForm = require("payment.manage_form");

     const _t = core._t;

     const mpesaMixin = {
       _getInlineFormInputs: function (acquirerId) {
         return {
           mpesa_number: document.getElementById(
             `o_mpesa_number_${acquirerId}`
           ),
         };
       },
       /**
        * Checks that all payment inputs adhere to the DOM validation constraints.
        *
        * @private
        * @param {number} acquirerId - The id of the selected acquirer
        * @return {boolean} - Whether all elements pass the validation constraints
        */
       _validateFormInputs: function (acquirerId) {
         const inputs = Object.values(this._getInlineFormInputs(acquirerId));
         return inputs.every((element) => element.reportValidity());
       },
        _prepareInlineForm: function (provider, paymentOptionId, flow) {
          if (provider !== "mpesa") {
            return this._super(...arguments);
          }
          
          if (flow === "token") {
            return Promise.resolve(); // Don't show the form for tokens
          }
          // Overwrite the flow of the select payment option
          this._setPaymentFlow("direct");
        },
       _processPayment: function(provider, paymentOptionId, flow){
         if (provider !== "mpesa" || flow === "token") {
           return this._super(...arguments); // Tokens are handled by the generic flow
         }

         if (!this._validateFormInputs(paymentOptionId)) {
           this._enableButton(); // The submit button is disabled at this point, enable it
           $('body').unblock(); // The page is blocked at this point, unblock it
           return Promise.resolve();
         }
         // Create the transaction and retrieve the processing values
         return this._rpc({
           route: this.txContext.transactionRoute,
           params: this._prepareTransactionRouteParams(
             "mpesa",
             paymentOptionId,
             "direct"
           ),
         })
           .then((processingValues) => {
             // Initiate the payment
             const inputs = this._getInlineFormInputs(paymentOptionId);
             return this._rpc({
               route: "/payment/mpesa/payment",
               params: {
                 acquirer_id: paymentOptionId,
                 reference: processingValues.reference,
                 partner_id: processingValues.partner_id,
                 amount: this.txContext.amount,
                 access_token: processingValues.access_token,
                 mpesa_number: inputs.mpesa_number.value,
               },
             }).then(() => (window.location = "/payment/status"));
           })
           .guardedCatch((error) => {
             error.event.preventDefault();
             this._displayError(
               _t("Server Error"),
               _t("We are not able to process your payment."),
               error.message.data.message
             );
           });
       }
     };
  checkoutForm.include(mpesaMixin);
  manageForm.include(mpesaMixin);

})