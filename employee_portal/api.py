import frappe
from datetime import datetime
from frappe.www.login import login as standard_login

@frappe.whitelist(allow_guest=True)
def custom_login(usr, pwd, with_csrf=False):
    try:
        allow_mobile_login = frappe.db.get_single_value("System Settings", "allow_login_using_mobile_number")
        if allow_mobile_login and usr.isnumeric():
            employee_login(phone_number=usr, dob=pwd)
        else:
            standard_login(usr, pwd, with_csrf)
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Custom Login Router Error")
        frappe.throw("Authentication Error")

@frappe.whitelist(allow_guest=True)
def employee_login(phone_number, dob):
    try:
        employee = frappe.get_doc("Employee", {"cell_number": phone_number})

        if not employee:
            frappe.throw("Karyawan dengan nomor telepon ini tidak ditemukan.")

        try:
            dob_date = datetime.strptime(dob, "%d%m%Y").date()
        except ValueError:
            frappe.throw("Format Tanggal Lahir salah. Gunakan format 8 digit ddmmyyyy.")

        if employee.date_of_birth != dob_date:
            frappe.throw("Nomor Telepon atau Tanggal Lahir salah.")

        user_id = employee.user_id
        if not user_id:
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
                
                employee.user_id = user_id
                employee.save(ignore_permissions=True)
                frappe.db.commit()

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