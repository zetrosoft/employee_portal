import frappe
from frappe import publish_realtime


def execute(doc, method):
    frappe.log_error(title="[DN Notification Debug]", message=f"--- Script dn_push_notification dipanggil untuk {doc.name} ---")

    try:
        doc_before_save = doc.get_doc_before_save()
        # Only send notification if workflow state changed to 'Approved'
        if doc.workflow_state == 'Approved' and doc_before_save and doc.workflow_state != doc_before_save.workflow_state:
            frappe.log_error(title="[DN Notification Debug]", message=f"Delivery Note {doc.name} masuk kondisi: 'Approved'")

            # Define roles to be notified
            approver_roles = ["Quality User", "Quality Manager"]
            
            # Get users with specified roles
            users_to_notify = get_users_with_roles(approver_roles)

            if users_to_notify:
                title = f"Inspeksi Kualitas Dibutuhkan: Delivery Note {doc.name}"
                content = f"Pengiriman dari Delivery Note {doc.name} butuh inspeksi kualitas final sebelum dikirim. Mohon buat Quality Inspection."
                
                send_notification(users_to_notify, title, content, doc.doctype, doc.name)
                frappe.log_error(title="[DN Notification Debug]", message=f"Notifikasi 'Approved' Delivery Note {doc.name} dikirim ke {len(users_to_notify)} user.")
            else:
                frappe.log_error(title="[DN Notification Debug]", message=f"Tidak ada user Quality User/Manager yang ditemukan untuk dinotifikasi pada Delivery Note {doc.name}.")

    except Exception:
        frappe.log_error(
            title='Gagal Menjalankan Hook Notifikasi Delivery Note',
            message=frappe.get_traceback()
        )

# --- Helper Functions (copied from qi_submit_notification.py for consistency) ---

def get_users_with_roles(roles):
    """Get a unique set of enabled users from a list of roles."""
    users = set()
    for role in roles:
        users_in_role = frappe.get_all("Has Role", filters={"role": role, "parenttype": "User"}, fields=["parent"])
        for user_entry in users_in_role:
            user_name = user_entry.parent
            if frappe.db.get_value("User", user_name, "enabled"):
                users.add(user_name)
    return list(users)

def send_notification(users, subject, content, doc_type, doc_name):
    """Creates Notification Log and publishes realtime event."""
    for user in users:
        notification_log = {
            "doctype": "Notification Log",
            "type": "Alert",
            "document_type": doc_type,
            "document_name": doc_name,
            "subject": subject,
            "for_user": user,
            "email_content": content
        }
        frappe.get_doc(notification_log).insert(ignore_permissions=True)
        publish_realtime('notification', user=user)
