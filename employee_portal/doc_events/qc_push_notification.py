import frappe
from frappe import publish_realtime


def execute(doc, method):
    frappe.log_error(title="[QC Notification Debug]", message=f"--- Script execute dipanggil untuk {doc.name} ---")

    try:
        doc_before_save = doc.get_doc_before_save()

        if not doc_before_save:
            frappe.log_error(title="[QC Notification Debug]", message="Keluar: Tidak ada doc_before_save (kemungkinan dokumen baru).")
            return

        frappe.log_error(title="[QC Notification Debug]", message=f"Status Sebelumnya: {doc_before_save.workflow_state}, Status Sekarang: {doc.workflow_state}")

        if doc.workflow_state == doc_before_save.workflow_state:
            frappe.log_error(title="[QC Notification Debug]", message="Keluar: workflow_state tidak berubah.")
            return

        # --- KONDISI 1: Menunggu Persetujuan Quality Manager ---
        if doc.workflow_state == 'Pending QAM Approval':
            frappe.log_error(title="[QC Notification Debug]", message="Masuk kondisi: 'Pending QAM Approval'")

            approver_role = "Quality Manager"

            approvers_tuple = frappe.db.sql("""
                SELECT T1.parent FROM `tabHas Role` AS T1
                JOIN `tabUser` AS T2 ON T1.parent = T2.name
                WHERE T1.role = %s AND T2.enabled = 1
            """, (approver_role,))
            approvers = [row[0] for row in approvers_tuple]

            frappe.log_error(title="[QC Notification Debug]", message=f"Nilai dari approver_role: {approver_role}")
            frappe.log_error(title="[QC Notification Debug]", message=f"Nilai dari approvers: {approvers}")

            if approvers:
                notification_title = f"Persetujuan QC Dibutuhkan: {doc.name}"
                notification_content = f"Quality Inspection {doc.name} menunggu persetujuan Anda."

                for user_id in approvers:
                    notification_log = {
                        "doctype": "Notification Log",
                        "type": "Alert",
                        "document_type": doc.doctype,
                        "document_name": doc.name,
                        "subject": notification_title,
                        "for_user": user_id,
                        "email_content": notification_content
                    }
                    frappe.get_doc(notification_log).insert(ignore_permissions=True)
                    publish_realtime('notification', user=user_id)

                frappe.log_error(title="[QC Notification Debug]", message=f"Notifikasi persetujuan untuk {doc.name} dikirim ke role {approver_role}.")
            else:
                frappe.log_error(title="[QC Notification Debug]", message=f"Tidak ada user yang ditemukan untuk role: {approver_role}")

        # --- KONDISI 2: Dokumen ditolak (Cancelled) ---
        elif doc.workflow_state == 'Rejected':
            frappe.log_error(title="[QC Notification Debug]", message="Masuk kondisi: 'Rejected'")

            # Set docstatus to 2 (Cancelled)
            if doc.docstatus == 0:
                frappe.db.set_value(doc.doctype, doc.name, 'docstatus', 2, update_modified=False)

            user_to_notify = doc.owner
            if user_to_notify:
                notification_title = f"Quality Inspection Ditolak: {doc.name}"
                notification_content = f"Quality Inspection {doc.name} telah Ditolak. Status dokumen sekarang Dibatalkan."

                notification_log = {
                    "doctype": "Notification Log",
                    "type": "Alert",
                    "document_type": doc.doctype,
                    "document_name": doc.name,
                    "subject": notification_title,
                    "for_user": user_to_notify,
                    "email_content": notification_content
                }
                frappe.get_doc(notification_log).insert(ignore_permissions=True)
                publish_realtime('notification', user=user_to_notify)
                frappe.log_error(title="[QC Notification Debug]", message=f"Notifikasi penolakan untuk {doc.name} dikirim ke {user_to_notify} dan docstatus di set ke 2.")

        # --- KONDISI 3: Dokumen telah disetujui (Submitted) ---
        elif doc.workflow_state == 'Submitted':
            frappe.log_error(title="[QC Notification Debug]", message="Masuk kondisi: 'Submitted'")

            # Set docstatus to 1 (Submitted)
            if doc.docstatus == 0:
                frappe.db.set_value(doc.doctype, doc.name, 'docstatus', 1, update_modified=False)

            user_to_notify = doc.owner
            if user_to_notify:
                notification_title = f"QC {doc.name} telah disubmit"
                notification_content = f"Quality Inspection {doc.name} Anda telah disetujui dan disubmit."

                notification_log = {
                    "doctype": "Notification Log",
                    "type": "Alert",
                    "document_type": doc.doctype,
                    "document_name": doc.name,
                    "subject": notification_title,
                    "for_user": user_to_notify,
                    "email_content": notification_content
                }
                frappe.get_doc(notification_log).insert(ignore_permissions=True)
                publish_realtime('notification', user=user_to_notify)
                frappe.log_error(title="[QC Notification Debug]", message=f"Notifikasi 'Submitted' untuk {doc.name} dikirim ke {user_to_notify} dan docstatus di set ke 1.")

    except Exception:
        frappe.log_error(
            title='Gagal Menjalankan Hook Notifikasi Quality Inspection',
            message=frappe.get_traceback()
        )
