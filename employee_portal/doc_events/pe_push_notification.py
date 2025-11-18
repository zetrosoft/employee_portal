import frappe
from frappe import publish_realtime


def execute(doc, method):
    frappe.log_error(title="[PE Notification Debug]", message=f"--- Script execute dipanggil untuk {doc.name} ---")

    try:
        doc_before_save = doc.get_doc_before_save()

        if not doc_before_save:
            frappe.log_error(title="[PE Notification Debug]", message="Keluar: Tidak ada doc_before_save (kemungkinan dokumen baru).")
            return

        frappe.log_error(title="[PE Notification Debug]", message=f"Status Sebelumnya: {doc_before_save.workflow_state}, Status Sekarang: {doc.workflow_state}")

        if doc.workflow_state == doc_before_save.workflow_state:
            frappe.log_error(title="[PE Notification Debug]", message="Keluar: workflow_state tidak berubah.")
            return

        # --- KONDISI 1: Menunggu Persetujuan Accounts Manager ---
        if doc.workflow_state == 'Pending AM Approval':
            frappe.log_error(title="[PE Notification Debug]", message="Masuk kondisi: 'Pending AM Approval'")

            approver_role = "Accounts Manager"

            approvers_tuple = frappe.db.sql("""
                SELECT T1.parent FROM `tabHas Role` AS T1
                JOIN `tabUser` AS T2 ON T1.parent = T2.name
                WHERE T1.role = %s AND T2.enabled = 1
            """, (approver_role,))
            approvers = [row[0] for row in approvers_tuple]

            frappe.log_error(title="[PE Notification Debug]", message=f"Nilai dari approver_role: {approver_role}")
            frappe.log_error(title="[PE Notification Debug]", message=f"Nilai dari approvers: {approvers}")

            if approvers:
                notification_title = f"Persetujuan PE Dibutuhkan: {doc.name}"
                notification_content = f"Payment Entry {doc.name} menunggu persetujuan Anda."

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

                frappe.log_error(title="[PE Notification Debug]", message=f"Notifikasi persetujuan untuk {doc.name} dikirim ke role {approver_role}.")
            else:
                frappe.log_error(title="[PE Notification Debug]", message=f"Tidak ada user yang ditemukan untuk role: {approver_role}")

        # --- KONDISI 3: Dokumen ditolak ---
        elif doc.workflow_state == 'Rejected':
            frappe.log_error(title="[PE Notification Debug]", message="Masuk kondisi: 'Rejected'")

            accounts_managers = [row[0] for row in frappe.db.sql("SELECT T1.parent FROM `tabHas Role` AS T1 JOIN `tabUser` AS T2 ON T1.parent = T2.name WHERE T1.role = 'Accounts Manager' AND T2.enabled = 1")]
            recipients = [doc.owner, *accounts_managers] # Notify owner and Accounts Manager

            if recipients:
                notification_title = f"Payment Entry Ditolak: {doc.name}"
                notification_content = f"Payment Entry {doc.name} telah Ditolak. Status dokumen sekarang Dibatalkan."

                for user_id in recipients:
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
                frappe.log_error(title="[PE Notification Debug]", message=f"Notifikasi penolakan untuk {doc.name} dikirim ke {recipients} dan docstatus di set ke 2.")

        # --- KONDISI 4: Dokumen telah disetujui (Submitted) ---
        elif doc.workflow_state == 'Submitted':
            frappe.log_error(title="[PE Notification Debug]", message="Masuk kondisi: 'Submitted'")

            accounts_managers = [row[0] for row in frappe.db.sql("SELECT T1.parent FROM `tabHas Role` AS T1 JOIN `tabUser` AS T2 ON T1.parent = T2.name WHERE T1.role = 'Accounts Manager' AND T2.enabled = 1")]
            recipients = [doc.owner, *accounts_managers] # Notify owner and Accounts Manager

            if recipients:
                notification_title = f"PE {doc.name} telah disubmit"
                notification_content = f"Payment Entry {doc.name} Anda telah disetujui dan disubmit."

                for user_id in recipients:
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
                frappe.log_error(title="[PE Notification Debug]", message=f"Notifikasi 'Submitted' untuk {doc.name} dikirim ke {recipients}.")

    except Exception:
        frappe.log_error(
            title='Gagal Menjalankan Hook Notifikasi Payment Entry',
            message=frappe.get_traceback()
        )
