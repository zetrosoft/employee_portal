import frappe
from frappe.exceptions import DuplicateEntryError


def main():
    """
    Membuat atau memperbarui izin peran.
    Menggunakan DocType Custom DocPerm/DocPerm dan disesuaikan untuk
    skema basis data lama (tabel tabDocPerm yang tidak memiliki kolom 'parenttype').
    """
    frappe.clear_cache()

    # Digunakan untuk DocType yang dipetakan ke tabDocPerm di instalasi lama
    TARGET_DOCTYPE = "Custom DocPerm"

    # Lakukan pengecekan fallback DocType:
    if not frappe.db.exists("DocType", TARGET_DOCTYPE):
        TARGET_DOCTYPE = "DocPerm"
        if not frappe.db.exists("DocType", TARGET_DOCTYPE):
            frappe.throw(f"DocType '{TARGET_DOCTYPE}' atau 'Custom DocPerm' tidak ditemukan. Skrip tidak bisa dilanjutkan.")


    role_name = "Employee User"
    permlevel = 0

    if not frappe.db.exists("Role", role_name):
        frappe.throw(f"Role '{role_name}' tidak ditemukan.")

    default_permissions = {
        "read": 0, "write": 0, "create": 0, "delete": 0,
        "report": 0, "cancel": 0, "submit": 0, "amend": 0,
        "print": 0, "email": 0, "export": 0, "set_user_permissions": 0,
        "share": 0, "restrict_to_domain": 0,
        # Field yang mungkin ada di DocPerm:
        "if_owner": 0, "select": 0
    }

    permissions_data = [
        {"ref_doctype": "Leave Application", "read": 1, "write": 1, "create": 1, "delete": 1, "report": 1, "cancel": 1},
        {"ref_doctype": "Leave Allocation", "read": 1, "report": 1},
        {"ref_doctype": "Holiday List", "read": 1, "report": 1},
        {"ref_doctype": "Employee Leave Balance", "read": 1, "report": 1},
        {"ref_doctype": "Leave Control Panel", "read": 1, "report": 1},
        {"ref_doctype": "Expense Claim", "read": 1, "write": 1, "create": 1, "delete": 1, "report": 1, "cancel": 1},
        {"ref_doctype": "Employee Advance", "read": 1, "write": 1, "create": 1, "delete": 1, "report": 1},
        {"ref_doctype": "Employee Advance Summary", "read": 1, "report": 1},
    ]

    for perm_def in permissions_data:
        target_doctype = perm_def.pop("ref_doctype")

        # PERBAIKAN KRITIS: Menghapus 'parenttype' dari filter
        rp_name = frappe.db.get_value(
            TARGET_DOCTYPE,
            {"role": role_name, "parent": target_doctype, "permlevel": permlevel},
            "name"
        )

        try:
            if rp_name:
                rp_doc = frappe.get_doc(TARGET_DOCTYPE, rp_name)
                action = "Updated"
            else:
                rp_doc = frappe.new_doc(TARGET_DOCTYPE)
                rp_doc.role = role_name
                # Di tabDocPerm, DocType yang diizinkan disimpan di kolom 'parent'
                rp_doc.parent = target_doctype
                rp_doc.permlevel = permlevel

                # JANGAN SET parenttype atau parentfield, karena kolomnya tidak ada
                action = "Created"

            # Gabungkan izin default (0) dengan izin yang didefinisikan (1)
            final_permissions = default_permissions.copy()
            final_permissions.update(perm_def)

            # Tetapkan nilai izin pada dokumen
            for field, value in final_permissions.items():
                # Pastikan hanya field yang relevan yang diset
                if field in rp_doc.meta.get_valid_columns():
                    setattr(rp_doc, field, value)

            # Simpan/Insert dokumen
            if action == "Created":
                rp_doc.insert(ignore_permissions=True)
            else:
                rp_doc.save(ignore_permissions=True)

            frappe.msgprint(f"Berhasil {action} {TARGET_DOCTYPE} untuk DocType: {target_doctype}")

        except Exception as e:
            frappe.log_error(title="Setup Permissions Error", message=f"Gagal {action} {TARGET_DOCTYPE} untuk {target_doctype}: {e}")
            frappe.db.rollback()
            frappe.throw(f"Gagal menjalankan setup izin untuk {target_doctype}. Cek log error.")

    frappe.db.commit()
    frappe.msgprint(f"{TARGET_DOCTYPE} setup complete for '{role_name}'.")
