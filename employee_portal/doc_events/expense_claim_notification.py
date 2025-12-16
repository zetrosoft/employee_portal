import logging

import frappe
from frappe import publish_realtime
from frappe.utils import get_url_to_form

logger = logging.getLogger(__name__)

def send_notification_on_state_change(doc, method=None):
    """Entry point for doc_events hook called from hooks.py."""
    doc_before_save = doc.get_doc_before_save()

    new_state = doc.workflow_state
    old_state = doc_before_save.workflow_state if doc_before_save else None

    if new_state == old_state and doc_before_save: # Hanya jika ada doc_before_save, artinya ini update
        # State tidak berubah, tidak perlu update notifikasi atau status
        return # Keluar dari fungsi jika tidak ada perubahan state dan ini bukan dokumen baru

    # --- Logika baru untuk memperbarui approval_status ---
    if new_state == "Approved":
        if doc.approval_status != "Approved":
            doc.db_set("approval_status", "Approved", update_modified=False)
            logger.info(f"Expense Claim {doc.name}: approval_status set to Approved based on workflow_state.", extra={"expense_notification": True})
    elif new_state == "Rejected":
        if doc.approval_status != "Rejected":
            doc.db_set("approval_status", "Rejected", update_modified=False)
            logger.info(f"Expense Claim {doc.name}: approval_status set to Rejected based on workflow_state.", extra={"expense_notification": True})
    # --- Akhir logika baru ---

    # Logika notifikasi yang sudah ada
    # Case 1: Rejected by Manager (transitions back to Draft)
    if new_state == "Draft" and old_state == "Pending Manager Approval":
        handle_manager_rejection(doc)

    # Case 2: Rejected by Accounts Manager/Director (transitions to Rejected state)
    elif new_state == "Rejected":
        handle_finance_manager_rejection(doc)

    # Case 3: Approval steps
    else:
        handle_approvals(doc)

def handle_approvals(doc):
    """Handles notifications for approval steps."""
    new_state = doc.workflow_state
    owner_name = frappe.get_value("User", doc.owner, "full_name") or doc.owner

    subject = ""
    content = ""
    role_to_notify = None
    recipients = []

    logger.info(f"handle_approvals triggered for {doc.name}. New state: {new_state}", extra={"expense_notification": True})

    # 1. Employee -> Manager
    if new_state == "Pending Manager Approval":
        role_to_notify = "Manager"
        subject = f"Expense Claim {doc.name} from {owner_name} needs your approval"
        content = f"Please review and approve the Expense Claim {doc.name}."

        # Tentukan penerima spesifik (expense_approver)
        if doc.expense_approver:
            recipients = [doc.expense_approver]
            logger.info(f"Targeting specific approver: {doc.expense_approver}", extra={"expense_notification": True})
        else:
            # Fallback ke role_to_notify statis
            recipients = get_users_with_role(role_to_notify)
            logger.info(f"Falling back to role: {role_to_notify}, recipients: {recipients}", extra={"expense_notification": True})

    # 2. Manager -> Finance Reviewer
    elif new_state == "Pending Finance Review":
        role_to_notify = "Accounts User"
        subject = f"Expense Claim {doc.name} has been approved by Manager"
        content = f"Please review the Expense Claim {doc.name} for financial checking."
        recipients = get_users_with_role(role_to_notify)
        logger.info(f"Targeting role: {role_to_notify}, recipients: {recipients}", extra={"expense_notification": True})

    # 3. Finance Reviewer -> Accounts Manager
    elif new_state == "Pending AM Approval":
        role_to_notify = "Accounts Manager"
        subject = f"Expense Claim {doc.name} is ready for your approval"
        content = f"Please review and approve the Expense Claim {doc.name}."
        recipients = get_users_with_role(role_to_notify)
        logger.info(f"Targeting role: {role_to_notify}, recipients: {recipients}", extra={"expense_notification": True})

    # 4. Accounts Manager -> Director (Value >= 10jt)
    elif new_state == "Pending Director Approval":
        role_to_notify = "Director"
        subject = f"Expense Claim {doc.name} from {owner_name} needs your approval"
        content = f"Expense Claim {doc.name} with amount {doc.get_formatted('total_claimed_amount')} requires your approval."
        recipients = get_users_with_role(role_to_notify)
        logger.info(f"Targeting role: {role_to_notify}, recipients: {recipients}", extra={"expense_notification": True})

    # 5. Final Approval
    elif new_state == "Approved":
        last_approver_role = get_last_approver_role(doc)
        subject = f"Your Expense Claim {doc.name} has been approved"
        content = f"Your Expense Claim {doc.name} has been fully approved."
        recipients = [doc.owner]
        if last_approver_role == "Director":
             recipients.extend(get_all_workflow_roles(doc.owner))
        logger.info(f"Approved. Recipients: {recipients}", extra={"expense_notification": True})

    # 6. Rejection
    elif new_state == "Rejected":
        last_approver_role = get_last_approver_role(doc)
        rejected_by = frappe.get_value("User", frappe.session.user, "full_name") or frappe.session.user
        subject = f"Your Expense Claim {doc.name} has been rejected"
        content = f"Your Expense Claim {doc.name} was rejected by {rejected_by}."

        if last_approver_role == "Director":
            recipients = get_all_workflow_roles(doc.owner)
        else: # Rejected by Manager or Accounts Manager
            recipients = get_rejection_recipients(doc, last_approver_role)
        logger.info(f"Rejected. Recipients: {recipients}", extra={"expense_notification": True})

    if recipients:
        final_recipients = list(set(recipients))
        logger.info(f"Final recipients for state {new_state}: {final_recipients}", extra={"expense_notification": True})
        for user in final_recipients:
            create_notification_log(doc, subject, content, user)
        logger.info(f"Notification '{subject}' sent to {final_recipients}", extra={"expense_notification": True})
    else:
        logger.warning(f"No recipients found for state {new_state}. No notification sent.", extra={"expense_notification": True})


