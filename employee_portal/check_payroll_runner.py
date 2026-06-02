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
    # Jika dijalankan dari bench console/execute, context sudah ada (frappe.db sudah terhubung).
    if not frappe.db:
        # Coba ambil site dari konteks lokal atau environment
        site = getattr(frappe.local, "site", None)
        
        if not site:
            import os
            # Jika dijalankan sebagai script mandiri di dalam folder frappe-bench/sites
            if os.path.exists("currentsite.txt"):
                with open("currentsite.txt") as f:
                    site = f.read().strip()
            elif os.path.exists("sites/currentsite.txt"):
                with open("sites/currentsite.txt") as f:
                    site = f.read().strip()

        if not site:
            print("Error: Nama site tidak ditemukan. Gunakan 'bench --site [nama-site] execute ...'")
            return

        frappe.init(site=site)
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
    
    # Jangan destroy jika dalam konteks bench agar tidak merusak proses lain
    if not getattr(frappe.local, "site", None):
        frappe.destroy()

if __name__ == "__main__":
    run_check_payroll_filters()
