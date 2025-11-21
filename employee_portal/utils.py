import frappe


def create_workflow_roles_function():
    # Daftar peran yang dibutuhkan untuk workflow
    required_roles = [
        "Director",
        "Production Manager",
        "Quality Manager"
    ]

    print("Memeriksa dan membuat peran yang dibutuhkan...")

    for role_name in required_roles:
        if not frappe.db.exists("Role", role_name):
            try:
                role = frappe.get_doc({
                    "doctype": "Role",
                    "role_name": role_name
                })
                role.insert(ignore_permissions=True)
                frappe.db.commit()
                print(f"SUKSES: Peran '{role_name}' telah berhasil dibuat.")
            except Exception as e:
                print(f"GAGAL: Tidak dapat membuat peran '{role_name}'. Error: {e}")
                frappe.db.rollback()
        else:
            print(f"INFO: Peran '{role_name}' sudah ada.")

    print("Verifikasi peran selesai.")
