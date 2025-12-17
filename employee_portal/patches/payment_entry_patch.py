import frappe
from erpnext.accounts.doctype.payment_entry.payment_entry import PaymentEntry

# 1. Simpan metode-metode asli sebelum kita menimpanya
original_get_valid_reference_doctypes = PaymentEntry.get_valid_reference_doctypes
original_on_submit = PaymentEntry.on_submit

# 2. Definisikan metode pengganti (patched method)
def patched_get_valid_reference_doctypes(self):
    # Panggil metode asli terlebih dahulu
    valid_doctypes = original_get_valid_reference_doctypes(self)
    
    if self.party_type == "Employee":
        # Karena hasil aslinya adalah tuple, kita ubah ke list untuk dimodifikasi
        valid_doctypes_list = list(valid_doctypes)
        if "Expense Claim" not in valid_doctypes_list:
            valid_doctypes_list.append("Expense Claim")
        return tuple(valid_doctypes_list)
        
    return valid_doctypes

def patched_on_submit(self):
    # Panggil metode on_submit asli terlebih dahulu
    original_on_submit(self)

    # Kemudian jalankan logika kustom kita untuk update status
    if self.reference_doctype == "Expense Claim" and self.reference_name:
        try:
            expense_claim_doc = frappe.get_doc("Expense Claim", self.reference_name)
            if hasattr(expense_claim_doc, "update_paid_status"):
                expense_claim_doc.update_paid_status()
                expense_claim_doc.save(ignore_permissions=True)
            else:
                frappe.db.set_value("Expense Claim", self.reference_name, "status", "Paid")
            frappe.db.commit()
        except Exception as e:
            frappe.log_error(f"Error in payment_entry_patch on_submit: {e}")

# 3. Buat fungsi untuk menerapkan patch
def apply_patch():
    # Tindakan Monkey Patching: Timpa metode di kelas asli dengan versi kita
    PaymentEntry.get_valid_reference_doctypes = patched_get_valid_reference_doctypes
    PaymentEntry.on_submit = patched_on_submit
