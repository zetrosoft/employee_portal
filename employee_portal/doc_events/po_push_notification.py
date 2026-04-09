import frappe
from frappe import publish_realtime


def execute(doc, method):
	"""
	Sends push notifications based on Purchase Order workflow state changes.
	"""
	frappe.log_error(
		title="[PO Notification Debug]", message=f"--- Script execute dipanggil untuk {doc.name} ---"
	)

	try:
		doc_before_save = doc.get_doc_before_save()

		if not doc_before_save:
			return

		if doc.workflow_state == doc_before_save.workflow_state:
			return

		# --- KONDISI 1: Dokumen membutuhkan persetujuan ---
		pending_states = ["Pending PM Approval", "Pending AM Approval", "Pending Director Approval"]
		if doc.workflow_state in pending_states:
			# Find the role that is allowed to approve from the current state
			approver_role = frappe.get_value(
				"Workflow Transition",
				{
					"parent": "Purchase Order Approval",
					"state": doc.workflow_state,
					"action": "Approve",
				},
				"allowed",
			)

			if not approver_role:
				return

			# Get users with the approver role
			approvers_tuple = frappe.db.sql(
				"""
                SELECT T1.parent FROM `tabHas Role` AS T1
                JOIN `tabUser` AS T2 ON T1.parent = T2.name
                WHERE T1.role = %s AND T2.enabled = 1
            """,
				(approver_role,),
			)
			approvers = [row[0] for row in approvers_tuple]

			if approvers:
				notification_title = f"Persetujuan PO Dibutuhkan: {doc.name}"
				notification_content = f"Purchase Order {doc.name} menunggu persetujuan Anda."

				for user_id in approvers:
					n_log = frappe.new_doc("Notification Log")
					n_log.type = "Alert"
					n_log.document_type = doc.doctype
					n_log.document_name = doc.name
					n_log.subject = notification_title
					n_log.for_user = user_id
					n_log.email_content = notification_content
					n_log.insert(ignore_permissions=True, ignore_mandatory=True)
					publish_realtime("notification", user=user_id)

				frappe.log_error(
					title="[PO Notification Debug]",
					message=f"Notifikasi persetujuan untuk {doc.name} dikirim ke role {approver_role}.",
				)
			else:
				pass  # No users found for role, no log needed as per request

		# --- KONDISI 2: Dokumen ditolak ---
		elif doc.workflow_state == "Rejected":
			user_to_notify = doc.owner
			if user_to_notify:
				notification_title = f"Purchase Order Ditolak: {doc.name}"
				notification_content = (
					f"Purchase Order {doc.name} telah Ditolak. Status dokumen sekarang Dibatalkan."
				)

				n_log = frappe.new_doc("Notification Log")
				n_log.type = "Alert"
				n_log.document_type = doc.doctype
				n_log.document_name = doc.name
				n_log.subject = notification_title
				n_log.for_user = user_to_notify
				n_log.email_content = notification_content
				n_log.insert(ignore_permissions=True, ignore_mandatory=True)
				publish_realtime("notification", user=user_to_notify)

				# Set docstatus to 2 (Cancelled) only after notification is sent
				if doc.docstatus == 0:
					frappe.db.set_value(doc.doctype, doc.name, "docstatus", 2, update_modified=False)

				frappe.log_error(
					title="[PO Notification Debug]",
					message=f"Notifikasi penolakan untuk {doc.name} dikirim ke {user_to_notify} dan docstatus di set ke 2.",
				)

		# --- KONDISI 3: Dokumen telah disetujui (Submitted) ---
		elif doc.workflow_state == "Submitted":
			user_to_notify = doc.owner
			if user_to_notify:
				notification_title = f"PO {doc.name} telah disubmit"
				notification_content = f"Purchase Order {doc.name} Anda telah disetujui dan disubmit."

				n_log = frappe.new_doc("Notification Log")
				n_log.type = "Alert"
				n_log.document_type = doc.doctype
				n_log.document_name = doc.name
				n_log.subject = notification_title
				n_log.for_user = user_to_notify
				n_log.email_content = notification_content
				n_log.insert(ignore_permissions=True, ignore_mandatory=True)
				publish_realtime("notification", user=user_to_notify)
				frappe.log_error(
					title="[PO Notification Debug]",
					message=f"Notifikasi 'Submitted' untuk {doc.name} dikirim ke {user_to_notify}.",
				)

	except Exception:
		frappe.log_error(
			title="Gagal Menjalankan Hook Notifikasi Purchase Order", message=frappe.get_traceback()
		)
