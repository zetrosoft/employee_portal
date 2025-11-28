import frappe


def execute():
    """
    Patch untuk secara eksplisit memberikan akses Workspace ke Role.
    Ini berjalan sekali selama `bench migrate`.
    """
    # Menggunakan frappe.logger.info karena msgprint tidak selalu terlihat di console migrate
    log = frappe.logger("employee_portal_patch")
    log.info("Memulai patch: grant_workspace_access")

    workspaces_to_grant = ["Leaves", "Expense Claims"]
    target_role = "Employee User"

    if not frappe.db.exists("Role", target_role):
        log.warning(f"Role '{target_role}' tidak ditemukan. Patch dilewati.")
        return

    for workspace_name in workspaces_to_grant:
        if not frappe.db.exists("Workspace", workspace_name):
            log.warning(f"Workspace '{workspace_name}' tidak ditemukan. Melewati.")
            continue

        try:
            workspace = frappe.get_doc("Workspace", workspace_name)

            # Jika sudah publik, seharusnya tidak ada masalah.
            # Namun, jika ada kustomisasi, kita pastikan peran tetap ada.
            # frappe.msgprint tidak bekerja di patch, jadi gunakan log
            log.info(f"Memproses Workspace '{workspace_name}'. Public status: {workspace.public}")

            # Periksa apakah peran sudah ada di tabel 'roles'
            has_role_entry = False
            for r in workspace.get("roles"):
                if r.role == target_role:
                    has_role_entry = True
                    break

            if has_role_entry:
                log.info(f"Role '{target_role}' sudah memiliki akses ke Workspace '{workspace_name}'. Tidak ada perubahan.")
            else:
                # Jika peran belum ada, tambahkan.
                log.info(f"Menambahkan Role '{target_role}' ke Workspace '{workspace_name}'...")
                workspace.append("roles", {
                    "role": target_role
                })
                # Jika kita secara eksplisit menambahkan peran, lebih aman untuk membuatnya tidak publik
                # agar hanya peran yang terdaftar yang memiliki akses.
                # Ini akan menimpa for_all=1 jika ada kustomisasi.
                workspace.public = 0

                workspace.save(ignore_permissions=True)
                log.info(f"Berhasil menyimpan perubahan untuk Workspace '{workspace_name}'.")

        except Exception as e:
            log.error(f"Gagal memproses Workspace {workspace_name}: {e}", exc_info=True)
            # Jangan rollback agar patch lain bisa tetap berjalan

    frappe.db.commit()
    log.info("Patch grant_workspace_access selesai.")
