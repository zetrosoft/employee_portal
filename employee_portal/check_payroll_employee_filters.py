import frappe
import json
from frappe.utils import flt, getdate, cint
# Perubahan di sini: Impor DocType dari frappe.query_builder, Term dari frappe.query_builder.terms
from frappe.query_builder import DocType, SubQuery
from frappe.query_builder.terms import Term
from frappe.query_builder.functions import Coalesce, Count # Impor fungsi secara terpisah

# --- HELPER FUNCTIONS (REDEFINED FROM payroll_entry.py FOR DIAGNOSTIC PURPOSES) ---

def get_salary_structure(company, currency, salary_slip_based_on_timesheet, payroll_frequency):
    SalaryStructure = DocType("Salary Structure")
    query = (
        frappe.qb.from_(SalaryStructure)
        .select(SalaryStructure.name)
        .where(
            (SalaryStructure.docstatus == 1)
            & (SalaryStructure.is_active == "Yes")
            & (SalaryStructure.company == company)
            & (SalaryStructure.currency == currency)
            & (SalaryStructure.salary_slip_based_on_timesheet == salary_slip_based_on_timesheet)
        )
    )
    if not salary_slip_based_on_timesheet:
        query = query.where(SalaryStructure.payroll_frequency == payroll_frequency)
    return query.run(pluck=True)

def get_filtered_employees(sal_struct, filters):
    SalaryStructureAssignment = DocType("Salary Structure Assignment")
    Employee = DocType("Employee")

    query = (
        frappe.qb.from_(Employee)
        .join(SalaryStructureAssignment)
        .on(Employee.name == SalaryStructureAssignment.employee)
        .where(
            (SalaryStructureAssignment.docstatus == 1)
            & (Employee.status != "Inactive")
            & (Employee.company == filters.company)
            & ((Employee.date_of_joining <= filters.end_date) | (Employee.date_of_joining.isnull()))
            & ((Employee.relieving_date >= filters.start_date) | (Employee.relieving_date.isnull()))
            & (SalaryStructureAssignment.salary_structure.isin(sal_struct))
            & (SalaryStructureAssignment.payroll_payable_account == filters.payroll_payable_account)
            & (filters.end_date >= SalaryStructureAssignment.from_date)
        )
    )

    for fltr_key in ["branch", "department", "designation", "grade"]:
        if filters.get(fltr_key):
            query = query.where(Employee[fltr_key] == filters[fltr_key])
    
    # Match conditions (izin akses) diabaikan untuk skrip diagnostik ini
    # karena kita berasumsi script dijalankan oleh admin atau via bench.
    
    return query.run(pluck=True)

def remove_payrolled_employees(employee_names, start_date, end_date):
    SalarySlip = DocType("Salary Slip")
    employees_with_payroll = (
        frappe.qb.from_(SalarySlip)
        .select(SalarySlip.employee)
        .distinct()
        .where(
            (SalarySlip.docstatus == 1)
            & (SalarySlip.start_date == start_date)
            & (SalarySlip.end_date == end_date)
        )
    ).run(pluck=True)
    return [emp for emp in employee_names if emp not in employees_with_payroll]

# --- MAIN DIAGNOSTIC FUNCTION ---

@frappe.whitelist()
def check_payroll_employee_filters(
    company,
    payroll_frequency,
    start_date,
    end_date,
    currency,
    payroll_payable_account,
    salary_slip_based_on_timesheet=0,
    branch=None,
    department=None,
    designation=None,
    grade=None,
):
    """
    Diagnoses why employees might not appear in Payroll Entry's 'Get Employees' list.
    """
    report = []
    
    filters = frappe._dict({
        "company": company,
        "payroll_frequency": payroll_frequency,
        "start_date": getdate(start_date),
        "end_date": getdate(end_date),
        "currency": currency,
        "payroll_payable_account": payroll_payable_account,
        "salary_slip_based_on_timesheet": cint(salary_slip_based_on_timesheet),
        "branch": branch,
        "department": department,
        "designation": designation,
        "grade": grade,
    })

    report.append("---" + " Diagnostik Filter Karyawan Payroll ---")
    report.append(f"Input Filter: {json.dumps(filters, indent=2)}")

    # Step 1: Check Salary Structures
    sal_structs = get_salary_structure(
        filters.company,
        filters.currency,
        filters.salary_slip_based_on_timesheet,
        filters.payroll_frequency,
    )
    if not sal_structs:
        report.append(f"❌ GAGAL: Tidak ditemukan Struktur Gaji (Salary Structure) aktif yang cocok dengan kriteria berikut:")
        report.append(f"    Company: {filters.company}")
        report.append(f"    Currency: {filters.currency}")
        report.append(f"    Salary Slip Based on Timesheet: {filters.salary_slip_based_on_timesheet}")
        report.append(f"    Payroll Frequency: {filters.payroll_frequency}")
        report.append("    Pastikan ada Salary Structure yang disubmit dan aktif dengan kriteria ini.")
        return "\n".join(report)
    else:
        report.append(f"✅ DITEMUKAN: Struktur Gaji yang cocok: {', '.join(sal_structs)}")

    # Step 2: Get Filtered Employees based on Salary Structure Assignment & other criteria
    all_eligible_employees = get_filtered_employees(sal_structs, filters)
    if not all_eligible_employees:
        report.append(f"❌ GAGAL: Tidak ditemukan karyawan yang memenuhi kriteria dasar:")
        report.append(f"    Karyawan harus Aktif dan memiliki Penugasan Struktur Gaji (Salary Structure Assignment) yang disubmit.")
        report.append(f"    Penugasan Struktur Gaji harus terkait dengan Struktur Gaji yang ditemukan sebelumnya, akun dapat dibayar ({filters.payroll_payable_account}), dan dalam rentang tanggal payroll ({filters.start_date} - {filters.end_date}).")
        if filters.department: report.append(f"    Departemen: {filters.department}")
        if filters.designation: report.append(f"    Jabatan: {filters.designation}")
        if filters.branch: report.append(f"    Cabang: {filters.branch}")
        if filters.grade: report.append(f"    Grade: {filters.grade}")
        return "\n".join(report)
    else:
        report.append(f"✅ DITEMUKAN: Karyawan yang memenuhi kriteria dasar: {', '.join(all_eligible_employees)}")

    # Step 3: Remove already payrolled employees
    final_employees = remove_payrolled_employees(all_eligible_employees, filters.start_date, filters.end_date)
    if not final_employees:
        report.append(f"❌ GAGAL: Semua karyawan yang memenuhi syarat sudah memiliki slip gaji yang disubmit untuk periode {filters.start_date} - {filters.end_date}.")
        report.append("    Ini berarti tidak ada karyawan baru untuk di-payroll.")
        return "\n".join(report)
    else:
        report.append(f"✅ BERHASIL: Karyawan yang siap untuk di-payroll: {', '.join(final_employees)}")

    report.append("\n---" + " Diagnostik Selesai ---")
    report.append("Silakan periksa konfigurasi data Anda di Frappe berdasarkan laporan ini.")
    return "\n".join(report)
