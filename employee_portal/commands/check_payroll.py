import frappe
import click
from employee_portal.check_payroll_employee_filters import check_payroll_employee_filters

@click.command('check-payroll-filters')
@click.option('--company', required=True, help='Nama perusahaan.')
@click.option('--payroll-frequency', required=True, help='Frekuensi payroll (misal: Monthly).')
@click.option('--start-date', required=True, help='Tanggal mulai (YYYY-MM-DD).')
@click.option('--end-date', required=True, help='Tanggal akhir (YYYY-MM-DD).')
@click.option('--currency', required=True, help='Mata uang (misal: IDR).')
@click.option('--payroll-payable-account', required=True, help='Akun payable payroll.')
@click.option('--designation', help='Jabatan (opsional).')
@click.option('--branch', help='Cabang (opsional).')
@click.option('--department', help='Departemen (opsional).')
@click.option('--grade', help='Grade (opsional).')
@click.option('--salary-slip-based-on-timesheet', type=int, default=0, help='0 atau 1.')
def check_filters(company, payroll_frequency, start_date, end_date, currency, payroll_payable_account,
                  designation=None, branch=None, department=None, grade=None, salary_slip_based_on_timesheet=0):
    """
    Menjalankan diagnostik untuk filter karyawan payroll.
    """
    result = check_payroll_employee_filters(
        company=company,
        payroll_frequency=payroll_frequency,
        start_date=start_date,
        end_date=end_date,
        currency=currency,
        payroll_payable_account=payroll_payable_account,
        salary_slip_based_on_timesheet=salary_slip_based_on_timesheet,
        branch=branch,
        department=department,
        designation=designation,
        grade=grade
    )
    print(result)
