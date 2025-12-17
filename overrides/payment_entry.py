import frappe
from erpnext.accounts.doctype.payment_entry.payment_entry import PaymentEntry

class PaymentEntryCustom(PaymentEntry):
    def get_valid_reference_doctypes(self):
        """
        Overrides the standard get_valid_reference_doctypes to include
        "Expense Claim" as a valid reference for Employee party_type.
        """
        valid_doctypes = super().get_valid_reference_doctypes()

        if self.party_type == "Employee":
            # Convert tuple to list to allow modification, then convert back to tuple
            valid_doctypes_list = list(valid_doctypes)
            if "Expense Claim" not in valid_doctypes_list:
                valid_doctypes_list.append("Expense Claim")
            valid_doctypes = tuple(valid_doctypes_list)
            
        return valid_doctypes
