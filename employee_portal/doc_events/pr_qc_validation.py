import frappe
from frappe import _
from frappe import publish_realtime

def execute_validation(doc, method):
    """
    Handles validation and notifications for Purchase Receipts containing
    'Persediaan Bahan Baku' item group.
    """
    # Check if the document contains the specified item group
    has_bahan_baku = False
    item_codes = [item.item_code for item in doc.items]
    if item_codes:
        has_bahan_baku = frappe.db.exists("Item", {
            "name": ("in", item_codes),
            "item_group": "Persediaan Bahan Baku"
        })

    if not has_bahan_baku:
        return

    # --- Logic for Notification on Save (runs on 'on_update' hook) ---
    if method == "on_update" and doc.docstatus == 0:
        notify_on_save(doc)

    # --- Logic for Validation on Submit (runs on 'before_submit' hook) ---
    elif method == "before_submit":
        validate_on_submit(doc)

def notify_on_save(doc):
    """Send notification to QC and other roles when a draft PR is saved."""
    frappe.log_error(title="[PR QC Notif]", message=f"Preparing notification for PR {doc.name}.")
    
    roles_to_notify = [
        'Quality User', 'Quality Manager', 'Purchase User', 
        'Purchase Manager', 'Stock Manager'
    ]
    
    users_to_notify = get_users_with_roles(roles_to_notify)

    if users_to_notify:
        notification_subject = f"Quality Inspection Dibutuhkan untuk PR: {doc.name}"
        notification_content = f"Purchase Receipt {doc.name} berisi item 'Persediaan Bahan Baku' dan membutuhkan inspeksi kualitas."
        
        send_notification(users_to_notify, notification_subject, notification_content, doc.doctype, doc.name)
        frappe.log_error(title="[PR QC Notif]", message=f"Notifikasi QC dikirim untuk PR {doc.name} ke {len(users_to_notify)} user.")
    else:
        frappe.log_error(title="[PR QC Notif]", message=f"Tidak ada user yang ditemukan untuk dinotifikasi pada PR {doc.name}.")


def validate_on_submit(doc):
    """Validate if Quality Inspection is completed before submitting."""
    # Check for a linked, submitted Quality Inspection
    qi_doc_submitted = frappe.db.exists("Quality Inspection", {
        "purchase_receipt": doc.name,
        "docstatus": 1
    })

    if not qi_doc_submitted:
        # Provide a more helpful message if a QI exists but is not submitted
        qi_doc_draft = frappe.db.exists("Quality Inspection", {"purchase_receipt": doc.name, "docstatus": 0})
        if qi_doc_draft:
            msg = _("Quality Inspection {0} belum di-submit. Harap selesaikan proses inspeksi terlebih dahulu.").format(qi_doc_draft)
        else:
            msg = _("Quality Inspection untuk Purchase Receipt ini belum dibuat atau diselesaikan.")
        
        frappe.throw(msg, title=_("Inspeksi Belum Selesai"))

# --- Helper Functions ---

def get_users_with_roles(roles):
    """Get a unique set of enabled users from a list of roles."""
    users = set()
    for role in roles:
        users_in_role = frappe.get_all("Has Role", filters={"role": role, "parenttype": "User"}, fields=["parent"])
        for user_entry in users_in_role:
            user_name = user_entry.parent
            # Check if user is enabled
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
