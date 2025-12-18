import frappe
from erpnext.accounts.doctype.payment_entry.payment_entry import PaymentEntry

class PaymentEntryCustom(PaymentEntry):
    def get_valid_reference_doctypes(self):
        valid_doctypes = super(PaymentEntryCustom, self).get_valid_reference_doctypes()
        if self.party_type == "Employee":
            return ("Journal Entry", "Expense Claim")
        return valid_doctypes

    def validate(self):
        # NOTE: The previous custom validation logic was based on outdated single-reference fields
        # and has been removed. The base validation should now correctly handle "Expense Claim"
        # as a valid doctype thanks to the get_valid_reference_doctypes method.
        super(PaymentEntryCustom, self).validate()

    def on_submit(self):
        # HACK: The base `on_submit` method seems to require `reference_doctype`
        # on the main doc. We'll temporarily set it from the first child table row
        # to satisfy the parent method, and then remove it.
        set_temp_fields = self.references and not hasattr(self, 'reference_doctype')

        if set_temp_fields:
            self.reference_doctype = self.references[0].reference_doctype
            self.reference_name = self.references[0].reference_name

        try:
            # Call the standard on_submit which now should not fail
            super(PaymentEntryCustom, self).on_submit()
        finally:
            # Clean up the temporary fields
            if set_temp_fields:
                del self.reference_doctype
                del self.reference_name

        # LOGIKA UNTUK UPDATE STATUS EXPENSE CLAIM
        # This part was fixed previously and should remain.
        for ref in self.references:
            if ref.reference_doctype == "Expense Claim" and ref.reference_name:
                try:
                    expense_claim_doc = frappe.get_doc("Expense Claim", ref.reference_name)
                    
                    if hasattr(expense_claim_doc, "update_paid_status"):
                        expense_claim_doc.update_paid_status()
                        expense_claim_doc.save(ignore_permissions=True)
                    else:
                        frappe.db.set_value("Expense Claim", ref.reference_name, "status", "Paid")
                    frappe.db.commit()
                except Exception as e:
                    frappe.log_error(f"Error updating Expense Claim status for {ref.reference_name}: {e}", "PE Override")
