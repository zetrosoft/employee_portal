import frappe


def create_notification_for_workflow_state(doctype, state, subject, message, recipients, condition=None):
	"""
	Membuat atau memperbarui notifikasi otomatis untuk perubahan status workflow.
	Nama notifikasi dibuat unik berdasarkan Doctype dan State.
	"""
	# Menggunakan PO- sebagai prefix untuk Purchase Order agar lebih singkat dan unik
	notification_name = f"PO-{state.replace(' ', '-')}-Notif"

	# Hapus notifikasi yang sudah ada dengan nama yang sama untuk menghindari konflik
	if frappe.db.exists("Notification", notification_name):
		try:
			frappe.delete_doc("Notification", notification_name, ignore_permissions=True)
			frappe.db.commit()
			print(f"Existing Notification '{notification_name}' deleted.")
		except Exception as e:
			# Log error jika gagal menghapus, tapi tetap lanjutkan proses
			frappe.log_error(
				f"Failed to delete existing notification {notification_name}: {e}",
				"Delete Workflow Notification Error",
			)

	# Sekarang buat notifikasi baru dengan konfigurasi yang benar
	try:
		notification = frappe.get_doc(
			{
				"doctype": "Notification",
				"name": notification_name,
				"document_type": doctype,
				"subject": subject,
				"message": message,
				"channel": "In App Alert",
				"event": "Value Change",
				# FIX PENTING: Menggunakan value_field dan value untuk Value Change
				"value_field": "workflow_state",
				"value": state,
				"set_property_after_alert": "",
				"recipients": [],
			}
		)

		for recipient_role in recipients:
			# FIX: Menggunakan 'receiver_by_role' untuk menentukan penerima berdasarkan Role
			notification.append("recipients", {"receiver_by_role": recipient_role})

		# Menambahkan kondisi jika ada
		if condition:
			notification.conditions = condition

		notification.insert(ignore_permissions=True)
		frappe.db.commit()
		print(f"Notification '{notification_name}' created successfully.")

	except Exception as e:
		frappe.log_error(
			f"Error creating notification {notification_name}: {e}", "Create Workflow Notification"
		)
		print(f"FAILED to create notification '{notification_name}'. Check ERPNext Error Log.")


@frappe.whitelist()
def setup_po_notifications():
	doctype = "Purchase Order"

	# Notifikasi menunggu persetujuan
	# ----------------------------------------------------------------------

	# 1. PO masuk ke status Pending PM
	create_notification_for_workflow_state(
		doctype=doctype,
		state="Pending PM",
		subject="""Purchase Order {{ doc.name }} menunggu persetujuan""",
		message="""Purchase Order <b>{{ doc.name }}</b> dari <b>{{ doc.owner }}</b> (total: {{ frappe.format(doc.grand_total, "Currency") }}) menunggu persetujuan Anda.""",
		recipients=["Purchase Manager"],
	)

	# 2. PO masuk ke status Pending AM
	create_notification_for_workflow_state(
		doctype=doctype,
		state="Pending AM",
		subject="""Purchase Order {{ doc.name }} menunggu persetujuan""",
		message="""Purchase Order <b>{{ doc.name }}</b> dari <b>{{ doc.owner }}</b> (total: {{ frappe.format(doc.grand_total, "Currency") }}) menunggu persetujuan Anda dari Purchase Manager.""",
		recipients=["Account Manager"],
	)

	# 3. PO masuk ke status Pending Director
	create_notification_for_workflow_state(
		doctype=doctype,
		state="Pending Director",
		subject="""Purchase Order {{ doc.name }} menunggu persetujuan""",
		message="""Purchase Order <b>{{ doc.name }}</b> dari <b>{{ doc.owner }}</b> (total: {{ frappe.format(doc.grand_total, "Currency") }}) menunggu persetujuan Anda dari Account Manager.""",
		recipients=["Director"],
	)

	# Notifikasi Penolakan dan Pengajuan Akhir
	# ----------------------------------------------------------------------

	# 4. Notifikasi penolakan (Hanya berdasar status Cancelled)
	create_notification_for_workflow_state(
		doctype=doctype,
		state="Cancelled",
		subject="""Purchase Order {{ doc.name }} DITOLAK""",
		message="""Purchase Order <b>{{ doc.name }}</b> telah DITOLAK dalam proses persetujuan. Silakan periksa detailnya.""",
		recipients=["Purchase User", "Purchase Manager", "Account Manager"],
		# Kondisi pembeda siapa yang menolak lebih baik ditangani di Custom Script/Workflow Action daripada Notification Condition
	)

	# 5. PO masuk ke status Submitted (Nilai Kecil <= 10 Juta)
	# FIX: Menggunakan state unik 'Submitted-Small'
	create_notification_for_workflow_state(
		doctype=doctype,
		state="Submitted-Small",
		subject="""Purchase Order {{ doc.name }} di-SUBMIT (Nilai Kecil)""",
		message="""Purchase Order <b>{{ doc.name }}</b> telah di-SUBMIT (nilai kecil). Anda dapat melanjutkan proses penerimaan barang.""",
		recipients=["Purchase User", "Purchase Manager", "Account Manager"],
		# Hanya picu notif jika state dokumen adalah Submitted DAN grand_total <= 10 Juta
		condition='doc.workflow_state == "Submitted" and doc.grand_total <= 10000000',
	)

	# 6. PO masuk ke status Submitted (Nilai Besar > 10 Juta)
	# FIX: Menggunakan state unik 'Submitted-Large'
	create_notification_for_workflow_state(
		doctype=doctype,
		state="Submitted-Large",
		subject="""Purchase Order {{ doc.name }} di-SUBMIT (Nilai Besar)""",
		message="""Purchase Order <b>{{ doc.name }}</b> telah di-SUBMIT oleh Director (nilai besar). Anda dapat melanjutkan proses penerimaan barang.""",
		recipients=["Purchase User", "Purchase Manager", "Account Manager"],
		# Hanya picu notif jika state dokumen adalah Submitted DAN grand_total > 10 Juta
		condition='doc.workflow_state == "Submitted" and doc.grand_total > 10000000',
	)

	print("Purchase Order notifications setup completed.")


if __name__ == "__main__":
	setup_po_notifications()
