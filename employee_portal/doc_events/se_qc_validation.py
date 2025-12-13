import frappe
from frappe import _, publish_realtime


def execute_validation(doc, method):
	"""
	Handles QC validation for Stock Entries of type 'Manufacture'.
	This is intended to be called from a 'before_submit' hook.
	"""
	# This validation should only apply to 'Manufacture' Stock Entries
	if doc.stock_entry_type != "Manufacture":
		return

	# Check for items that require QC (assuming Finished Goods group)
	items_to_check = [
		item
		for item in doc.items
		if item.is_finished_item
		and frappe.db.get_value("Item", item.item_code, "inspection_required_on_manufacture")
	]

	if not items_to_check:
		# Clear summary field if no items require QC
		frappe.db.set_value(
			"Stock Entry", doc.name, "custom_qc_validation_summary", "", update_modified=False
		)
		return

	validation_results = []
	has_errors = False

	for item in items_to_check:
		result = {"item_code": item.item_code, "item_name": item.item_name, "qi_status": "", "keterangan": ""}

		# Check for a submitted QI for this Stock Entry and Item
		qi = frappe.db.get_value(
			"Quality Inspection",
			{
				"reference_type": "Stock Entry",
				"reference_name": doc.name,
				"item_code": item.item_code,
				"docstatus": 1,
			},
			["name", "status"],
			as_dict=True,
		)

		if not qi:
			result["qi_status"] = "Belum Dibuat"
			result["keterangan"] = "Proses inspeksi untuk item ini belum ada atau belum di-submit."
			has_errors = True
		elif qi.status == "Rejected":
			result["qi_status"] = f"<b style='color:red;'>{qi.status}</b>"
			# Get detailed rejection reasons
			qi_doc = frappe.get_doc("Quality Inspection", qi.name)
			rejected_reasons_list = []
			for reading in qi_doc.readings:
				if reading.status == "Rejected":
					parameter_name = frappe.get_cached_value(
						"Quality Inspection Parameter", reading.specification, "parameter"
					)
					reason_detail = f"Parameter: '{parameter_name}' ditolak."
					rejected_reasons_list.append(reason_detail)

			if rejected_reasons_list:
				result["keterangan"] = "Item ditolak karena: " + "; ".join(rejected_reasons_list)
			else:
				result["keterangan"] = "Item ditolak (tidak ada detail alasan)."
			has_errors = True
		else:  # Accepted
			result["qi_status"] = f"<b style='color:green;'>{qi.status}</b>"
			result["keterangan"] = f"Inspeksi Kualitas (QI: {qi.name}) diterima."

		validation_results.append(result)

	html_summary = build_html_summary(validation_results)

	# Save the summary to the hidden field on the Stock Entry
	frappe.db.set_value(
		"Stock Entry", doc.name, "custom_qc_validation_summary", html_summary, update_modified=False
	)

	if has_errors:
		# Notify relevant roles about the failure
		notify_on_failure(doc)

		# Throw the exception to block submission
		frappe.throw(html_summary, title=_("Validasi Inspeksi Gagal"))
	else:
		# Clear the summary field if validation passes
		frappe.db.set_value(
			"Stock Entry", doc.name, "custom_qc_validation_summary", "", update_modified=False
		)


