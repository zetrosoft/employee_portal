import frappe


def create_employee_portal_role():
    # Create Role "Employee Portal"
    if not frappe.db.exists("Role", "Employee Portal"):
        role = frappe.get_doc({
            "doctype": "Role",
            "role_name": "Employee Portal",
            "desk_access": 1,
            "is_custom": 1
        })
        role.insert(ignore_permissions=True)
        frappe.db.commit()
        print("Role 'Employee Portal' created.")
    else:
        print("Role 'Employee Portal' already exists.")

    # Set permissions for Leave Application
    set_permissions_for_doctype("Leave Application", "Employee Portal")

    # Set permissions for Expense Claim
    set_permissions_for_doctype("Expense Claim", "Employee Portal")

    frappe.db.commit()
    print("Permissions for 'Employee Portal' role set.")

def set_permissions_for_doctype(doctype_name, role_name):
    # Clear existing permissions for the role and doctype
    frappe.db.sql(
        """DELETE FROM `tabCustom DocPerm` WHERE role = %s AND parent = %s""",
        (role_name, doctype_name)
    )
    frappe.db.sql(
        """DELETE FROM `tabDocPerm` WHERE role = %s AND parent = %s""",
        (role_name, doctype_name)
    )

    # Add new permissions
    permissions = frappe.get_doc({
        "doctype": "DocPerm",
        "role": role_name,
        "parent": doctype_name,
        "parenttype": "DocType",
        "parentfield": "permissions",
        "read": 1,
        "write": 1,
        "create": 1,
        "delete": 1,
        "submit": 1,
        "cancel": 1,
        "amend": 0, # Amend is usually not needed for basic CRUD + Submit/Cancel
        "report": 1,
        "export": 1,
        "print": 1,
        "email": 1,
        "import": 0,
        "set_user_permissions": 0
    })
    permissions.insert(ignore_permissions=True)
    print(f"Permissions for {doctype_name} set for role '{role_name}'.")

if __name__ == "__main__":
    create_employee_portal_role()
