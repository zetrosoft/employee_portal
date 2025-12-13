import frappe
from frappe import publish_realtime
from frappe.utils import get_url_to_form
import logging

logger = logging.getLogger(__name__)

def send_notification_on_state_change(doc, method=None):
	"""Entry point for doc_events hook called from hooks.py."""
	doc_before_save = doc.get_doc_before_save()
	if not doc_before_save:
		return

	new_state = doc.workflow_state
	old_state = doc_before_save.workflow_state

	if new_state == old_state:
		return

	# Case 1: Rejected by Manager (transitions back to Draft)
	if new_state == "Draft" and old_state == "Pending Manager Approval":
		handle_manager_rejection(doc)

	# Case 2: Rejected by HR Manager (transitions to Rejected state)
	elif new_state == "Rejected":
		handle_hr_manager_rejection(doc)

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

	logger.info(f"handle_approvals triggered for {doc.name}. New state: {new_state}", extra={"leave_notification": True})

	# 1. Employee -> Manager
	if new_state == "Pending Manager Approval":
		role_to_notify = "Manager"
		subject = f"Leave Application from {owner_name} needs your approval"
		content = f"Please review the Leave Application {doc.name}."
		
		# PERBAIKAN DI SINI: Tentukan penerima spesifik (leave_approver)
		if doc.leave_approver:
			recipients = [doc.leave_approver]
			logger.info(f"Targeting specific approver: {doc.leave_approver}", extra={"leave_notification": True})
		else:
			# Jika doc.leave_approver tidak ada, fallback ke role_to_notify statis
			recipients = get_users_with_role(role_to_notify)
			logger.info(f"Falling back to role: {role_to_notify}, recipients: {recipients}", extra={"leave_notification": True})


	# 2. Manager -> HR Reviewer
	elif new_state == "Pending HR Review":
		role_to_notify = "HR User"
		subject = f"Leave Application {doc.name} has been approved by Manager"
		content = f"Please review the Leave Application {doc.name} for HR checking."
		recipients = get_users_with_role(role_to_notify) # Ini benar untuk HR User statis
		logger.info(f"Targeting role: {role_to_notify}, recipients: {recipients}", extra={"leave_notification": True})
		
	# 3. HR User -> HR Manager
	elif new_state == "Pending HR Manager Approval":
		role_to_notify = "HR Manager"
		subject = f"Leave Application {doc.name} is ready for your final approval"
		content = f"Please review and approve the Leave Application {doc.name}."
		recipients = get_users_with_role(role_to_notify) # Ini benar untuk HR Manager statis
		logger.info(f"Targeting role: {role_to_notify}, recipients: {recipients}", extra={"leave_notification": True})

	# 4. Final Approval by HR Manager
	elif new_state == "Approved":
		subject = f"Your Leave Application {doc.name} has been approved"
		content = f"Your Leave Application {doc.name} has been fully approved and submitted."
		recipients = [doc.owner] # Notifikasi ke owner
		if doc.leave_approver: # Notifikasi ke manajer awal
			recipients.append(doc.leave_approver)
		# Notifikasi ke Manajer HR (jika diperlukan untuk arsip)
		recipients.extend(get_users_with_role("HR Manager")) 
		logger.info(f"Approved. Recipients: {recipients}", extra={"leave_notification": True})

	if recipients:
		final_recipients = list(set(recipients))
		logger.info(f"Final recipients for state {new_state}: {final_recipients}", extra={"leave_notification": True})
		for user in final_recipients:
			create_notification_log(doc, subject, content, user)
		logger.info(f"Notification '{subject}' sent to {final_recipients}", extra={"leave_notification": True})
	else:
		logger.warning(f"No recipients found for state {new_state}. No notification sent.", extra={"leave_notification": True})


def handle_manager_rejection(doc):
	"""Handles notification and status change for rejection by Manager."""
	rejected_by_user = frappe.get_value("User", frappe.session.user, "full_name") or frappe.session.user
	subject = f"Your Leave Application {doc.name} has been rejected"
	content = f"Your Leave Application {doc.name} was rejected by Manager ({rejected_by_user}). The application has been cancelled."

	# Notify only the owner
	create_notification_log(doc, subject, content, doc.owner)

	# IMPORTANT: Set docstatus to 2 (Cancelled) as per requirement
	if doc.docstatus != 2:
		frappe.db.set_value(doc.doctype, doc.name, "docstatus", 2, update_modified=False)

	frappe.log_error(
		title="[Leave App Notification]",
		message=f"Manager rejection for {doc.name} handled. Notified {doc.owner}. Docstatus set to 2.",
	)


def handle_hr_manager_rejection(doc):
	"""Handles notification for rejection by HR Manager."""
	rejected_by_user = frappe.get_value("User", frappe.session.user, "full_name") or frappe.session.user
	subject = f"Leave Application {doc.name} has been rejected by HR Manager"
	content = f"The Leave Application {doc.name} from {doc.employee_name} was rejected by HR Manager ({rejected_by_user}). The application has been cancelled."

	# Notify all roles except HR Manager
	recipients = {doc.owner}
	recipients.update(get_users_with_role("Manager"))
	recipients.update(get_users_with_role("HR User"))

	final_recipients = list(recipients)
	for user in final_recipients:
		create_notification_log(doc, subject, content, user)

	# docstatus is already set to 2 by the workflow engine
	frappe.log_error(
		title="[Leave App Notification]",
		message=f"HR Manager rejection for {doc.name} handled. Notified {final_recipients}.",
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
		frappe.log_error(f"Failed to create notification for {user} on {doc.name}: {e}", "Leave App Error")


def get_users_with_role(role_name):
    """Returns a list of enabled users with a given role by directly querying the database."""
    # PERUBAHAN DI SINI: Menggunakan frappe.db.sql untuk menghindari masalah izin/parent DocType
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
    return [user_dict["name"] for user_dict in users_data]
