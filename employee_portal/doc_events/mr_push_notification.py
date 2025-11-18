import frappe
from frappe import publish_realtime


def execute(doc, method):
    """
    Sends push notifications based on Material Request workflow state changes.
    """
    frappe.log_error(title="[MR Notification Debug]", message=f"--- Script execute dipanggil untuk {doc.name} ---")

    try:
        doc_before_save = doc.get_doc_before_save()

        if not doc_before_save:
            return

        if doc.workflow_state == doc_before_save.workflow_state:
            return

        # --- KONDISI 1: Dokumen membutuhkan persetujuan ---
        pending_states = ['Pending PM Approval', 'Pending Stock User Review', 'Pending SM Approval']
        if doc.workflow_state in pending_states:

            action_for_state = {
                'Pending PM Approval': 'Approve',
                'Pending Stock User Review': 'Forward to Manager',
                'Pending SM Approval': 'Approve and Submit'
            }

            current_action = action_for_state.get(doc.workflow_state)

            if not current_action:
                return

            # Find the role that is allowed to approve from the current state
            approver_role = frappe.get_value(
                "Workflow Transition",
                {
                    "parent": "Material Request Approval",
                    "state": doc.workflow_state,
                    "action": current_action,
                },
                "allowed"
            )

            if not approver_role:
                return

            # Get users with the approver role
            approvers_tuple = frappe.db.sql("""
                SELECT T1.parent FROM `tabHas Role` AS T1
                JOIN `tabUser` AS T2 ON T1.parent = T2.name
                WHERE T1.role = %s AND T2.enabled = 1
            """, (approver_role,))
            approvers = [row[0] for row in approvers_tuple]

            if approvers:
                notification_title = f"Persetujuan MR Dibutuhkan: {doc.name}"
                notification_content = f"Material Request {doc.name} menunggu tindakan Anda."

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

                frappe.log_error(title="[MR Notification Debug]", message=f"Notifikasi persetujuan untuk {doc.name} dikirim ke role {approver_role}.")
            else:
                pass

        # --- KONDISI 2: Dokumen ditolak ---
        elif doc.workflow_state == 'Rejected':

            user_to_notify = doc.owner
            if user_to_notify:
                notification_title = f"Material Request Ditolak: {doc.name}"
                notification_content = f"Material Request {doc.name} telah Ditolak. Status dokumen sekarang Dibatalkan."

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

                if doc.docstatus == 0:
                    frappe.db.set_value(doc.doctype, doc.name, 'docstatus', 2, update_modified=False)

                frappe.log_error(title="[MR Notification Debug]", message=f"Notifikasi penolakan untuk {doc.name} dikirim ke {user_to_notify} dan docstatus di set ke 2.")

        # --- KONDISI 3: Dokumen telah disetujui (Submitted) ---
        elif doc.workflow_state == 'Submitted' and doc.status == 1:

            users_to_notify = {doc.owner}
            purchasing_roles = ['Purchase User', 'Purchase Manager']

            for role in purchasing_roles:
                users_in_role_tuple = frappe.db.sql("""
                    SELECT T1.parent FROM `tabHas Role` AS T1
                    JOIN `tabUser` AS T2 ON T1.parent = T2.name
                    WHERE T1.role = %s AND T2.enabled = 1
                """, (role,))
                
                for row in users_in_role_tuple:
                    users_to_notify.add(row[0])

            if users_to_notify:
                notification_title = f"MR Disetujui: {doc.name}"
                notification_content = f"Material Request {doc.name} telah disetujui dan siap untuk proses selanjutnya."

                # Filter out any potential None values from the set
                valid_users = {user for user in users_to_notify if user}

                for user_id in valid_users:
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

                user_list_str = ", ".join(list(valid_users))
                frappe.log_error(title="[MR Notification Debug]", message=f"Notifikasi 'Submitted' untuk {doc.name} dikirim ke: {user_list_str}.")

    except Exception:
        frappe.log_error(
            title='Gagal Menjalankan Hook Notifikasi Material Request',
            message=frappe.get_traceback()
        )
