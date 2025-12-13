import frappe
from hrms.hr.doctype.leave_application.leave_application import LeaveApplication
import logging

logger = logging.getLogger(__name__)

class LeaveApplicationCustom(LeaveApplication):
    def on_update(self): # Menambahkan override untuk on_update
        super().on_update() # Pastikan fungsi asli tetap terpanggil
        logger.info(
            f"Leave Application {self.name} on_update triggered. leave_approver: {self.leave_approver}, current_user: {frappe.session.user}",
            extra={"leave_application_override_debug": True}
        )
        # Anda bisa menambahkan logika notifikasi kustom di sini jika diperlukan,
        # tetapi fokus utama kita sekarang adalah debugging tombol workflow.

    def notify_approver(self):
        """
        Overrides the standard notify_approver to disable PWA Notification.
        This is a workaround for the 'erps_db.pwa_notification_id_seq' error.
        """
        logger.info(
            f"PWA Notification for Leave Application {self.name} is disabled via override.",
            extra={"leave_application_override": True}
        )
        pass