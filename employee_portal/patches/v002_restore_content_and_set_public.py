import json
import os

import frappe


def execute():
    """
    Patch v2: Memulihkan konten workspace dari file fixture JSON asli
    dan mengatur ulang workspace menjadi publik. Ini untuk memperbaiki efek samping
    dari patch v001.
    """
    log = frappe.logger("workspace_restore_patch")
    log.info("Memulai patch v2: restore_workspace_content_and_set_public")

    base_path = frappe.get_app_path("employee_portal", "fixtures")

    workspaces_to_restore = {
        "Leaves": os.path.join(base_path, "leaves_workspace.json"),
        "Expense Claims": os.path.join(base_path, "expense_claims_workspace.json")
    }

    for name, fixture_path in workspaces_to_restore.items():
        if not frappe.db.exists("Workspace", name):
            log.warning(f"Workspace '{name}' tidak ditemukan di DB. Melewati pemulihan untuk workspace ini.")
            continue

        try:
            # 1. Ambil dokumen dari database
            workspace_doc = frappe.get_doc("Workspace", name)

            # 2. Baca file fixture
            with open(fixture_path) as f:
                fixture_data = json.load(f)

            log.info(f"Memulihkan konten untuk '{name}' dari {fixture_path}")

            # 3. Hapus konten lama (tabel anak) untuk mencegah duplikasi
            workspace_doc.set("links", [])
            workspace_doc.set("shortcuts", [])
            workspace_doc.set("charts", [])
            workspace_doc.set("number_cards", [])
            workspace_doc.set("custom_blocks", [])

            # 4. Timpa field level atas dan konten dari fixture
            workspace_doc.content = fixture_data.get("content")
            workspace_doc.icon = fixture_data.get("icon")
            workspace_doc.sequence_id = fixture_data.get("sequence_id")

            # 5. Atur ulang menjadi publik dan hapus peran spesifik
            workspace_doc.public = 1
            workspace_doc.set("roles", [])

            # 6. Simpan dokumen
            workspace_doc.save(ignore_permissions=True)
            log.info(f"Berhasil memulihkan dan mengatur ulang Workspace '{name}'.")

        except FileNotFoundError:
            log.error(f"File fixture tidak ditemukan: {fixture_path}. Tidak dapat memulihkan '{name}'.")
        except Exception as e:
            log.error(f"Terjadi kesalahan saat memulihkan Workspace '{name}': {e}", exc_info=True)

    frappe.db.commit()
    log.info("Patch v2: restore_workspace_content_and_set_public selesai.")
