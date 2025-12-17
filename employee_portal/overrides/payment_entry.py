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
        # Jika bukan 'Expense Claim', jalankan validasi standar.
        if self.reference_doctype != "Expense Claim":
            super(PaymentEntryCustom, self).validate()
            return

        # --- FIX UNTUK REFERENSI YANG HILANG ---
        # Simpan kedua nilai asli
        original_ref_doctype = self.reference_doctype
        original_ref_name = self.reference_name
        
        # Hapus sementara referensi sebelum memanggil validasi inti
        # agar tidak divalidasi dan dikosongkan oleh parent class.
        self.reference_doctype = None
        self.reference_name = None

        try:
            super(PaymentEntryCustom, self).validate()
        finally:
            # Selalu kembalikan nilai asli setelah validasi inti selesai.
            self.reference_doctype = original_ref_doctype
            self.reference_name = original_ref_name

    def on_submit(self):
        # Jalankan dulu on_submit standar
        super(PaymentEntryCustom, self).on_submit()

        # --- LOGIKA BARU UNTUK UPDATE STATUS EXPENSE CLAIM ---
        if self.reference_doctype == "Expense Claim" and self.reference_name:
            try:
                # Dapatkan dokumen Expense Claim yang dirujuk
                expense_claim_doc = frappe.get_doc("Expense Claim", self.reference_name)
                
                # Panggil metode update_paid_status (jika ada) atau set status secara manual
                # Di ERPNext v13+, cara yang benar adalah memanggil 'update_paid_status'
                if hasattr(expense_claim_doc, "update_paid_status"):
                    expense_claim_doc.update_paid_status()
                    expense_claim_doc.save(ignore_permissions=True)
                else:
                    # Fallback jika metode tidak ada
                    frappe.db.set_value("Expense Claim", self.reference_name, "status", "Paid")

                # Commit perubahan database
                frappe.db.commit()

            except frappe.DoesNotExistError:
                frappe.log_error(f"Expense Claim {self.reference_name} not found when submitting Payment Entry {self.name}", "Payment Entry Override")
            except Exception as e:
                frappe.log_error(f"Error updating Expense Claim status: {e}", "Payment Entry Override")
