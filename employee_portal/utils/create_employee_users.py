import re
from datetime import datetime

import frappe


def parse_employee_sql_data(sql_file_path):
    employees_data = []
    with open(sql_file_path) as f:
        for line in f:
            if line.strip().startswith('INSERT INTO `tabEmployee` VALUES'):
                # Extract values from the INSERT statement
                # This is a simplified regex and might need adjustment based on actual SQL format
                match = re.search(r'VALUES \((.*?)\);', line)
                if match:
                    values_str = match.group(1)
                    # Split by comma, but be careful with commas inside strings
                    # A more robust SQL parser might be needed for complex cases
                    values = [v.strip().strip("'`) ") for v in values_str.split("','")]

                    # Assuming the order of columns from tabEmployee.sql
                    # 'name', 'creation', 'modified', 'modified_by', 'owner', 'docstatus', 'idx', 'employee', 'naming_series', 'first_name', 'middle_name', 'last_name', 'employee_name', 'gender', 'date_of_birth', 'salutation', 'date_of_joining', 'image', 'status', 'user_id', 'create_user_permission', 'company', 'department', 'employee_number', 'designation', 'reports_to', 'branch', 'scheduled_confirmation_date', 'final_confirmation_date', 'contract_end_date', 'notice_number_of_days', 'date_of_retirement', 'cell_number', 'personal_email', 'company_email', 'prefered_contact_email', 'prefered_email', 'unsubscribed', 'current_address', 'current_accommodation_type', 'permanent_address', 'permanent_accommodation_type', 'person_to_be_contacted', 'emergency_phone_number', 'relation', 'attendance_device_id', 'holiday_list', 'ctc', 'salary_currency', 'salary_mode', 'bank_name', 'bank_ac_no', 'iban', 'marital_status', 'family_background', 'blood_group', 'health_details', 'passport_number', 'valid_upto', 'date_of_issue', 'place_of_issue', 'bio', 'resignation_letter_date', 'relieving_date', 'held_on', 'new_workplace', 'leave_encashed', 'encashment_date', 'reason_for_leaving', 'feedback', 'lft', 'rgt', 'old_parent', '_user_tags', '_comments', '_assign', '_liked_by', 'employment_type', 'grade', 'job_applicant', 'default_shift', 'expense_approver', 'leave_approver', 'shift_request_approver', 'payroll_cost_center', 'health_insurance_provider', 'health_insurance_no', 'golongan', 'jabatan', 'status_pajak', 'jumlah_tanggungan', 'override_tax_method', 'tipe_karyawan', 'penghasilan_final', 'npwp', 'upload_npwp', 'ktp', 'upload_ktp', 'npwp_suami', 'npwp_gabung_suami', 'ikut_bpjs_kesehatan', 'bpjs_kesehatan_id', 'ikut_bpjs_ketenagakerjaan', 'bpjs_ketenagakerjaan_id', 'custom_tempat_lahir', 'custom_agama', 'custom_no_kk'

                    # Adjust indices based on the actual SQL dump format
                    # This is a best guess based on common Frappe SQL dumps
                    # You might need to manually verify these indices against your actual tabEmployee.sql
                    try:
                        employee_name = values[12] if len(values) > 12 else None
                        cell_number = values[31] if len(values) > 31 else None
                        personal_email = values[32] if len(values) > 32 else None
                        date_of_birth_str = values[14] if len(values) > 14 else None
                        employee_id = values[7] if len(values) > 7 else None # 'employee' field, usually the NIK
                        user_id_in_employee_doc = values[19] if len(values) > 19 else None

                        employees_data.append({
                            "employee_id": employee_id,
                            "employee_name": employee_name,
                            "cell_number": cell_number,
                            "personal_email": personal_email,
                            "date_of_birth": date_of_birth_str,
                            "user_id_in_employee_doc": user_id_in_employee_doc
                        })
                    except IndexError as e:
                        print(f"Error parsing line: {line.strip()}. Index error: {e}")
                        print(f"Values: {values}")
    return employees_data

def format_phone_number(phone_number):
    if not phone_number:
        return None
    # Remove all non-digit characters
    formatted_number = re.sub(r'\D', '', phone_number)
    # Add country code if not present and starts with 0
    if formatted_number.startswith('0'):
        formatted_number = '62' + formatted_number[1:]
    return formatted_number

