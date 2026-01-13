import frappe
from frappe import _
from erpnext.accounts.doctype.payment_entry.payment_entry import PaymentEntry

class PaymentEntryCustom(PaymentEntry):
    def get_valid_reference_doctypes(self):
        valid_doctypes = super(PaymentEntryCustom, self).get_valid_reference_doctypes()
        if self.party_type == "Employee":
            return ("Journal Entry", "Expense Claim", "Employee Advance")
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

        # LOGIKA UNTUK UPDATE STATUS EXPENSE CLAIM DAN EMPLOYEE ADVANCE
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
            
            elif ref.reference_doctype == "Employee Advance" and ref.reference_name:
                try:
                    frappe.db.set_value("Employee Advance", ref.reference_name, "status", "Paid")
                    frappe.db.commit()
                except Exception as e:
                    frappe.log_error(f"Error updating Employee Advance status for {ref.reference_name}: {e}", "PE Override")
    
    def validate_allocated_amount(self):
        # Override standard validation to handle Employee Advance specifically
        from frappe.utils import flt

        fail_message = _("Row #{0}: Allocated Amount cannot be greater than outstanding amount.")

        for d in self.get("references"):
            if d.reference_doctype == "Employee Advance":
                # Custom validation for Employee Advance
                if d.reference_name:
                    employee_advance_doc = frappe.get_doc("Employee Advance", d.reference_name)
                    
                    # Calculate outstanding for Employee Advance
                    # Assume outstanding = advance_amount - paid_amount - claimed_amount
                    total_advance_amount = flt(employee_advance_doc.advance_amount)
                    total_paid_amount = flt(employee_advance_doc.paid_amount)
                    total_claimed_amount = flt(employee_advance_doc.claimed_amount)
                    
                    outstanding_for_advance = total_advance_amount - total_paid_amount - total_claimed_amount
                    
                    if flt(d.allocated_amount) > outstanding_for_advance:
                        frappe.throw(fail_message.format(d.idx))
            else:
                # For other doctypes, call the standard validation logic
                super(PaymentEntryCustom, self).validate_allocated_amount()
