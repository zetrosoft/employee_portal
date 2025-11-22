import frappe
from frappe import _, publish_realtime


def send_notification_on_submit(doc, method):
    """
    On submission of a Quality Inspection, sends a notification to the relevant
    department based on the inspection type (Incoming, In Process, or Outgoing).
    """
    if not doc.reference_name:
        return

    roles_to_notify = []
    notification_subject = ""
    notification_content = ""

    inspection_status = doc.status or "N/A"
    colored_status = f"<b style='color:green;'>{inspection_status}</b>" if inspection_status == "Accepted" else f"<b style='color:red;'>{inspection_status}</b>"

    # Determine recipients and message based on Inspection Type
    if doc.inspection_type == 'Incoming' and doc.reference_type == 'Purchase Receipt':
        roles_to_notify = ['Purchase User', 'Purchase Manager']
        notification_subject = f"Hasil Inspeksi untuk PR {doc.reference_name} ({inspection_status})"
        notification_content = f"Inspeksi Kualitas untuk Purchase Receipt {doc.reference_name} telah selesai dengan hasil: {colored_status}."

    elif doc.inspection_type == 'In Process' and doc.reference_type == 'Stock Entry':
        roles_to_notify = ['Production User', 'Production Manager']
        notification_subject = f"Hasil Inspeksi untuk Produksi {doc.reference_name} ({inspection_status})"
        notification_content = f"Inspeksi Kualitas untuk hasil produksi (Stock Entry: {doc.reference_name}) telah selesai dengan hasil: {colored_status}."

    elif doc.inspection_type == 'Outgoing' and doc.reference_type == 'Delivery Note':
        roles_to_notify = ['Logistics User', 'Logistics Manager']
        notification_subject = f"Hasil Inspeksi untuk Pengiriman {doc.reference_name} ({inspection_status})"
        notification_content = f"Inspeksi Kualitas untuk pengiriman (Delivery Note: {doc.reference_name}) telah selesai dengan hasil: {colored_status}."

    else:
        # If no specific type matches, do not send a notification
        return

    users_to_notify = get_users_with_roles(roles_to_notify)

    if users_to_notify:
        linked_doctype = doc.reference_type
        linked_docname = doc.reference_name

        send_notification(users_to_notify, notification_subject, notification_content, linked_doctype, linked_docname)
        frappe.log_error(title="[QI Notif]", message=f"Notifikasi hasil QI {doc.name} dikirim ke {len(users_to_notify)} user untuk tipe {doc.inspection_type}.")
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
