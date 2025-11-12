import frappe
from frappe import publish_realtime

def execute(doc, method):
    frappe.log_error(title="[SI Notification Debug]", message=f"--- Script si_push_notification dipanggil untuk {doc.name} ---")
    
    try:
        doc_before_save = doc.get_doc_before_save()
        if not doc_before_save or doc.workflow_state == doc_before_save.workflow_state:
            return

        # --- KONDISI 1: Menunggu Persetujuan Accounts Manager ---
        if doc.workflow_state == 'Pending AM Approval':
            frappe.log_error(title="[SI Notification Debug]", message="Masuk kondisi: 'Pending AM Approval'")
            approver_role = "Accounts Manager"
            approvers_tuple = frappe.db.sql("SELECT T1.parent FROM `tabHas Role` AS T1 JOIN `tabUser` AS T2 ON T1.parent = T2.name WHERE T1.role = %s AND T2.enabled = 1", (approver_role,))
            approvers = [row[0] for row in approvers_tuple]
            
            if approvers:
                title = f"Persetujuan Sales Invoice Dibutuhkan: {doc.name}"
                content = f"Sales Invoice {doc.name} menunggu persetujuan Anda."
                for user_id in approvers:
                    frappe.get_doc({
                        "doctype": "Notification Log", "type": "Alert", "document_type": doc.doctype,
                        "document_name": doc.name, "subject": title, "for_user": user_id, "email_content": content
                    }).insert(ignore_permissions=True)
                    publish_realtime('notification', user=user_id)
                frappe.log_error(title="[SI Notification Debug]", message=f"Notifikasi dikirim ke role {approver_role}.")

        # --- KONDISI 2: Menunggu Persetujuan Direktur ---
        elif doc.workflow_state == 'Pending Director Approval':
            frappe.log_error(title="[SI Notification Debug]", message="Masuk kondisi: 'Pending Director Approval'")
            approver_role = "Director"
            approvers_tuple = frappe.db.sql("SELECT T1.parent FROM `tabHas Role` AS T1 JOIN `tabUser` AS T2 ON T1.parent = T2.name WHERE T1.role = %s AND T2.enabled = 1", (approver_role,))
            approvers = [row[0] for row in approvers_tuple]

            if approvers:
                title = f"Persetujuan Sales Invoice Dibutuhkan: {doc.name}"
                content = f"Sales Invoice {doc.name} menunggu persetujuan Anda."
                for user_id in approvers:
                    frappe.get_doc({
                        "doctype": "Notification Log", "type": "Alert", "document_type": doc.doctype,
                        "document_name": doc.name, "subject": title, "for_user": user_id, "email_content": content
                    }).insert(ignore_permissions=True)
                    publish_realtime('notification', user=user_id)
                frappe.log_error(title="[SI Notification Debug]", message=f"Notifikasi dikirim ke role {approver_role}.")

        # --- KONDISI 3: Dokumen Ditolak (REVISI) ---
        elif doc.workflow_state == 'Rejected':
            frappe.log_error(title="[SI Notification Debug]", message="Masuk kondisi: 'Rejected'")
            if doc.docstatus != 2:
                frappe.db.set_value(doc.doctype, doc.name, 'docstatus', 2, update_modified=False)

            accounts_managers = [row[0] for row in frappe.db.sql("SELECT T1.parent FROM `tabHas Role` AS T1 JOIN `tabUser` AS T2 ON T1.parent = T2.name WHERE T1.role = 'Accounts Manager' AND T2.enabled = 1")]
            
            # Penerima notifikasi hanya owner dan Accounts Manager
            recipients = list(set([doc.owner] + accounts_managers))
            
            title = f"Sales Invoice Ditolak: {doc.name}"
            content = f"Sales Invoice {doc.name} Anda telah ditolak."
            for user_id in recipients:
                frappe.get_doc({
                    "doctype": "Notification Log", "type": "Alert", "document_type": doc.doctype,
                    "document_name": doc.name, "subject": title, "for_user": user_id, "email_content": content
                }).insert(ignore_permissions=True)
                publish_realtime('notification', user=user_id)
            frappe.log_error(title="[SI Notification Debug]", message=f"Notifikasi penolakan dikirim ke {recipients}.")

        # --- KONDISI 4: Dokumen Disetujui (Submitted) ---
        elif doc.workflow_state == 'Submitted':
            frappe.log_error(title="[SI Notification Debug]", message="Masuk kondisi: 'Submitted'")
            
            accounts_managers = [row[0] for row in frappe.db.sql("SELECT T1.parent FROM `tabHas Role` AS T1 JOIN `tabUser` AS T2 ON T1.parent = T2.name WHERE T1.role = 'Accounts Manager' AND T2.enabled = 1")]
            recipients = list(set([doc.owner] + accounts_managers))
            
            title = f"Sales Invoice Disetujui: {doc.name}"
            content = f"Sales Invoice {doc.name} Anda telah disetujui dan disubmit."
            for user_id in recipients:
                frappe.get_doc({
                    "doctype": "Notification Log", "type": "Alert", "document_type": doc.doctype,
                    "document_name": doc.name, "subject": title, "for_user": user_id, "email_content": content
                }).insert(ignore_permissions=True)
                publish_realtime('notification', user=user_id)
            frappe.log_error(title="[SI Notification Debug]", message=f"Notifikasi 'Submitted' dikirim ke {recipients}.")

    except Exception:
        frappe.log_error(
            title='Gagal Menjalankan Hook Notifikasi Sales Invoice',
            message=frappe.get_traceback()
        )
