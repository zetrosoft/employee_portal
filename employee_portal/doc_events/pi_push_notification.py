import frappe
from frappe import publish_realtime


def execute(doc, method):
    """
    Sends push notifications based on Purchase Invoice workflow state changes.
    """
    frappe.log_error(title="[PI Notification Debug]", message=f"--- Script execute dipanggil untuk {doc.name} ---")

    try:
        doc_before_save = doc.get_doc_before_save()

        if not doc_before_save:
            return

        if doc.workflow_state == doc_before_save.workflow_state:
            return

        # --- KONDISI 1: Dokumen membutuhkan persetujuan ---
        pending_states = ['Pending Accounts User Review', 'Pending AM Approval']
        if doc.workflow_state in pending_states:

            # Get the role that is allowed to edit the current state
            editable_by_role = frappe.db.get_value(
                "Workflow Document State",
                {
                    "parent": "Purchase Invoice Approval",
                    "state": doc.workflow_state,
                },
                "allow_edit"
            )

            if not editable_by_role:
                return

            # Get users with that role
            users_to_notify_tuple = frappe.db.sql("""
                SELECT T1.parent FROM `tabHas Role` AS T1
                JOIN `tabUser` AS T2 ON T1.parent = T2.name
                WHERE T1.role = %s AND T2.enabled = 1
            """, (editable_by_role,))
            users_to_notify = [row[0] for row in users_to_notify_tuple]

            if users_to_notify:
                notification_title = f"Persetujuan PI Dibutuhkan: {doc.name}"
                notification_content = f"Purchase Invoice {doc.name} menunggu tindakan Anda."

                for user_id in users_to_notify:
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

                frappe.log_error(title="[PI Notification Debug]", message=f"Notifikasi persetujuan untuk {doc.name} dikirim ke role {editable_by_role}.")
            else:
                pass

        # --- KONDISI 2: Dokumen ditolak ---
        elif doc.workflow_state == 'Rejected':

            user_to_notify = doc.owner
            if user_to_notify:
                notification_title = f"Purchase Invoice Ditolak: {doc.name}"
                notification_content = f"Purchase Invoice {doc.name} telah Ditolak. Status dokumen sekarang Dibatalkan."

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

                # Set docstatus to 2 (Cancelled) only after notification is sent
                if doc.docstatus == 0:
                    frappe.db.set_value(doc.doctype, doc.name, 'docstatus', 2, update_modified=False)

                frappe.log_error(title="[PI Notification Debug]", message=f"Notifikasi penolakan untuk {doc.name} dikirim ke {user_to_notify} dan docstatus di set ke 2.")

        # --- KONDISI 3: Dokumen telah disetujui (Submitted) ---
        elif doc.workflow_state == 'Submitted':

            user_to_notify = doc.owner
            if user_to_notify:
                notification_title = f"PI {doc.name} telah disubmit"
                notification_content = f"Purchase Invoice {doc.name} Anda telah disetujui dan disubmit."

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
                frappe.log_error(title="[PI Notification Debug]", message=f"Notifikasi 'Submitted' untuk {doc.name} dikirim ke {user_to_notify}.")

    except Exception:
        frappe.log_error(
            title='Gagal Menjalankan Hook Notifikasi Purchase Invoice',
            message=frappe.get_traceback()
        )