def format_date_of_birth_for_password(date_of_birth_str):
    if not date_of_birth_str or date_of_birth_str == '0000-00-00':
        return None
    try:
        # Try parsing common date formats
        for fmt in ('%Y-%m-%d', '%d-%b-%y', '%d/%m/%Y', '%d-%m-%Y'):
            try:
                dt_obj = datetime.strptime(date_of_birth_str, fmt)
                return dt_obj.strftime('%d%m%Y')
            except ValueError:
                pass
        # If none of the above formats work, try to handle 'DD-Mon-YY' where year is 2 digits
        if re.match(r'\d{2}-\w{3}-\d{2}', date_of_birth_str):
            # Example: 28-Nov-03 -> 28112003
            # This is a bit tricky with strptime for 2-digit years, so manual mapping might be safer
            # For simplicity, let's assume common formats are handled by the loop above
            pass
        frappe.log_error(f"Could not parse date of birth: {date_of_birth_str}", "Date Parsing Error")
        return None
    except Exception as e:
        frappe.log_error(f"Error formatting date of birth {date_of_birth_str}: {e}", "Date Formatting Error")
        return None

@frappe.whitelist()
def create_employee_users():
    sql_file_path = "/Users/user/Projects/custom-siumang/tabEmployee.sql"
    employees_data = parse_employee_sql_data(sql_file_path)

    role_name = "Employee Portal"

    for data in employees_data:
        employee_id = data.get("employee_id")
        employee_name = data.get("employee_name")
        cell_number = data.get("cell_number")

        date_of_birth_str = data.get("date_of_birth")


        if not employee_id:
            frappe.log_error(f"Skipping employee due to missing employee_id: {employee_name}", "Create Employee User")
            continue

        # Format cell number
        formatted_cell_number = format_phone_number(cell_number)
        if not formatted_cell_number:
            frappe.log_error(f"Skipping employee {employee_name} due to invalid cell number: {cell_number}", "Create Employee User")
            continue

        # Determine user ID (prioritize cell_number)
        user_id = formatted_cell_number

        # Format date of birth for password
        password = format_date_of_birth_for_password(date_of_birth_str)
        if not password:
            frappe.log_error(f"Skipping employee {employee_name} due to invalid date of birth for password: {date_of_birth_str}", "Create Employee User")
            continue

        # Find the Employee DocType
        employee_doc = None
        if employee_id:
            employee_doc = frappe.get_doc("Employee", employee_id)
        elif employee_name:
            employee_doc = frappe.get_list("Employee", filters={"employee_name": employee_name}, limit=1)
            if employee_doc:
                employee_doc = frappe.get_doc("Employee", employee_doc[0].name)

        if not employee_doc:
            frappe.log_error(f"Could not find Employee DocType for {employee_name} ({employee_id})", "Create Employee User")
            continue

        # Check user_id in Employee DocType
        if not employee_doc.user_id:
            # User ID in Employee DocType is empty, create/update Frappe User
            user = None
            if frappe.db.exists("User", user_id):
                user = frappe.get_doc("User", user_id)
                print(f"User {user_id} already exists. Updating roles.")
            else:
                try:
                    user = frappe.get_doc({
                        "doctype": "User",
                        "email": user_id, # Frappe uses 'email' as the user ID field
                        "first_name": employee_name.split(' ')[0] if employee_name else user_id,
                        "last_name": ' '.join(employee_name.split(' ')[1:]) if employee_name and len(employee_name.split(' ')) > 1 else '',
                        "enabled": 1,
                        "new_password": password,
                        "send_welcome_email": 0
                    })
                    user.insert(ignore_permissions=True)
                    frappe.db.commit()
                    print(f"User {user_id} created for {employee_name}.")
                except Exception as e:
                    frappe.log_error(f"Error creating user {user_id} for {employee_name}: {e}", "Create Employee User")
                    continue

            # Assign role to user
            if user and role_name not in [r.role for r in user.roles]:
                user.add_roles(role_name)
                user.save(ignore_permissions=True)
                frappe.db.commit()
                print(f"Role '{role_name}' assigned to user {user_id}.")

            # Update Employee DocType with user_id
            employee_doc.user_id = user_id
            employee_doc.save(ignore_permissions=True)
            frappe.db.commit()
            print(f"Employee {employee_name} linked to user {user_id}.")
        else:
            # User ID in Employee DocType is already set, ensure correct role
            user_id_from_doc = employee_doc.user_id
            if frappe.db.exists("User", user_id_from_doc):
                user = frappe.get_doc("User", user_id_from_doc)
                if role_name not in [r.role for r in user.roles]:
                    user.add_roles(role_name)
                    user.save(ignore_permissions=True)
                    frappe.db.commit()
                    print(f"Role '{role_name}' assigned to existing user {user_id_from_doc}.")
                else:
                    print(f"User {user_id_from_doc} already has role '{role_name}'.")
            else:
                frappe.log_error(f"User {user_id_from_doc} linked in Employee DocType for {employee_name} does not exist.", "Create Employee User")

    print("Employee user creation/update process completed.")

if __name__ == "__main__":
    create_employee_users()
