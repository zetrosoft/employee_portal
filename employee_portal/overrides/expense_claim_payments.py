import frappe
from hrms.hr.doctype.expense_claim.expense_claim import make_bank_entry as original_make_bank_entry


@frappe.whitelist()
def make_bank_entry(dt, dn):
    """
    Overrides the standard make_bank_entry from HRMS to adjust
    reference_type for Expense Claim accounts in Journal Entry.
    """
    # Panggil fungsi make_bank_entry asli dari HRMS
    je_dict = original_make_bank_entry(dt, dn)

    # Konversi dictionary ke objek DocType Journal Entry sementara
    je = frappe.get_doc(je_dict)

    # Iterasi melalui akun di Journal Entry
    for account_entry in je.get("accounts"):
        # Jika reference_type adalah "Expense Claim" dan party_type adalah "Employee"
        # Ini adalah baris untuk payable_account yang merujuk kembali ke Expense Claim
        if (
            account_entry.reference_type == "Expense Claim"
            and account_entry.party_type == "Employee"
            and account_entry.party == frappe.get_doc(dt, dn).employee
        ):
            # Hapus reference_type dan reference_name untuk menghindari validasi
            # yang mengharuskan Reference Doctype must be one of Journal Entry.
            account_entry.reference_type = None
            account_entry.reference_name = None

            # Opsional: Tambahkan remark untuk pelacakan
            # account_entry.user_remark = f"Reference to Expense Claim {dn} removed by override"

    return je.as_dict()
