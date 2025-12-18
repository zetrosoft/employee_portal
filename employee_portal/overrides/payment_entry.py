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
        # Jalankan dulu on_submit standar
        super(PaymentEntryCustom, self).on_submit()

        # LOGIKA UNTUK UPDATE STATUS EXPENSE CLAIM
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
