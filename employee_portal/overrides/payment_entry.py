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

    def validate(self):
        # Cek apakah ini adalah kasus khusus untuk Expense Claim
        is_expense_claim_ref = self.reference_doctype == "Expense Claim"

        if is_expense_claim_ref:
            # Simpan nilai asli untuk dikembalikan nanti
            original_ref_doctype = self.reference_doctype
            original_ref_name = self.reference_name
            
            # Hapus sementara referensi agar validasi inti lolos
            self.reference_doctype = None
            self.reference_name = None

        try:
            # Selalu jalankan validasi inti dari parent class
            super(PaymentEntryCustom, self).validate()
        finally:
            # Jika ini adalah kasus khusus, kembalikan nilai asli setelah validasi selesai
            if is_expense_claim_ref:
                self.reference_doctype = original_ref_doctype
                self.reference_name = original_ref_name

    def on_submit(self):
        # Jalankan dulu on_submit standar
        super(PaymentEntryCustom, self).on_submit()

        # LOGIKA UNTUK UPDATE STATUS EXPENSE CLAIM
        if self.reference_doctype == "Expense Claim" and self.reference_name:
            try:
                # Dapatkan dokumen Expense Claim yang dirujuk
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
