import frappe
from frappe import _, publish_realtime


def execute_validation(doc, method):
    """
    Handles QC validation for Delivery Notes.
    This is intended to be called from a 'before_submit' hook.
    """
    # Check for items that require QC before delivery
    items_to_check = [
        item for item in doc.items
        if frappe.db.get_value("Item", item.item_code, "inspection_required_before_delivery")
    ]

    if not items_to_check:
        # Clear summary field if no items require QC
        frappe.db.set_value("Delivery Note", doc.name, "custom_qc_validation_summary", "", update_modified=False)
        return

    validation_results = []
    has_errors = False

    for item in items_to_check:
        result = {
            "item_code": item.item_code,
            "item_name": item.item_name,
            "qi_status": "",
            "keterangan": ""
        }

        # Check for a submitted QI for this Delivery Note and Item
        qi = frappe.db.get_value("Quality Inspection", {
            "reference_type": "Delivery Note",
            "reference_name": doc.name,
            "item_code": item.item_code,
            "docstatus": 1
        }, ["name", "status"], as_dict=True)

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
                    parameter_name = frappe.get_cached_value('Quality Inspection Parameter', reading.specification, 'parameter')
                    reason_detail = f"Parameter: '{parameter_name}' ditolak."
                    rejected_reasons_list.append(reason_detail)

            if rejected_reasons_list:
                result["keterangan"] = "Item ditolak karena: " + "; ".join(rejected_reasons_list)
            else:
                result["keterangan"] = "Item ditolak (tidak ada detail alasan)."
            has_errors = True
        else: # Accepted
            result["qi_status"] = f"<b style='color:green;'>{qi.status}</b>"
            result["keterangan"] = f"Inspeksi Kualitas (QI: {qi.name}) diterima."

        validation_results.append(result)

    html_summary = build_html_summary(validation_results)

    # Save the summary to the hidden field on the Delivery Note
    frappe.db.set_value("Delivery Note", doc.name, "custom_qc_validation_summary", html_summary, update_modified=False)

    if has_errors:
        # Notify relevant roles about the failure
        notify_on_failure(doc)

        # Throw the exception to block submission
        frappe.throw(html_summary, title=_("Validasi Inspeksi Gagal"))
    else:
        # Clear the summary field if validation passes
        frappe.db.set_value("Delivery Note", doc.name, "custom_qc_validation_summary", "", update_modified=False)


def update_delivery_note_on_qi_submit(doc, method):
    """
    Triggered on_submit of a Quality Inspection.
    Updates the workflow state of the parent Delivery Note.
    """
    # Pastikan ini adalah QI untuk Delivery Note
    if not (doc.reference_type == "Delivery Note" and doc.reference_name):
        return

    try:
        dn_doc = frappe.get_doc("Delivery Note", doc.reference_name)

        # Hanya jalankan jika DN dalam status menunggu inspeksi
        if dn_doc.workflow_state != "Pending QC Inspection":
            return

        new_state = ""
        if doc.status == "Approved":
            new_state = "Approved QC"
            # Kosongkan alasan penolakan jika ada
            dn_doc.custom_rejection_reason = None
        elif doc.status == "Rejected":
            new_state = "Rejected QC"
            # Kumpulkan alasan penolakan dari tabel readings
            reasons = [
                reading.get("specification")
                for reading in doc.get("readings")
                if reading.get("status") == "Rejected"
            ]
            reason_text = "QI ditolak karena parameter berikut: " + ", ".join(reasons) if reasons else "QI ditolak tanpa detail spesifik."
            dn_doc.custom_rejection_reason = reason_text

        if new_state:
            dn_doc.workflow_state = new_state
            dn_doc.save(ignore_permissions=True)
            frappe.db.commit()
            frappe.log_error(
                title="State Changed via QI",
                message=f"Status Delivery Note {dn_doc.name} diubah menjadi {new_state} oleh QI {doc.name}."
            )

            # --- Begin: Add Notification Logic ---
            # Notify relevant users about the QC result
            notify_logistics_on_qc_completion(dn_doc, new_state)
            # --- End: Add Notification Logic ---

    except frappe.DoesNotExistError:
        frappe.log_error(
            title="Hook QI Gagal",
            message=f"Dokumen Delivery Note {doc.reference_name} tidak ditemukan."
        )
    except Exception as e:
        frappe.log_error(
            title="Hook QI Gagal",
            message=f"Terjadi error saat mengubah status DO dari QI {doc.name}: {e}"
        )


def build_html_summary(results):
    """Builds an HTML table from the validation results."""
    html_summary = """
        <p>Proses submit Delivery Note tidak bisa dilanjutkan karena ada masalah pada Inspeksi Kualitas (QC). Mohon periksa detail di bawah:</p>
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
                <td>{res['item_code']}</td>
                <td>{res['item_name']}</td>
                <td>{res['qi_status']}</td>
                <td>{res['keterangan']}</td>
            </tr>
        """
    html_summary += "</tbody></table>"
    return html_summary


def notify_logistics_on_qc_completion(dn_doc, qc_status):
    """Sends a notification to logistics users when QC is completed."""
    recipients = set([dn_doc.owner])
    logistics_managers = get_users_with_roles(['Logistics Manager'])
    recipients.update(logistics_managers)

    if qc_status == "Approved QC":
        subject = f"QC Approved for Delivery Note {dn_doc.name}"
        content = f"Quality Inspection for Delivery Note {dn_doc.name} has been approved. The document is now ready for your final submission."
    elif qc_status == "Rejected QC":
        subject = f"ACTION REQUIRED: QC Rejected for Delivery Note {dn_doc.name}"
        content = f"Quality Inspection for Delivery Note {dn_doc.name} has been rejected. Please review the document and take necessary action (Revise or Cancel)."
    else:
        return # Do not notify for other statuses

    send_notification(list(recipients), subject, content, dn_doc.doctype, dn_doc.name)


def notify_on_failure(doc):
    """Sends notification to logistic roles on validation failure."""
    roles_to_notify = ['Logistic User', 'Logistic Manager']
    users_to_notify = get_users_with_roles(roles_to_notify)
    if users_to_notify:
        subject = f"Submit Gagal untuk Pengiriman (DN) {doc.name}: Butuh Tindakan"
        content = f"Validasi Inspeksi Kualitas untuk Delivery Note {doc.name} gagal. Mohon buka dokumen untuk melihat detail item yang bermasalah."
        send_notification(users_to_notify, subject, content, doc.doctype, doc.name)

# --- Helper functions ---
def get_users_with_roles(roles):
    users = set()
    for role in roles:
        users_in_role = frappe.get_all("Has Role", filters={"role": role, "parenttype": "User"}, fields=["parent"])
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
            "email_content": content
        }
        frappe.get_doc(notification_log).insert(ignore_permissions=True)
        publish_realtime('notification', user=user)
