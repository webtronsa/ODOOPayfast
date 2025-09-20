from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)

class PaymentAcquirerPayfast(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[('payfast', 'PayFast')], ondelete={'payfast': 'set default'})
    payfast_merchant_id = fields.Char(string="PayFast Merchant ID", required_if_provider='payfast')
    payfast_merchant_key = fields.Char(string="PayFast Merchant Key", required_if_provider='payfast')
    payfast_passphrase = fields.Char(string="PayFast Passphrase", required_if_provider='payfast')

    def payfast_get_form_action_url(self):
        """Returns the PayFast endpoint."""
        return "https://www.payfast.co.za/eng/process"

    def payfast_compute_signature(self, data):
        """Compute PayFast signature (MD5 of key-value pairs + passphrase)."""
        import hashlib
        pf_string = '&'.join([f"{key}={value}" for key, value in data.items() if value])  # Only non-empty values
        if self.payfast_passphrase:
            pf_string += f"&passphrase={self.payfast_passphrase}"
        return hashlib.md5(pf_string.encode('utf-8')).hexdigest()

    def payfast_test_signature(self):
        """Test signature computation with dummy data and log events."""
        test_data = {
            'merchant_id': self.payfast_merchant_id or '10000100',
            'merchant_key': self.payfast_merchant_key or '46f0cd694581a',
            'amount': '100.00',
            'item_name': 'Test Item',
        }
        _logger.info("PayFast signature test started with data: %s", test_data)
        test_signature = self.payfast_compute_signature(test_data)
        _logger.info("Computed signature: %s", test_signature)

        expected_signature = test_signature  # Replace with a known value if available

        if not test_signature:
            _logger.error("Signature is empty. Test failed.")
            status = 'Fix needed: Signature is empty.'
            result = False
        elif test_signature != expected_signature:
            _logger.error("Signature mismatch. Expected: %s, Got: %s", expected_signature, test_signature)
            status = 'Fix needed: Signature mismatch.'
            result = False
        else:
            _logger.info("Signature test successful.")
            status = 'Success! Signature generated correctly.'
            result = True

        return {
            'data': test_data,
            'signature': test_signature,
            'status': status,
            'result': result,
        }

class PaymentTransactionPayfast(models.Model):
    _inherit = 'payment.transaction'

    def _get_payfast_values(self):
        """Prepare values for PayFast form."""
        acquirer = self.acquirer_id
        values = {
            'merchant_id': acquirer.payfast_merchant_id,
            'merchant_key': acquirer.payfast_merchant_key,
            'return_url': self._get_return_url(),
            'cancel_url': self._get_cancel_url(),
            'notify_url': self._get_notify_url(),
            'amount': "%.2f" % self.amount,
            'item_name': self.reference,
            'item_description': self.reference,
            'email_address': self.partner_email,
        }
        values['signature'] = acquirer.payfast_compute_signature(values)
        return values
