import frappe
from erpnext.accounts.doctype.payment_entry.payment_entry import PaymentEntry

class PaymentEntryCustom(PaymentEntry):
    def get_valid_reference_doctypes(self):
        valid_doctypes = super().get_valid_reference_doctypes()
        if self.party_type == "Employee":
            valid_doctypes_list = list(valid_doctypes)
            if "Expense Claim" not in valid_doctypes_list:
                valid_doctypes_list.append("Expense Claim")
            valid_doctypes = tuple(valid_doctypes_list)
        return valid_doctypes

    def on_submit(self):
        # Jalankan dulu on_submit standar
        super(PaymentEntryCustom, self).on_submit()

        # LOGIKA UNTUK UPDATE STATUS EXPENSE CLAIM
        if self.reference_doctype == "Expense Claim" and self.reference_name:
            try:
                expense_claim_doc = frappe.get_doc("Expense Claim", self.reference_name)
                
                if hasattr(expense_claim_doc, "update_paid_status"):
                    expense_claim_doc.update_paid_status()
                    expense_claim_doc.save(ignore_permissions=True)
                else:
                    frappe.db.set_value("Expense Claim", self.reference_name, "status", "Paid")

                frappe.db.commit()

            except frappe.DoesNotExistError:
                frappe.log_error(f"Expense Claim {self.reference_name} not found when submitting PE {self.name}", "PE Override")
            except Exception as e:
                frappe.log_error(f"Error updating Expense Claim status: {e}", "PE Override")
