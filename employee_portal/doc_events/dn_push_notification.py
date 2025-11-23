import frappe
from frappe import publish_realtime


def execute(doc, method):
    """
    Handles sending notifications based on workflow state changes for Delivery Notes.
    """
    try:
        doc_before_save = doc.get_doc_before_save()
        if not doc_before_save or doc.workflow_state == doc_before_save.workflow_state:
            # If there's no previous state or the state hasn't changed, do nothing.
            return

        # Get the specific state transition
        transition = (doc_before_save.workflow_state, doc.workflow_state)
        frappe.log_error(title="[DN Notification]", message=f"State transition for {doc.name}: {transition}")

        # 1. Draft -> Pending Logistics Manager Approval
        if transition == ("Draft", "Pending Logistics Manager Approval"):
            notify(
                doc=doc,
                roles=["Logistics Manager"],
                subject=f"Approval Required: Delivery Note {doc.name}",
                content=f"Delivery Note {doc.name} from {doc.customer} requires your approval."
            )

        # 2. Pending LM Approval -> Pending QC Inspection
        elif transition == ("Pending Logistics Manager Approval", "Pending QC Inspection"):
            notify(
                doc=doc,
                roles=["Quality User", "Quality Manager"],
                subject=f"QC Inspection Required: Delivery Note {doc.name}",
                content=f"Delivery Note {doc.name} has been approved and requires a Quality Inspection."
            )

        # 3. Pending LM Approval -> Rejected
        elif transition == ("Pending Logistics Manager Approval", "Rejected"):
            notify(
                doc=doc,
                users=[doc.owner], # Notify the creator
                subject=f"Rejected: Your Delivery Note {doc.name}",
                content=f"Your Delivery Note {doc.name} has been rejected by the Logistics Manager."
            )

        # 4. Approved QC -> Submitted
        elif transition == ("Approved QC", "Submitted"):
            notify(
                doc=doc,
                roles=["Sales User", "Sales Manager"],
                subject=f"Submitted: Delivery Note {doc.name}",
                content=f"Delivery Note {doc.name} for customer {doc.customer} has been submitted and is ready for dispatch."
            )

    except Exception:
        frappe.log_error(
            title='Gagal Menjalankan Hook Notifikasi Delivery Note',
            message=frappe.get_traceback()
        )

# --- Generalized Helper Functions ---

def notify(doc, roles=None, users=None, subject="", content=""):
    """
    Sends notifications to a list of roles or users.
    """
    if not roles and not users:
        frappe.log_error(title="[DN Notification]", message=f"Notification for {doc.name} aborted: No recipients specified.")
        return

    recipients = set(users or [])
    if roles:
        recipients.update(get_users_with_roles(roles))

    if not recipients:
        frappe.log_error(title="[DN Notification]", message=f"No users found for roles {roles} to notify for {doc.name}.")
        return

    for user in recipients:
        notification_log = {
            "doctype": "Notification Log",
            "type": "Alert",
            "document_type": doc.doctype,
            "document_name": doc.name,
            "subject": subject,
            "for_user": user,
            "email_content": content
        }
        frappe.get_doc(notification_log).insert(ignore_permissions=True, ignore_mandatory=True)
        frappe.publish_realtime(event='notification', message={"type": "Alert", "subject": subject}, user=user)

    frappe.log_error(title="[DN Notification]", message=f"Notification '{subject}' sent to {len(recipients)} users.")


def get_users_with_roles(roles):
    """Get a unique set of enabled users from a list of roles."""
    users = set()
    for role in roles:
        users_in_role = frappe.get_all("Has Role", filters={"role": role, "parenttype": "User"}, fields=["parent"])
        for user_entry in users_in_role:
            user_name = user_entry.parent
            # Ensure user is not "Administrator" and is enabled
            if user_name != "Administrator" and frappe.db.get_value("User", user_name, "enabled"):
                users.add(user_name)
    return list(users)
