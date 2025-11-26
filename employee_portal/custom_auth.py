import re

import frappe
from frappe.exceptions import ValidationError
from frappe.utils import get_url

# Store original Frappe login method
_original_frappe_login = None

def custom_employee_login(usr, pwd):
    """
    Overrides the default Frappe login method to allow custom employee login.
    """
    global _original_frappe_login
    if _original_frappe_login is None:
        # Lazily get the original login method to avoid circular imports
        # This will be the Frappe's default login method
        _original_frappe_login = frappe.get_attr("frappe.auth.login")

    frappe.log_error(title="Custom Login Override", message=f"Attempting custom login for usr: {usr}")

    # Clean the input user (cell_number) for consistent lookup
    cleaned_user_cell_number = re.sub(r'[^0-9]', '', usr)

    # 1. Try to find employee by cell_number in tabEmployee where user_id is empty
    employees = frappe.get_list(
        "Employee",
        filters={
            "cell_number": cleaned_user_cell_number,  # User input is cell_number
            "user_id": ["is", "not set"] # Only for unprovisioned accounts
        },
        fields=["name", "employee_name", "cell_number", "company_email", "personal_email"]
    )

    if employees:
        employee = employees[0]
        # Clean employee's cell_number from DB for consistent processing
        cleaned_employee_cell_number = re.sub(r'[^0-9]', '', employee.cell_number)

        # 2. Validate password (last 5 digits of cleaned cell_number)
        if not cleaned_employee_cell_number or len(cleaned_employee_cell_number) < 5:
            frappe.log_error(title="Custom Login Failed", message=f"Employee {employee.name} cleaned cell_number is too short or missing.")
            # Fallback to original Frappe login
            return _original_frappe_login(usr, pwd)

        expected_pwd = cleaned_employee_cell_number[-5:]

        if pwd == expected_pwd:
            # Password is valid, now provision Frappe User (if not already)
            frappe_user_email = ""
            if employee.company_email and "@" in employee.company_email:
                frappe_user_email = employee.company_email
            elif employee.personal_email and "@" in employee.personal_email:
                frappe_user_email = employee.personal_email
            else:
                frappe_user_email = f"{cleaned_employee_cell_number}@siumang.co.id"

            frappe_user_name = frappe.db.get_value("User", {"email": frappe_user_email}, "name")

            if frappe_user_name:
                user_doc = frappe.get_doc("User", frappe_user_name)
            else:
                user_doc = frappe.new_doc("User")
                user_doc.email = frappe_user_email
                user_doc.first_name = employee.employee_name.split(' ')[0] if employee.employee_name else employee.name
                user_doc.last_name = " ".join(employee.employee_name.split(' ')[1:]) if employee.employee_name and len(employee.employee_name.split(' ')) > 1 else ""
                user_doc.user_type = "Website User" # Or "System User" if desk access is needed for all features
                user_doc.send_welcome_email = 0
                user_doc.enabled = 1
                user_doc.save(ignore_permissions=True)
                user_doc.set_password(pwd) # Set initial password

            # Assign 'Employee User' role
            if not user_doc.has_role("Employee User"):
                user_doc.add_roles("Employee User")
                frappe.log_error(title="Custom Login Info", message=f"Assigned 'Employee User' role to {user_doc.name}.")

            # Link Frappe User to Employee
            if employee.user_id != user_doc.name:
                frappe.db.set_value("Employee", employee.name, "user_id", user_doc.name, update_modified=False)
                frappe.db.commit() # Commit this change immediately
                frappe.log_error(title="Custom Login Info", message=f"Linked Frappe User {user_doc.name} to Employee {employee.name}.")

            # Manually set the Frappe session
            frappe.session.user = user_doc.name
            frappe.db.commit()
            frappe.log_error(title="Custom Login Success", message=f"Employee {employee.name} successfully logged in as Frappe User: {user_doc.name}.")
            return # Successfully handled login

        else: # Password invalid
            frappe.log_error(title="Custom Login Failed", message=f"Invalid password for employee {employee.name}.")
            # Fallback to original Frappe login for standard users or if custom logic fails
            # Frappe's login will raise ValidationError if credentials are bad
            return _original_frappe_login(usr, pwd)

    else: # Employee not found with empty user_id, or cell_number is not the login method
        frappe.log_error(title="Custom Login Fallback", message=f"No unprovisioned employee found with cell_number {cleaned_user_cell_number}. Falling back to standard Frappe login.")
        # Fallback to original Frappe login for standard users or if custom logic doesn't apply
        return _original_frappe_login(usr, pwd)
