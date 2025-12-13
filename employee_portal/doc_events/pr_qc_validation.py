import frappe
from frappe import _, publish_realtime


def execute_validation(doc, method):
	"""
	Handles validation and notifications for Purchase Receipts containing
	'Persediaan Bahan Baku' item group.
	"""
	# Check if the document contains the specified item group
	has_bahan_baku = False
	item_codes = [item.item_code for item in doc.items]
	if item_codes:
		has_bahan_baku = frappe.db.exists(
			"Item", {"name": ("in", item_codes), "item_group": "Persediaan Bahan Baku"}
		)

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
		"Quality User",
		"Quality Manager",
		"Purchase User",
		"Purchase Manager",
		"Stock Manager",
	]

	users_to_notify = get_users_with_roles(roles_to_notify)

	if users_to_notify:
		notification_subject = f"Quality Inspection Dibutuhkan untuk PR: {doc.name}"
		notification_content = f"Purchase Receipt {doc.name} berisi item 'Persediaan Bahan Baku' dan membutuhkan inspeksi kualitas."

		send_notification(users_to_notify, notification_subject, notification_content, doc.doctype, doc.name)
		frappe.log_error(
			title="[PR QC Notif]",
			message=f"Notifikasi QC dikirim untuk PR {doc.name} ke {len(users_to_notify)} user.",
		)
	else:
		frappe.log_error(
			title="[PR QC Notif]",
			message=f"Tidak ada user yang ditemukan untuk dinotifikasi pada PR {doc.name}.",
		)


def validate_on_submit(doc):
	"""
	Validates if a submitted Quality Inspection exists and is 'Accepted' for
	each item in the PR that requires one.
	"""
	items_to_check = [
		item
		for item in doc.items
		if frappe.db.get_value("Item", item.item_code, "item_group") == "Persediaan Bahan Baku"
	]

	if not items_to_check:
		return

	validation_results = []
	has_errors = False

	for item in items_to_check:
		result = {"item_code": item.item_code, "item_name": item.item_name, "qi_status": "", "keterangan": ""}

		qi = frappe.db.get_value(
			"Quality Inspection",
			{
				"reference_type": "Purchase Receipt",
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

			qi_doc = frappe.get_doc("Quality Inspection", qi.name)
			rejected_reasons_list = []

			for reading in qi_doc.readings:
				if reading.status == "Rejected":
					parameter_name = frappe.get_cached_value(
						"Quality Inspection Parameter", reading.specification, "parameter"
					)
					parameter_description = frappe.get_cached_value(
						"Quality Inspection Parameter", reading.specification, "description"
					)

					reason_detail = f"Parameter: '{parameter_name}'"
					if parameter_description:
						# Clean HTML tags if any, and limit description length for summary
						cleaned_description = parameter_description.replace("<p>", "").replace("</p>", "")
						if len(cleaned_description) > 50:  # Limit to 50 chars for summary
							cleaned_description = cleaned_description[:50] + "..."
						reason_detail += f" ({cleaned_description})"

					if reading.numeric:
						# Fetch the actual reading value, can be reading_1, reading_2 etc.
						# For simplicity, let's just show the first reading if available, or just the min/max expectation
						actual_reading_value = reading.reading_1 if reading.reading_1 else ""
						reason_detail += f" - Harapan: {reading.min_value}-{reading.max_value}"
						if actual_reading_value:
							reason_detail += f", Terbaca: {actual_reading_value}"

					elif reading.value:  # Non-numeric value based inspection
						reason_detail += f" - Harapan: '{reading.value}'"
						if reading.reading_value:
							reason_detail += f", Terbaca: '{reading.reading_value}'"

					rejected_reasons_list.append(reason_detail)

			if rejected_reasons_list:
				result["keterangan"] = "Item ditolak karena: " + "; ".join(rejected_reasons_list)
			else:
				result["keterangan"] = (
					"Item ditolak karena salah satu atau lebih kriteria inspeksi tidak terpenuhi (detail tidak tersedia)."
				)

			has_errors = True
		else:  # qi.status == "Accepted"
			result["qi_status"] = f"<b style='color:green;'>{qi.status}</b>"
			result["keterangan"] = f"Inspeksi Kualitas (QI: {qi.name}) diterima."

		validation_results.append(result)

	# Build the HTML table
	html_summary = """
        <p>Proses submit Purchase Receipt tidak bisa dilanjutkan karena ada masalah pada Inspeksi Kualitas (QC). Mohon periksa detail di bawah:</p>
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
	for res in validation_results:
		html_summary += f"""
            <tr>
                <td>{res["item_code"]}</td>
                <td>{res["item_name"]}</td>
                <td>{res["qi_status"]}</td>
                <td>{res["keterangan"]}</td>
            </tr>
        """
	html_summary += "</tbody></table>"

	# Save the summary to the hidden field on the Purchase Receipt
	frappe.db.set_value(
		"Purchase Receipt", doc.name, "custom_qc_validation_summary", html_summary, update_modified=False
	)

	if has_errors:
		# Notify relevant roles about the failure
		roles_to_notify = ["Purchase User", "Purchase Manager"]
		users_to_notify = get_users_with_roles(roles_to_notify)
		if users_to_notify:
			subject = f"Submit Gagal untuk PR {doc.name}: Butuh Tindakan"
			content = f"Validasi Inspeksi Kualitas untuk Purchase Receipt {doc.name} gagal. Mohon buka dokumen untuk melihat detail item yang bermasalah."
			send_notification(users_to_notify, subject, content, doc.doctype, doc.name)

		# Throw the exception to block submission
		frappe.throw(html_summary, title=_("Validasi Inspeksi Gagal"))
	else:
		# Clear the summary field if validation passes
		frappe.db.set_value(
			"Purchase Receipt", doc.name, "custom_qc_validation_summary", "", update_modified=False
		)


# --- Helper Functions ---


def get_users_with_roles(roles):
	"""Get a unique set of enabled users from a list of roles."""
	users = set()
	for role in roles:
		users_in_role = frappe.get_all(
			"Has Role", filters={"role": role, "parenttype": "User"}, fields=["parent"]
		)
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
			"email_content": content,
		}
		frappe.get_doc(notification_log).insert(ignore_permissions=True)
		publish_realtime("notification", user=user)
