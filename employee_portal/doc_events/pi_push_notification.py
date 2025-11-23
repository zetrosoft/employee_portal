import frappe
from frappe import publish_realtime

def execute(doc, method):
    """
    Handles sending notifications based on workflow state changes for Purchase Invoices.
    """
    try:
        doc_before_save = doc.get_doc_before_save()
        if not doc_before_save or doc.workflow_state == doc_before_save.workflow_state:
            # If there's no previous state or the state hasn't changed, do nothing.
            return

        transition = (doc_before_save.workflow_state, doc.workflow_state)
        frappe.log_error(title="[PI Notification]", message=f"State transition for {doc.name}: {transition}")

        # 1. Draft -> Pending Purchase Manager Approval
        if transition == ("Draft", "Pending Purchase Manager Approval"):
            notify(
                doc=doc,
                roles=["Purchase Manager"],
                subject=f"Approval Required: Purchase Invoice {doc.name}",
                content=f"Purchase Invoice {doc.name} requires your approval."
            )

        # 2. Pending Purchase Manager Approval -> Pending Accounts User Review
        elif transition == ("Pending Purchase Manager Approval", "Pending Accounts User Review"):
            notify(
                doc=doc,
                roles=["Accounts User"],
                subject=f"Review Required: Purchase Invoice {doc.name}",
                content=f"Purchase Invoice {doc.name} requires your review."
            )
        
        # 3. Pending Purchase Manager Approval -> Rejected
        elif transition == ("Pending Purchase Manager Approval", "Rejected"):
            notify(
                doc=doc,
                users=[doc.owner],
                subject=f"Rejected: Your Purchase Invoice {doc.name}",
                content=f"Your Purchase Invoice {doc.name} has been rejected by the Purchase Manager."
            )

        # 4. Pending Accounts User Review -> Pending AM Approval
        elif transition == ("Pending Accounts User Review", "Pending AM Approval"):
            notify(
                doc=doc,
                roles=["Accounts Manager"],
                subject=f"Approval Required: Purchase Invoice {doc.name}",
                content=f"Purchase Invoice {doc.name} requires approval from Accounts Manager."
            )

        # 5. Pending Accounts User Review -> Rejected
        elif transition == ("Pending Accounts User Review", "Rejected"):
            notify(
                doc=doc,
                users=[doc.owner],
                subject=f"Rejected: Your Purchase Invoice {doc.name}",
                content=f"Your Purchase Invoice {doc.name} has been rejected by the Accounts User."
            )

        # 6. Pending AM Approval -> Submitted
        elif transition == ("Pending AM Approval", "Submitted"):
            notify(
                doc=doc,
                users=[doc.owner],
                subject=f"Submitted: Your Purchase Invoice {doc.name}",
                content=f"Your Purchase Invoice {doc.name} has been approved and submitted."
            )

        # 7. Pending AM Approval -> Rejected
        elif transition == ("Pending AM Approval", "Rejected"):
            notify(
                doc=doc,
                users=[doc.owner],
                subject=f"Rejected: Your Purchase Invoice {doc.name}",
                content=f"Your Purchase Invoice {doc.name} has been rejected by the Accounts Manager."
            )

    except Exception:
        frappe.log_error(
            title='Gagal Menjalankan Hook Notifikasi Purchase Invoice',
            message=frappe.get_traceback()
        )

# --- Generalized Helper Functions (Copied from dn_push_notification.py for consistency) ---

def notify(doc, roles=None, users=None, subject="", content=""):
    """
    Sends notifications to a list of roles or users.
    """
    if not roles and not users:
        frappe.log_error(title="[PI Notification]", message=f"Notification for {doc.name} aborted: No recipients specified.")
        return

    recipients = set(users or [])
    if roles:
        recipients.update(get_users_with_roles(roles))

    if not recipients:
        frappe.log_error(title="[PI Notification]", message=f"No users found for roles {roles} to notify for {doc.name}.")
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

    frappe.log_error(title="[PI Notification]", message=f"Notification '{subject}' sent to {len(recipients)} users.")


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
