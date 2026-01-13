import frappe
from frappe import _
from hrms.hr.doctype.leave_application.leave_application import LeaveApplication
import logging

logger = logging.getLogger(__name__)

class LeaveApplicationCustom(LeaveApplication):
    def on_update(self):
        super().on_update()
        logger.info(
            f"Leave Application {self.name} on_update triggered. leave_approver: {self.leave_approver}, current_user: {frappe.session.user}",
            extra={"leave_application_override_debug": True}
        )

    def on_submit(self):
        logger.info(f"on_submit triggered. self.status: {self.status}, self.workflow_state: {getattr(self, 'workflow_state', None)}", extra={"leave_application_debug": True})
        current_workflow_state = getattr(self, "workflow_state", None)

        is_pending_workflow_state = current_workflow_state in [
            "Pending Manager Approval",
            "Pending HR Review",
            "Pending HR Manager Approval",
        ]

        if self.docstatus != 1 and self.status in ["Open", "Cancelled"] and not is_pending_workflow_state:
            frappe.log_error(
                message=_("Leave Applications with status 'Open' and 'Cancelled' cannot be submitted."),
                title="Invalid Leave Application Submission",
                reference_doctype=self.doctype,
                reference_name=self.name,
            )
            frappe.throw(_("Leave Applications with status 'Open' or 'Cancelled' cannot be submitted directly without a pending workflow state."))
        else:
            if current_workflow_state == "Approved":
                self.status = "Approved"
            elif current_workflow_state == "Rejected":
                self.status = "Rejected"

            self.validate_back_dated_application()
            self.update_attendance()
            self.validate_for_self_approval()

            if frappe.db.get_single_value("HR Settings", "send_leave_notification"):
               self.notify_employee()
            self.create_leave_ledger_entry()
            self.reload()

    def notify_approver(self):
        logger.info(
            f"PWA Notification for Leave Application {self.name} is disabled via override.",
            extra={"leave_application_override": True}
        )
        pass

    def notify_approval_status(self):
        pass