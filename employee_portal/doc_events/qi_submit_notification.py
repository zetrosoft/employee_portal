import frappe
from frappe import _, publish_realtime


def send_notification_on_submit(doc, method):
    """
    On submission of a Quality Inspection, sends a notification to the relevant
    department based on the inspection type (Incoming, In Process, or Outgoing).
    """
    frappe.log_error(title="[QI Notif Debug]", message=f"Fungsi send_notification_on_submit dipanggil untuk QI: {doc.name}")

    if not doc.reference_name:
        frappe.log_error(title="[QI Notif Debug]", message=f"QI {doc.name}: reference_name kosong. Notifikasi dibatalkan.")
        return

    # --- Ambil owner dari dokumen referensi ---
    reference_doc_owner = frappe.db.get_value(doc.reference_type, doc.reference_name, "owner")
    
    # --- Tentukan users spesifik untuk dinotifikasi ---
    users_to_notify_list = []
    if reference_doc_owner:
        users_to_notify_list.append(reference_doc_owner)
    
    # Tambahkan peran umum yang selalu ingin dinotifikasi untuk semua QI (opsional, uncomment jika diperlukan)
    # Misalnya, semua System Manager atau Quality Manager
    # roles_to_notify_always = ['System Manager', 'Quality Manager']
    # users_to_notify_list.extend(get_users_with_roles(roles_to_notify_always))

    # Hapus duplikasi jika owner juga termasuk dalam peran umum
    users_to_notify_list = list(set(users_to_notify_list))


    notification_subject = f"Hasil Inspeksi Kualitas untuk {doc.reference_type} {doc.reference_name}"
    inspection_status = doc.status or "N/A"
    colored_status = f"<b style='color:green;'>{inspection_status}</b>" if inspection_status == "Accepted" else f"<b style='color:red;'>{inspection_status}</b>"
    notification_content = f"Inspeksi Kualitas untuk {doc.reference_type} {doc.reference_name} telah selesai dengan hasil: {colored_status}. Silakan tinjau."

    # frappe.log_error(title="[QI Notif Debug]", message=f"QI {doc.name}: users_to_notify_list: {users_to_notify_list}") # Debugging
    if users_to_notify_list:
        linked_doctype = doc.reference_type
        linked_docname = doc.reference_name

        send_notification(users_to_notify_list, notification_subject, notification_content, linked_doctype, linked_docname)
        frappe.log_error(title="[QI Notif]", message=f"Notifikasi hasil QI {doc.name} dikirim ke {len(users_to_notify_list)} user ({users_to_notify_list}) untuk {doc.reference_type} {doc.reference_name}.")
    else:
        frappe.log_error(title="[QI Notif]", message=f"QI {doc.name}: Tidak ada user yang ditemukan (owner atau peran umum) untuk dinotifikasi pada {doc.reference_type} {doc.reference_name}. Notifikasi dibatalkan.")


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
