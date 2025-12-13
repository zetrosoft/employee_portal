import frappe
from frappe import publish_realtime
from frappe.utils import get_url_to_form


def send_notification_on_state_change(doc, method=None):
	"""Entry point for doc_events hook called from hooks.py."""
	doc_before_save = doc.get_doc_before_save()
	if not doc_before_save:
		return

	if doc.workflow_state == doc_before_save.workflow_state:
		return

	send_workflow_notification(doc)


def send_workflow_notification(doc):
	"""Creates and sends notifications based on the new workflow state."""
	new_state = doc.workflow_state
	owner_name = frappe.get_value("User", doc.owner, "full_name") or doc.owner

	subject = ""
	content = ""
	recipients = []
	role_to_notify = None

	if new_state == "Pending Manager Approval":
		role_to_notify = "Manager"
		subject = f"Expense Claim {doc.name} from {owner_name} needs your approval"
		content = f"Please review and approve the Expense Claim {doc.name}."

	elif new_state == "Pending Finance Review":
		role_to_notify = "Accounts User"
		subject = f"Expense Claim {doc.name} has been approved by Manager"
		content = f"Please review the Expense Claim {doc.name} for financial checking."

	elif new_state == "Pending AM Approval":
		role_to_notify = "Accounts Manager"
		subject = f"Expense Claim {doc.name} is ready for your approval"
		content = f"Please review and approve the Expense Claim {doc.name}."

	elif new_state == "Pending Director Approval":
		role_to_notify = "Director"
		subject = f"Expense Claim {doc.name} from {owner_name} needs your approval"
		content = f"Expense Claim {doc.name} with amount {doc.get_formatted('total_claimed_amount')} requires your approval."

	elif new_state == "Approved":
		last_approver_role = get_last_approver_role(doc)
		subject = f"Your Expense Claim {doc.name} has been approved"
		content = f"Your Expense Claim {doc.name} has been fully approved."
		recipients = [doc.owner]
		if last_approver_role == "Director":
			recipients.extend(get_all_workflow_users(doc.owner))

	elif new_state == "Rejected":
		last_approver_role = get_last_approver_role(doc)
		rejected_by = frappe.get_value("User", frappe.session.user, "full_name") or frappe.session.user
		subject = f"Your Expense Claim {doc.name} has been rejected"
		content = f"Your Expense Claim {doc.name} was rejected by {rejected_by}."

		if last_approver_role == "Director":
			recipients = get_all_workflow_users(doc.owner)
		else:
			recipients = get_rejection_recipients(doc, last_approver_role)

	if role_to_notify:
		recipients = get_users_with_role(role_to_notify)

	if recipients:
		final_recipients = list(set(recipients))

		for user in final_recipients:
			create_notification_log(doc, subject, content, user)

		frappe.log_error(
			title="[Expense Claim Notification]",
			message=f"Notification '{subject}' sent to {final_recipients}",
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
		frappe.log_error(
			f"Failed to create notification for {user} on {doc.name}: {e}",
			"Expense Claim Error",
		)


def get_users_with_role(role_name):
	"""Returns a list of enabled users with a given role."""
	return frappe.get_users_with_role(role_name)


def get_last_approver_role(doc):
	"""Tries to determine the role of the user who triggered the last state change."""
	last_version = frappe.get_all(
		"Version",
		filters={"doctype": doc.doctype, "docname": doc.name},
		fields=["owner"],
		order_by="creation desc",
		limit=1,
	)

	if last_version:
		last_modifier = last_version[0].owner
		roles = frappe.get_roles(last_modifier)
		workflow_roles = [
			"Director",
			"Accounts Manager",
			"Manager",
			"Accounts User",
			"Employee User",
		]
		for role in workflow_roles:
			if role in roles:
				return role
		if roles:
			return roles[0]
	return "System"


def get_all_workflow_users(owner=None):
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

	recipients.update(get_users_with_role("Manager"))

	if rejecter_role == "Accounts Manager":
		recipients.update(get_users_with_role("Accounts User"))

	return list(recipients)
