import frappe
from frappe import publish_realtime

def execute(doc, method):
    frappe.log_error(title="[SO Notification Debug]", message=f"--- Script so_push_notification dipanggil untuk {doc.name} ---")
    
    try:
        doc_before_save = doc.get_doc_before_save()
        if not doc_before_save or doc.workflow_state == doc_before_save.workflow_state:
            return

        # --- KONDISI 1: Menunggu Persetujuan Sales Manager ---
        if doc.workflow_state == 'Pending SAM Approval':
            frappe.log_error(title="[SO Notification Debug]", message="Masuk kondisi: 'Pending SAM Approval'")
            approver_role = "Sales Manager"
            approvers_tuple = frappe.db.sql("SELECT T1.parent FROM `tabHas Role` AS T1 JOIN `tabUser` AS T2 ON T1.parent = T2.name WHERE T1.role = %s AND T2.enabled = 1", (approver_role,))
            approvers = [row[0] for row in approvers_tuple]
            
            if approvers:
                title = f"Persetujuan SO Dibutuhkan: {doc.name}"
                content = f"Sales Order {doc.name} menunggu persetujuan Anda."
                for user_id in approvers:
                    frappe.get_doc({
                        "doctype": "Notification Log", "type": "Alert", "document_type": doc.doctype,
                        "document_name": doc.name, "subject": title, "for_user": user_id, "email_content": content
                    }).insert(ignore_permissions=True)
                    publish_realtime('notification', user=user_id)
                frappe.log_error(title="[SO Notification Debug]", message=f"Notifikasi dikirim ke role {approver_role}.")

        # --- KONDISI 2: Menunggu Persetujuan Direktur ---
        elif doc.workflow_state == 'Pending Director Approval':
            frappe.log_error(title="[SO Notification Debug]", message="Masuk kondisi: 'Pending Director Approval'")
            approver_role = "Director"
            approvers_tuple = frappe.db.sql("SELECT T1.parent FROM `tabHas Role` AS T1 JOIN `tabUser` AS T2 ON T1.parent = T2.name WHERE T1.role = %s AND T2.enabled = 1", (approver_role,))
            approvers = [row[0] for row in approvers_tuple]

            if approvers:
                title = f"Persetujuan SO Dibutuhkan: {doc.name}"
                content = f"Sales Order {doc.name} menunggu persetujuan Anda."
                for user_id in approvers:
                    frappe.get_doc({
                        "doctype": "Notification Log", "type": "Alert", "document_type": doc.doctype,
                        "document_name": doc.name, "subject": title, "for_user": user_id, "email_content": content
                    }).insert(ignore_permissions=True)
                    publish_realtime('notification', user=user_id)
                frappe.log_error(title="[SO Notification Debug]", message=f"Notifikasi dikirim ke role {approver_role}.")

        # --- KONDISI 3: Dokumen Ditolak ---
        elif doc.workflow_state == 'Rejected':
            frappe.log_error(title="[SO Notification Debug]", message="Masuk kondisi: 'Rejected'")
            if doc.docstatus != 2:
                frappe.db.set_value(doc.doctype, doc.name, 'docstatus', 2, update_modified=False)

            sales_managers = [row[0] for row in frappe.db.sql("SELECT T1.parent FROM `tabHas Role` AS T1 JOIN `tabUser` AS T2 ON T1.parent = T2.name WHERE T1.role = 'Sales Manager' AND T2.enabled = 1")]
            recipients = list(set([doc.owner] + sales_managers))
            
            title = f"Sales Order Ditolak: {doc.name}"
            content = f"Sales Order {doc.name} Anda telah ditolak."
            for user_id in recipients:
                frappe.get_doc({
                    "doctype": "Notification Log", "type": "Alert", "document_type": doc.doctype,
                    "document_name": doc.name, "subject": title, "for_user": user_id, "email_content": content
                }).insert(ignore_permissions=True)
                    publish_realtime('notification', user=user_id)
                frappe.log_error(title="[SO Notification Debug]", message=f"Notifikasi penolakan dikirim ke {recipients}.")

        # --- KONDISI 4: Dokumen Disetujui (Submitted) ---
        elif doc.workflow_state == 'Submitted':
            frappe.log_error(title="[SO Notification Debug]", message="Masuk kondisi: 'Submitted'")
            
            sales_managers = [row[0] for row in frappe.db.sql("SELECT T1.parent FROM `tabHas Role` AS T1 JOIN `tabUser` AS T2 ON T1.parent = T2.name WHERE T1.role = 'Sales Manager' AND T2.enabled = 1")]
            recipients = list(set([doc.owner] + sales_managers))

            title = f"Sales Order Disetujui: {doc.name}"
            content = f"Sales Order {doc.name} Anda telah disetujui dan disubmit."
            for user_id in recipients:
                frappe.get_doc({
                    "doctype": "Notification Log", "type": "Alert", "document_type": doc.doctype,
                    "document_name": doc.name, "subject": title, "for_user": user_id, "email_content": content
                }).insert(ignore_permissions=True)
                publish_realtime('notification', user=user_id)
            frappe.log_error(title="[SO Notification Debug]", message=f"Notifikasi 'Submitted' dikirim ke {recipients}.")

    except Exception:
        frappe.log_error(
            title='Gagal Menjalankan Hook Notifikasi Sales Order',
            message=frappe.get_traceback()
        )
