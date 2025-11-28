frappe.ui.form.on('Delivery Note', {
    refresh: function(frm) {
        // Add a visual indicator for the workflow state
        if (frm.doc.workflow_state) {
            const state_colors = {
                "Draft": "grey",
                "Pending Logistics Manager Approval": "orange",
                "Pending QC Inspection": "orange",
                "Approved QC": "blue",
                "Rejected QC": "red",
                "Submitted": "green",
                "Cancelled": "red"
            };
            const color = state_colors[frm.doc.workflow_state] || "darkgrey";
            frm.page.set_indicator(frm.doc.workflow_state, color);
        }

        // Show a persistent message if the document is in Rejected QC state
        if (frm.doc.workflow_state === 'Rejected QC' && frm.doc.custom_rejection_reason) {
            frm.dashboard.set_headline(
                `Quality Inspection Rejected <i class="fa fa-times"></i>`,
                'text-danger'
            );
            
            // Show the rejection reason in a message box
            // This message will appear every time the document is loaded in this state
            frm.add_custom_button(__('Show Rejection Reason'), function() {
                 frappe.msgprint({
                    title: __('Quality Inspection Rejection Details'),
                    indicator: 'red',
                    message: __(frm.doc.custom_rejection_reason)
                });
            }, 'fa fa-info-circle', 'btn-danger');

            // Also show an initial message so the user doesn't miss it
            if (!frm.is_new()) {
                 frappe.show_alert({
                    message: __('This Delivery Note was rejected during Quality Inspection. Please click "Show Rejection Reason" for details and either Revise or Cancel the document.'),
                    indicator: 'red'
                }, 10); // Show for 10 seconds
            }
        }
    }
});
