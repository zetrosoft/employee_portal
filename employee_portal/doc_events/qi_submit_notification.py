import frappe
from frappe import _
from frappe import publish_realtime

def send_notification_on_submit(doc, method):
    """
    On submission of Quality Inspection, send a notification to
    Purchasing and Stock roles.
    """
    # Ensure there is a linked Purchase Receipt to notify about
    if not doc.purchase_receipt:
        return

    frappe.log_error(title="[QI Notif]", message=f"Preparing notification for submitted QI {doc.name} linked to PR {doc.purchase_receipt}.")

    roles_to_notify = [
        'Purchase User', 'Purchase Manager', 'Stock Manager', 'Stock User'
    ]
    
    users_to_notify = get_users_with_roles(roles_to_notify)

    if users_to_notify:
        # The 'status' field in Quality Inspection holds the result (e.g., Accepted, Rejected)
        inspection_status = doc.status or "N/A"

        notification_subject = f"Hasil Inspeksi untuk PR {doc.purchase_receipt}"
        notification_content = f"Quality Inspection {doc.name} untuk Purchase Receipt {doc.purchase_receipt} telah selesai dengan hasil: {inspection_status}."
        
        # Link the notification to the related Purchase Receipt for better context
        linked_doctype = "Purchase Receipt"
        linked_docname = doc.purchase_receipt

        send_notification(users_to_notify, notification_subject, notification_content, linked_doctype, linked_docname)
        frappe.log_error(title="[QI Notif]", message=f"Notifikasi hasil QI {doc.name} dikirim ke {len(users_to_notify)} user.")
    else:
        frappe.log_error(title="[QI Notif]", message=f"Tidak ada user yang ditemukan untuk dinotifikasi pada QI {doc.name}.")


# --- Helper Functions ---

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
