import logging

import frappe
from hrms.hr.doctype.expense_claim.expense_claim import ExpenseClaim

logger = logging.getLogger(__name__)

class ExpenseClaimCustom(ExpenseClaim):
    def notify_approver(self):
        """
        Overrides the standard notify_approver to disable PWA Notification for Expense Claim.
        This is a workaround for the 'erps_db.pwa_notification_id_seq' error.
        """
        logger.info(
            f"PWA Notification for Expense Claim {self.name} is disabled via override.",
            extra={"expense_claim_override": True}
        )
        pass