def update_stock_entry_on_qi_submit(doc, method):
	"""
	Triggered on_submit of a Quality Inspection.
	Updates the workflow state of the parent Stock Entry.
	"""
	frappe.log_error(
		title="[SE QC Debug]",
		message=f"update_stock_entry_on_qi_submit dipanggil untuk QI: {doc.name}, Status QI: {doc.status}, Ref Type: {doc.reference_type}, Ref Name: {doc.reference_name}",
	)

	# Pastikan ini adalah QI untuk Stock Entry
	if not (doc.reference_type == "Stock Entry" and doc.reference_name):
		frappe.log_error(
			title="[SE QC Debug]",
			message=f"QI {doc.name}: Bukan untuk Stock Entry atau reference_name kosong. Keluar.",
		)
		return

	try:
		se_doc = frappe.get_doc("Stock Entry", doc.reference_name)
		frappe.log_error(
			title="[SE QC Debug]",
			message=f"QI {doc.name}: SE {se_doc.name} ditemukan. Current SE state: {se_doc.workflow_state}",
		)

		# Hanya jalankan jika SE dalam status menunggu inspeksi
		if se_doc.workflow_state != "Pending QC Inspection":
			frappe.log_error(
				title="[SE QC Debug]",
				message=f"QI {doc.name}: SE {se_doc.name} tidak dalam status 'Pending QC Inspection'. Keluar.",
			)
			return

		new_state = ""
		if doc.status == "Accepted":  # <-- Diubah dari "Approved" ke "Accepted"
			new_state = "Approved QC"
			# Kosongkan alasan penolakan jika ada
			se_doc.custom_rejection_reason = None
		elif doc.status == "Rejected":
			new_state = "Rejected QC"
			# Kumpulkan alasan penolakan dari tabel readings
			reasons = [
				reading.get("specification")
				for reading in doc.get("readings")
				if reading.get("status") == "Rejected"
			]
			reason_text = (
				"QI ditolak karena parameter berikut: " + ", ".join(reasons)
				if reasons
				else "QI ditolak tanpa detail spesifik."
			)
			se_doc.custom_rejection_reason = reason_text

		frappe.log_error(title="[SE QC Debug]", message=f"QI {doc.name}: New state determined: {new_state}")
		if new_state:
			current_user = frappe.session.user  # Simpan user saat ini
			try:
				frappe.set_user("Administrator")  # Jalankan sebagai Administrator untuk sementara
				se_doc.workflow_state = new_state
				se_doc.save(ignore_permissions=True)  # Gunakan save() dengan ignore_permissions=True
				frappe.db.commit()  # Commit the state change
				frappe.log_error(
					title="State Changed via QI",
					message=f"Status Stock Entry {se_doc.name} diubah menjadi {new_state} oleh QI {doc.name} via se_doc.save(as Administrator).",
				)
			except Exception as e:
				frappe.log_error(
					title="Workflow State Change Failed",
					message=f"Gagal mengubah status Stock Entry {se_doc.name} ke {new_state} oleh QI {doc.name}: {e}",
				)
				frappe.db.rollback()  # Rollback the entire transaction, including QI submission
				frappe.throw(
					_(
						"Gagal mengubah status Stock Entry. QI tidak disubmit. Mohon periksa Error Log untuk detail."
					)
				)
			finally:
				frappe.set_user(current_user)  # Kembalikan user ke semula

	except frappe.DoesNotExistError:
		frappe.log_error(
			title="Hook QI Gagal", message=f"Dokumen Stock Entry {doc.reference_name} tidak ditemukan."
		)
		frappe.db.rollback()  # Rollback if SE not found
		frappe.throw(_("Dokumen Stock Entry tidak ditemukan. QI tidak disubmit."))
	except Exception as e:
		frappe.log_error(
			title="Hook QI Gagal",
			message=f"Terjadi error umum saat mengubah status SE dari QI {doc.name}: {e}",
		)
		frappe.db.rollback()  # Rollback if any other error
		frappe.throw(
			_(
				"Terjadi error umum saat memperbarui Stock Entry. QI tidak disubmit. Mohon periksa Error Log untuk detail."
			)
		)


def build_html_summary(results):
	"""Builds an HTML table from the validation results."""
	html_summary = """
        <p>Proses submit Stock Entry tidak bisa dilanjutkan karena ada masalah pada Inspeksi Kualitas (QC). Mohon periksa detail di bawah:</p>
        <table class='table table-bordered'>
            <thead>
                <tr>
                    <th style='width: 15%;'>Item Code</th>
                    <th style='width: 30%;'>Item Name</th>
                    <th style='width: 15%;'>QI Status</th>
                    <th>Keterangan</th>
                </tr>
            </thead>
            <tbody>
    """
	for res in results:
		html_summary += f"""
            <tr>
                <td>{res["item_code"]}</td>
                <td>{res["item_name"]}</td>
                <td>{res["qi_status"]}</td>
                <td>{res["keterangan"]}</td>
            </tr>
        """
	html_summary += "</tbody></table>"
	return html_summary


def notify_on_failure(doc):
	"""Sends notification to production roles on validation failure."""
	roles_to_notify = ["Production User", "Production Manager"]
	users_to_notify = get_users_with_roles(roles_to_notify)
	if users_to_notify:
		subject = f"Submit Gagal untuk Produksi (SE) {doc.name}: Butuh Tindakan"
		content = f"Validasi Inspeksi Kualitas untuk Stock Entry {doc.name} gagal. Mohon buka dokumen untuk melihat detail item yang bermasalah."
		send_notification(users_to_notify, subject, content, doc.doctype, doc.name)


# --- Helper functions copied from pr_qc_validation.py ---
def get_users_with_roles(roles):
	users = set()
	for role in roles:
		users_in_role = frappe.get_all(
			"Has Role", filters={"role": role, "parenttype": "User"}, fields=["parent"]
		)
		for user_entry in users_in_role:
			user_name = user_entry.parent
			if frappe.db.get_value("User", user_name, "enabled"):
				users.add(user_name)
	return list(users)


def send_notification(users, subject, content, doc_type, doc_name):
	for user in users:
		notification_log = {
			"doctype": "Notification Log",
			"type": "Alert",
			"document_type": doc_type,
			"document_name": doc_name,
			"subject": subject,
			"for_user": user,
			"email_content": content,
		}
		frappe.get_doc(notification_log).insert(ignore_permissions=True)
		publish_realtime("notification", user=user)
