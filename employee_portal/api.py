import frappe
from datetime import datetime

@frappe.whitelist(allow_guest=True)
def employee_login(phone_number, dob):
    try:
        # 1. Find employee by phone number
        employee = frappe.get_doc("Employee", {"cell_number": phone_number})

        if not employee:
            frappe.throw("Karyawan dengan nomor telepon ini tidak ditemukan.")

        # 2. Validate Date of Birth (DOB)
        try:
            dob_date = datetime.strptime(dob, "%d%m%Y").date()
        except ValueError:
            frappe.throw("Format Tanggal Lahir salah. Gunakan format 8 digit ddmmyyyy.")

        if employee.date_of_birth != dob_date:
            frappe.throw("Nomor Telepon atau Tanggal Lahir salah.")

        # 3. Find or Create User
        user_id = employee.user_id
        if not user_id:
            # User does not exist, create a new one
            user_email = f"{employee.employee_number}@siumang.local"
            if frappe.db.exists("User", user_email):
                user_id = user_email
            else:
                new_user = frappe.get_doc({
                    "doctype": "User",
                    "email": user_email,
                    "first_name": employee.employee_name,
                    "send_welcome_email": 0,
                    "user_type": "System User",
                    "roles": [
                        {
                            "role": "Employee Portal"
                        }
                    ]
                })
                new_user.insert(ignore_permissions=True)
                user_id = new_user.name
                
                # Link user back to employee
                employee.user_id = user_id
                employee.save(ignore_permissions=True)
                frappe.db.commit()

        # 4. Perform Login
        frappe.local.login_manager.user = user_id
        frappe.local.login_manager.post_login()

    except frappe.exceptions.DoesNotExistError:
        frappe.throw("Karyawan dengan nomor telepon ini tidak ditemukan.")
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Employee Login Error")
        frappe.throw(f"Terjadi kesalahan saat proses login: {str(e)}")

@frappe.whitelist(allow_guest=True)
def get_login_settings():
    return {
        "allow_login_using_mobile_number": frappe.db.get_single_value("System Settings", "allow_login_using_mobile_number")
    }
