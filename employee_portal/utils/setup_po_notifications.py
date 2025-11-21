import frappe


def create_notification_for_workflow_state(doctype, state, subject, message, recipients, condition=None):
    # Nama notifikasi: PO-Pending-PM-Notif
    notification_name = f"{doctype[:2]}-{state.replace(' ', '-')}-Notif"

    # Hapus notifikasi yang sudah ada dengan nama yang sama
    if frappe.db.exists("Notification", notification_name):
        frappe.delete_doc("Notification", notification_name, ignore_permissions=True)
        frappe.db.commit()
        print(f"Existing Notification '{notification_name}' deleted.")

    # Sekarang buat notifikasi baru
    notification = frappe.get_doc({
        "doctype": "Notification",
        "name": notification_name,
        "document_type": doctype,
        "subject": subject,
        "message": message,
        "channel": "In App Alert",
        "event": "Value Change",
        "value_field": "workflow_state", # FIX: Ini adalah kolom yang harus diperiksa perubahannya
        "value": state, # Nilai baru yang memicu notifikasi
        "set_property_after_alert": "",
        "recipients": []
    })

    for recipient_role in recipients:
        # FIX: Menggunakan 'receiver_by_role' untuk menentukan penerima berdasarkan Role
        notification.append("recipients", {
            "receiver_by_role": recipient_role
        })

    # Menambahkan kondisi jika ada
    if condition:
        notification.conditions = condition

    try:
        frappe.log_error(f"data notif : {notification.as_dict()}", "Create Workflow Notification Data")
        notification.insert(ignore_permissions=True)
        frappe.db.commit()
        print(f"Notification '{notification_name}' created successfully.")
    except Exception as e:
        frappe.log_error(f"Error creating notification {notification_name}: {e}", "Create Workflow Notification")


@frappe.whitelist()
def setup_po_notifications():
    doctype = "Purchase Order"

    # 1. Ketika Purchase User membuat PO -> Submit (next_state: Pending PM)
    create_notification_for_workflow_state(
        doctype=doctype,
        state="Pending PM",
        subject="""Purchase Order {{ doc.name }} menunggu persetujuan""",
        message="""Purchase Order <b>{{ doc.name }}</b> dari <b>{{ doc.owner }}</b> (total: {{ frappe.format(doc.grand_total, "Currency") }}) menunggu persetujuan Anda.""",
        recipients=["Purchase Manager"]
    )

    # 2. Ketika Purchase Manager Approve (next_state: Pending AM)
    create_notification_for_workflow_state(
        doctype=doctype,
        state="Pending AM",
        subject="""Purchase Order {{ doc.name }} menunggu persetujuan""",
        message="""Purchase Order <b>{{ doc.name }}</b> dari <b>{{ doc.owner }}</b> (total: {{ frappe.format(doc.grand_total, "Currency") }}) menunggu persetujuan Anda dari Purchase Manager.""",
        recipients=["Accounts Manager"]
    )

    # 3. Ketika Accounts Manager Approve (kondisional) -> next_state: Pending Director
    create_notification_for_workflow_state(
        doctype=doctype,
        state="Pending Director",
        subject="""Purchase Order {{ doc.name }} menunggu persetujuan""",
        message="""Purchase Order <b>{{ doc.name }}</b> dari <b>{{ doc.owner }}</b> (total: {{ frappe.format(doc.grand_total, "Currency") }}) menunggu persetujuan Anda dari Accounts Manager.""",
        recipients=["Director"]
    )

    # 4. Notifikasi penolakan (Hanya berdasar status Cancelled, tanpa kondisi user yang menolak)
    # Ini akan terpicu jika workflow_state berubah menjadi "Cancelled".
    create_notification_for_workflow_state(
        doctype=doctype,
        state="Cancelled",
        subject="""Purchase Order {{ doc.name }} DITOLAK""",
        message="""Purchase Order <b>{{ doc.name }}</b> telah DITOLAK dalam proses persetujuan.""",
        recipients=["Purchase User", "Purchase Manager", "Accounts Manager"]
        # HAPUS kondisi kompleks yang tidak diperlukan.
    )

    # 5. Ketika Accounts Manager Approve (kondisional) -> next_state: Submitted (Nilai Kecil)
    create_notification_for_workflow_state(
        doctype=doctype,
        state="Submitted-Small",
        subject="""Purchase Order {{ doc.name }} di-SUBMIT (Nilai Kecil)""",
        message="""Purchase Order <b>{{ doc.name }}</b> telah di-SUBMIT oleh Accounts Manager (nilai kecil).""",
        recipients=["Purchase User", "Purchase Manager", "Accounts Manager"],
        # FIX: Pisahkan Submitted menjadi dua notif unik (Submitted-Small dan Submitted-Large)
        condition='doc.workflow_state == "Submitted" and doc.grand_total <= 10000000'
    )

    # 6. Ketika Director Approve (next_state: Submitted) (Nilai Besar)
    create_notification_for_workflow_state(
        doctype=doctype,
        state="Submitted-Large",
        subject="""Purchase Order {{ doc.name }} di-SUBMIT (Nilai Besar)""",
        message="""Purchase Order <b>{{ doc.name }}</b> telah di-SUBMIT oleh Director (nilai besar).""",
        recipients=["Purchase User", "Purchase Manager", "Accounts Manager"],
        # FIX: Pisahkan Submitted menjadi dua notif unik (Submitted-Small dan Submitted-Large)
        condition='doc.workflow_state == "Submitted" and doc.grand_total > 10000000'
    )

    print("Purchase Order notifications setup completed.")

if __name__ == "__main__":
    setup_po_notifications()
