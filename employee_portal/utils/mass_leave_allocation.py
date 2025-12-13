import frappe
import logging
from frappe.utils import getdate

# Dapatkan instance logger untuk modul ini
logger = logging.getLogger(__name__)

def create_mass_leave_allocation(leave_policy_doc, method=None):
    """
    Creates Leave Allocations for employees based on a Leave Policy's designation.
    This function should be called on_submit or on_update of Leave Policy.
    """
    # Muat ulang leave_policy untuk memastikan semua field tersedia
    try:
        leave_policy = frappe.get_doc("Leave Policy", leave_policy_doc.name)
    except Exception as e:
        logger.error(
            f"Failed to load Leave Policy {leave_policy_doc.name}: {e}",
            exc_info=True,
            extra={"mass_leave_allocation": True}
        )
        frappe.msgprint(f"Gagal memuat Kebijakan Cuti {leave_policy_doc.name}.", title="Alokasi Cuti Massal Gagal")
        return

    if not leave_policy.designation:
        logger.warning(
            f"Leave Policy {leave_policy.name} has no Designation linked. Skipping mass allocation.",
            extra={"mass_leave_allocation": True}
        )
        return

    logger.info(
        f"Processing mass leave allocation for Leave Policy: {leave_policy.name} "
        f"and Designation: {leave_policy.designation}",
        extra={"mass_leave_allocation": True}
    )

    # Find all employees with the linked designation
    employees = frappe.get_all(
        "Employee",
        filters={"designation": leave_policy.designation, "status": "Active"},
        fields=["name", "employee_name"]
    )

    if not employees:
        logger.warning(
            f"No active employees found for Designation: {leave_policy.designation}. Skipping mass allocation.",
            extra={"mass_leave_allocation": True}
        )
        return

    # Tentukan Fiscal Year sekali di awal
    fiscal_year_name = None
    fiscal_year_name = frappe.defaults.get_user_default("fiscal_year")

    if not fiscal_year_name:
        active_fiscal_year = frappe.get_value(
            "Fiscal Year",
            {"year_start_date": ["<=", getdate()], "year_end_date": [">=", getdate()]},
            "name"
        )
        fiscal_year_name = active_fiscal_year
    
    if not fiscal_year_name:
        logger.error(
            "Could not determine Fiscal Year. Skipping mass allocation.",
            extra={"mass_leave_allocation": True}
        )
        frappe.msgprint(f"Gagal menentukan Tahun Fiskal.", title="Alokasi Cuti Massal Gagal")
        return

    # Ambil tanggal mulai dan akhir dari Fiscal Year yang ditentukan
    fiscal_year_doc = frappe.get_doc("Fiscal Year", fiscal_year_name)
    allocation_from_date = fiscal_year_doc.year_start_date
    allocation_to_date = fiscal_year_doc.year_end_date # Menggunakan fiscal_year_doc.year_end_date

    if not allocation_from_date or not allocation_to_date:
        logger.error(
            f"Fiscal Year {fiscal_year_name} is missing 'year_start_date' or 'year_end_date'. Skipping mass allocation.",
            extra={"mass_leave_allocation": True}
        )
        frappe.msgprint(f"Tahun Fiskal {fiscal_year_name} tidak memiliki tanggal mulai atau akhir.", title="Alokasi Cuti Massal Gagal")
        return

    # Sekarang iterasi melalui setiap detail kebijakan cuti
    if not leave_policy.leave_policy_details:
        logger.warning(
            f"Leave Policy {leave_policy.name} has no Leave Policy Details. Skipping mass allocation.",
            extra={"mass_leave_allocation": True}
        )
        frappe.msgprint(f"Kebijakan Cuti {leave_policy.name} tidak memiliki Detail Kebijakan Cuti.", title="Alokasi Cuti Massal Gagal")
        return

    for detail in leave_policy.leave_policy_details:
        leave_type = detail.leave_type
        annual_allocation_days = detail.annual_allocation

        if not leave_type:
            logger.warning(
                f"Leave Policy Detail in {leave_policy.name} is missing Leave Type. Skipping.",
                extra={"mass_leave_allocation": True}
            )
            continue
        
        # Iterasi melalui setiap karyawan
        for employee_data in employees:
            employee = employee_data.name
            
            # Check if an allocation already exists for this employee, leave type, and fiscal year
            existing_allocation = frappe.db.exists(
                "Leave Allocation",
                {
                    "employee": employee,
                    "leave_type": leave_type, # Menggunakan leave_type dari detail
                    "fiscal_year": fiscal_year_name, # Menggunakan fiscal_year_name
                    "docstatus": ("<", 2) # Not cancelled
                }
            )

            if existing_allocation:
                logger.info(
                    f"Leave Allocation for {employee_data.employee_name} ({employee}) "
                    f"for {leave_type} in {fiscal_year_name} already exists. Skipping.",
                    extra={"mass_leave_allocation": True}
                )
                continue
            
            try:
                # Create new Leave Allocation
                allocation = frappe.new_doc("Leave Allocation")
                allocation.employee = employee
                allocation.employee_name = employee_data.employee_name
                allocation.leave_type = leave_type # Menggunakan leave_type dari detail
                allocation.new_leaves_allocated = annual_allocation_days # Menggunakan annual_allocation dari detail
                allocation.from_date = allocation_from_date # <-- Menggunakan tanggal dari Fiscal Year
                allocation.to_date = allocation_to_date # <-- Menggunakan tanggal dari Fiscal Year
                allocation.fiscal_year = fiscal_year_name # Menggunakan fiscal_year_name
                
                # Additional fields from leave_policy could be mapped here
                # For example, if leave_policy has "is_earned_leave", "is_carry_forward", etc.
                
                allocation.insert(ignore_permissions=True)
                allocation.submit()

                logger.info(
                    f"Created Leave Allocation {allocation.name} for {employee_data.employee_name} "
                    f"({employee}) for {leave_type}.",
                    extra={"mass_leave_allocation": True}
                )
                frappe.msgprint(f"Alokasi Cuti dibuat untuk {employee_data.employee_name} ({leave_type})", title="Alokasi Cuti Massal Berhasil")

            except Exception as e:
                error_message = f"Gagal membuat Alokasi Cuti untuk {employee_data.employee_name} ({leave_type}): {e}"
                logger.error(
                    error_message,
                    exc_info=True, # Untuk mencetak traceback
                    extra={"mass_leave_allocation": True}
                )
                frappe.msgprint(error_message, title="Alokasi Cuti Massal Gagal")