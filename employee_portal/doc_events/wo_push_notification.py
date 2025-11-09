import frappe

# Bungkus seluruh logika ke dalam fungsi 'execute'
def execute(doc, method):
    # 'method' di sini akan berisi 'on_update', tetapi jarang digunakan
    # Semua logika lama Anda dimulai dari sini

    try:
        # Metode modern dan aman untuk mendapatkan state dokumen sebelum disimpan.
        doc_before_save = doc.get_doc_before_save()

        # Keluar jika ini adalah dokumen baru atau jika state workflow tidak berubah.
        if not doc_before_save or doc.workflow_state == doc_before_save.workflow_state:
            return

        # --- KONDISI 1: Dokumen membutuhkan persetujuan ---
        if doc.workflow_state == 'Pending PM Approval':
            
            # (Logika notifikasi Pending PM Approval Anda)
            approver_role = frappe.get_value(
                "Workflow Transition",
                {
                    "parent": doc.workflow_name,
                    "state": doc_before_save.workflow_state,
                    "action": "Approve",
                },
                "allowed"
            )

            if not approver_role:
                frappe.log_error(f"Workflow hook: Approver role not found for Work Order {doc.name} from state {doc_before_save.workflow_state}.")
                return

            approvers = frappe.get_list('User', filters={'enabled': 1, 'roles': approver_role}, fields=['name'])
            
            if approvers:
                notification_title = f"Persetujuan WO Dibutuhkan: {doc.name}"
                notification_content = f"Work Order {doc.name} menunggu persetujuan Anda."
                
                for user in approvers:
                    frappe.send_notification(
                        title=notification_title,
                        content=notification_content,
                        doctype="Work Order",
                        name=doc.name,
                        for_user=user.name,
                        is_seen=0
                    )
                    frappe.publish_realtime('notification', user=user.name)
                
                frappe.log_event("Work Order", f"Notifikasi persetujuan untuk {doc.name} dikirim ke role {approver_role}.")

        # --- KONDISI 2: Dokumen ditolak ---
        elif doc.workflow_state == 'Rejected':
            
            # Logika force docstatus = 2 (sesuai permintaan Anda)
            if doc.docstatus == 0:
                # Menggunakan frappe.db.set_value untuk mengubah docstatus ke Canceled (2)
                # tanpa memicu save rekursif.
                frappe.db.set_value(doc.doctype, doc.name, 'docstatus', 2, update_modified=False)

            # Kirim notifikasi penolakan ke pembuat dokumen.
            user_to_notify = doc.owner
            if user_to_notify:
                notification_title = f"Work Order Ditolak: {doc.name}"
                notification_content = f"Work Order {doc.name} telah Ditolak. Status dokumen sekarang Dibatalkan."

                frappe.send_notification(
                    title=notification_title,
                    content=notification_content,
                    doctype="Work Order",
                    name=doc.name,
                    for_user=user_to_notify,
                    is_seen=0
                )
                frappe.publish_realtime('notification', user=user_to_notify)
                frappe.log_event("Work Order", f"Notifikasi penolakan untuk {doc.name} dikirim ke {user_to_notify} dan docstatus di set ke 2.")

    except Exception:
        frappe.log_error(
            title='Gagal Menjalankan Hook Notifikasi Work Order',
            message=frappe.get_traceback()
        )