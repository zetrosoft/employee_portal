import frappe
from frappe import publish_realtime
from frappe.core.page.permission_manager.permission_manager import get_users_with_role


# Bungkus seluruh logika ke dalam fungsi 'execute'
def execute(doc, method):
	frappe.log_error(
		title="[WO Notification Debug]", message=f"--- Script execute dipanggil untuk {doc.name} ---"
	)

	try:
		# Metode modern dan aman untuk mendapatkan state dokumen sebelum disimpan.
		doc_before_save = doc.get_doc_before_save()

		# Keluar jika ini adalah dokumen baru atau jika state workflow tidak berubah.
		if not doc_before_save:
			frappe.log_error(
				title="[WO Notification Debug]",
				message="Keluar: Tidak ada doc_before_save (kemungkinan dokumen baru).",
			)
			return

		frappe.log_error(
			title="[WO Notification Debug]",
			message=f"Status Sebelumnya: {doc_before_save.workflow_state}, Status Sekarang: {doc.workflow_state}",
		)

		if doc.workflow_state == doc_before_save.workflow_state:
			frappe.log_error(title="[WO Notification Debug]", message="Keluar: workflow_state tidak berubah.")
			return

		# --- KONDISI 1: Dokumen membutuhkan persetujuan ---
		if doc.workflow_state == "Pending PM Approval":
			frappe.log_error(title="[WO Notification Debug]", message="Masuk kondisi: 'Pending PM Approval'")

			# Find the role that is allowed to approve from the current state
			approver_role = frappe.get_value(
				"Workflow Transition",
				{
					"parent": "Work Order Approval Workflow",
					"state": doc.workflow_state,  # Use the current state
					"action": "Approve and Submit",  # Find the next logical action
				},
				"allowed",
			)

			if not approver_role:
				frappe.log_error(
					f"Workflow hook: Approver role not found for Work Order {doc.name} from state {doc_before_save.workflow_state}."
				)
				return

			# Get users with the approver role directly from the database to bypass permission issues
			# and join with User table to ensure we only get actual users, not Role Profiles.
			approvers_tuple = frappe.db.sql(
				"""
                SELECT
                    T1.parent
                FROM
                    `tabHas Role` AS T1
                JOIN
                    `tabUser` AS T2 ON T1.parent = T2.name
                WHERE
                    T1.role = %s AND T2.enabled = 1
            """,
				(approver_role,),
			)
			approvers = [row[0] for row in approvers_tuple]

			frappe.log_error(
				title="[WO Notification Debug]", message=f"Nilai dari approver_role: {approver_role}"
			)
			frappe.log_error(title="[WO Notification Debug]", message=f"Nilai dari approvers: {approvers}")

			if approvers:
				notification_title = f"Persetujuan WO Dibutuhkan: {doc.name}"
				notification_content = f"Work Order {doc.name} menunggu persetujuan Anda."

				for user_id in approvers:
					notification_log = {
						"doctype": "Notification Log",
						"type": "Alert",
						"document_type": doc.doctype,
						"document_name": doc.name,
						"subject": notification_title,
						"for_user": user_id,
						"email_content": notification_content,
					}
					frappe.get_doc(notification_log).insert(ignore_permissions=True)
					publish_realtime("notification", user=user_id)

				frappe.log_error(
					title="[WO Notification Debug]",
					message=f"Notifikasi persetujuan untuk {doc.name} dikirim ke role {approver_role}.",
				)
			else:
				frappe.log_error(
					title="[WO Notification Debug]",
					message=f"Tidak ada user yang ditemukan untuk role: {approver_role}",
				)

		# --- KONDISI 2: Dokumen ditolak ---
		elif doc.workflow_state == "Rejected":
			frappe.log_error(title="[WO Notification Debug]", message="Masuk kondisi: 'Rejected'")

			if doc.docstatus == 0:
				frappe.db.set_value(doc.doctype, doc.name, "docstatus", 2, update_modified=False)

			user_to_notify = doc.owner
			if user_to_notify:
				notification_title = f"Work Order Ditolak: {doc.name}"
				notification_content = (
					f"Work Order {doc.name} telah Ditolak. Status dokumen sekarang Dibatalkan."
				)

				notification_log = {
					"doctype": "Notification Log",
					"type": "Alert",
					"document_type": doc.doctype,
					"document_name": doc.name,
					"subject": notification_title,
					"for_user": user_to_notify,
					"email_content": notification_content,
				}
				frappe.get_doc(notification_log).insert(ignore_permissions=True)
				publish_realtime("notification", user=user_to_notify)
				frappe.log_error(
					title="[WO Notification Debug]",
					message=f"Notifikasi penolakan untuk {doc.name} dikirim ke {user_to_notify} dan docstatus di set ke 2.",
				)

		# --- KONDISI 3: Dokumen telah disetujui (Submitted) ---
		elif doc.workflow_state == "Submitted":
			frappe.log_error(title="[WO Notification Debug]", message="Masuk kondisi: 'Submitted'")

			user_to_notify = doc.owner
			if user_to_notify:
				notification_title = f"WO {doc.name} telah disubmit"
				notification_content = f"Work Order {doc.name} Anda telah disetujui dan disubmit."

				notification_log = {
					"doctype": "Notification Log",
					"type": "Alert",
					"document_type": doc.doctype,
					"document_name": doc.name,
					"subject": notification_title,
					"for_user": user_to_notify,
					"email_content": notification_content,
				}
				frappe.get_doc(notification_log).insert(ignore_permissions=True)
				publish_realtime("notification", user=user_to_notify)
				frappe.log_error(
					title="[WO Notification Debug]",
					message=f"Notifikasi 'Submitted' untuk {doc.name} dikirim ke {user_to_notify}.",
				)

	except Exception:
		frappe.log_error(title="Gagal Menjalankan Hook Notifikasi Work Order", message=frappe.get_traceback())
