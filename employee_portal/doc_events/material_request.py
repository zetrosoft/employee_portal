import frappe

def trigger_notifications(doc, method):
    frappe.log_error(title="[MR Notification Debug]", message=f"Hook 'on_update' triggered for MR {doc.name} with state {doc.workflow_state}")

    notification_map = {
        "Pending PM Approval": {"role": "Production Manager", "subject": f"MR {doc.name} needs your approval"},
        "Pending Stock User Review": {"role": "Stock User", "subject": f"MR {doc.name} needs your review"},
        "Pending SM Approval": {"role": "Stock Manager", "subject": f"MR {doc.name} needs your approval"},
        "Submitted": {"role": "owner", "subject": f"MR {doc.name} has been approved"},
        "Rejected": {"role": "owner", "subject": f"MR {doc.name} has been rejected"}
    }

    current_state = doc.workflow_state
    if current_state in notification_map:
        config = notification_map[current_state]
        
        notification_doc = {
            "doctype": "Notification Log",
            "channel": "System Notification",  # <-- PERBAIKAN DITAMBAHKAN DI SINI
            "document_type": "Material Request",
            "document_name": doc.name,
            "subject": config["subject"],
            "type": "Alert",
            "email_content": config.get("message", config["subject"])
        }

        try:
            if config["role"] == "owner":
                notification_doc["for_user"] = doc.owner
                frappe.get_doc(notification_doc).insert(ignore_permissions=True)
                frappe.log_error(title="[MR Notification Debug]", message=f"Attempted to create notification for owner: {doc.owner}")
            else:
                users = frappe.get_users_with_role(config["role"])
                if not users:
                    frappe.log_error(title="[MR Notification Debug]", message=f"No users found for role: {config['role']}")
                for user in users:
                    notification_doc["for_user"] = user
                    frappe.get_doc(notification_doc).insert(ignore_permissions=True)
                    frappe.log_error(title="[MR Notification Debug]", message=f"Attempted to create notification for user '{user}' in role '{config['role']}'")
        
        except Exception as e:
            frappe.log_error(title="[MR Notification Debug] - EXCEPTION", message=frappe.get_traceback())