def handle_manager_rejection(doc):
    """Handles notification and status change for rejection by Manager."""
    rejected_by_user = frappe.get_value("User", frappe.session.user, "full_name") or frappe.session.user
    subject = f"Your Expense Claim {doc.name} has been rejected"
    content = f"Your Expense Claim {doc.name} was rejected by Manager ({rejected_by_user}). The claim has been cancelled."

    # Notify only the owner
    create_notification_log(doc, subject, content, doc.owner)

    # Set docstatus to 2 (Cancelled)
    if doc.docstatus != 2:
        frappe.db.set_value(doc.doctype, doc.name, "docstatus", 2, update_modified=False)

    logger.error(
        f"Manager rejection for {doc.name} handled. Notified {doc.owner}. Docstatus set to 2.",
        extra={"expense_notification": True}
    )


def handle_finance_manager_rejection(doc):
    """Handles notification for rejection by Accounts Manager or Director."""
    rejected_by_user = frappe.get_value("User", frappe.session.user, "full_name") or frappe.session.user
    subject = f"Your Expense Claim {doc.name} has been rejected"
    content = f"Your Expense Claim {doc.name} was rejected by {rejected_by_user}. The claim has been cancelled."

    # Determine who to notify
    recipients = get_all_workflow_roles(doc.owner) # Notify all relevant parties

    final_recipients = list(recipients)
    for user in final_recipients:
        create_notification_log(doc, subject, content, user)

    # docstatus is already set to 2 by the workflow engine
    logger.error(
        f"Finance Manager/Director rejection for {doc.name} handled. Notified {final_recipients}.",
        extra={"expense_notification": True}
    )


def create_notification_log(doc, subject, content, user):
    """Helper function to create a Notification Log entry."""
    try:
        notification_log = {
            "doctype": "Notification Log",
            "type": "Alert",
            "document_type": doc.doctype,
            "document_name": doc.name,
            "subject": subject,
            "for_user": user,
            "email_content": content,
        }
        frappe.get_doc(notification_log).insert(ignore_permissions=True)
        publish_realtime("notification", user=user)
    except Exception as e:
        logger.error(
            f"Failed to create notification for {user} on {doc.name}: {e}",
            "Expense Claim Error",
            exc_info=True,
            extra={"expense_notification": True}
        )


def get_last_approver_role(doc):
    """Tries to determine the role of the user who triggered the last state change."""
    last_version = frappe.get_all(
        "Version",
        filters={"ref_doctype": doc.doctype, "docname": doc.name}, # Menggunakan ref_doctype
        fields=["owner"],
        order_by="creation desc",
        limit=1,
    )

    if last_version:
        last_modifier = last_version[0].owner
        roles = frappe.get_roles(last_modifier)
        # Prioritize workflow roles
        workflow_roles = ["Director", "Accounts Manager", "Manager", "Accounts User", "Employee User"]
        for role in workflow_roles:
            if role in roles:
                return role
        if roles:
            return roles[0]
    return "System"


def get_users_with_role(role_name):
    """Returns a list of enabled users with a given role by directly querying the database."""
    logger.info(f"Getting users for role: {role_name}", extra={"expense_notification": True})
    users_data = frappe.db.sql(
        """
        SELECT
            t1.name
        FROM
            `tabUser` t1,
            `tabHas Role` t2
        WHERE
            t1.name = t2.parent AND
            t2.role = %s AND
            t1.enabled = 1
        """,
        (role_name,), # Parameter untuk %s
        as_dict=True # Mengembalikan hasil sebagai list of dictionaries
    )
    result = [user_dict["name"] for user_dict in users_data]
    logger.info(f"Users for role {role_name}: {result}", extra={"expense_notification": True})
    return result


def get_all_workflow_roles(owner=None):
    """Get all unique users from the roles involved in the workflow."""
    roles = ["Manager", "Accounts User", "Accounts Manager", "Director"]
    users = set()
    if owner:
        users.add(owner)
    for role in roles:
        users.update(get_users_with_role(role))
    return list(users)


def get_rejection_recipients(doc, rejecter_role):
    """Get list of users to notify on rejection based on who rejected."""
    recipients = {doc.owner}

    # Manager is always notified
    recipients.update(get_users_with_role("Manager"))

    # If AM rejects, notify Accounts User as well
    if rejecter_role == "Accounts Manager":
        recipients.update(get_users_with_role("Accounts User"))

    return list(recipients)
