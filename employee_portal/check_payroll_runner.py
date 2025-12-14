import frappe
from employee_portal.check_payroll_employee_filters import check_payroll_employee_filters
import json

# --- HARDCODED ARGUMENTS ---
# Ganti nilai-nilai ini sesuai dengan Payroll Entry Anda
COMPANY = "PT. SIUMANG TEMAN SUKSES"
PAYROLL_FREQUENCY = "Monthly"
START_DATE = "2025-12-01"
END_DATE = "2025-12-31"
CURRENCY = "IDR"
PAYROLL_PAYABLE_ACCOUNT = "1111.002 - Kas Besar - SIUMANG"
DESIGNATION = "Operator" # Set None jika tidak ingin memfilter
BRANCH = None
DEPARTMENT = None
GRADE = None
SALARY_SLIP_BASED_ON_TIMESHEET = 0 # 0 for False, 1 for True

def run_check_payroll_filters():
    # Pastikan Frappe context terinisialisasi
    # frappe.init() dan frappe.connect() hanya jika dijalankan DI LUAR bench console/execute
    # Jika dijalankan dari bench console/execute, context sudah ada.
    # Untuk kasus ini, kita asumsikan dijalankan via `python3 script.py` jadi perlu init.
    
    # Check if frappe is already connected
    if not frappe.db:
        # Ganti "siumang" dengan nama situs Frappe Anda
        frappe.init(site="siumang.com") # Sesuaikan dengan nama situs Frappe Anda
        frappe.connect()

    result = check_payroll_employee_filters(
        company=COMPANY,
        payroll_frequency=PAYROLL_FREQUENCY,
        start_date=START_DATE,
        end_date=END_DATE,
        currency=CURRENCY,
        payroll_payable_account=PAYROLL_PAYABLE_ACCOUNT,
        designation=DESIGNATION,
        branch=BRANCH,
        department=DEPARTMENT,
        grade=GRADE,
        salary_slip_based_on_timesheet=SALARY_SLIP_BASED_ON_TIMESHEET
    )
    print(result)
    frappe.destroy() # Bersihkan koneksi Frappe

if __name__ == "__main__":
    run_check_payroll_filters()
