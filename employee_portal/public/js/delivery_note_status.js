frappe.ui.form.on('Delivery Note', {
    refresh: function(frm) {
        // --- Custom Status Pill Indicator ---
        if (frm.doc.workflow_state) {
            frm.page.wrapper.find('.custom-workflow-indicator').remove();
            const state = frm.doc.workflow_state;
            
            const color_map = {
                "Pending": "orange",
                "Approved": "cyan",
                "Rejected": "purple", // For Rejected QC
                "Submitted": "green",
                "Closed": "#2C3E50", // Dark Slate
                "Draft": "darkgrey",
            };
            const status_group = state.split(' ')[0];
            const color = color_map[status_group] || "darkgrey";

            const indicator_html = `
                <span class="custom-workflow-indicator indicator-pill whitespace-nowrap ml-2 ${color}">
                    <span class="indicator-dot"></span>
                    <span class="hidden-xs ml-1">${frappe.utils.escape_html(state)}</span>
                </span>
            `;
            frm.page.wrapper.find('.indicator-pill').last().after(indicator_html);
        } else {
            frm.page.wrapper.find('.custom-workflow-indicator').remove();
        }

        // --- QC Rejection Popup ---
        if (frm.doc.workflow_state === 'Rejected QC' && frm.doc.custom_rejection_reason) {
            frappe.msgprint({
                title: __('Quality Inspection Rejected'),
                indicator: 'red',
                message: `<b>Submission is blocked.</b><br><br>Reason:<br>${frm.doc.custom_rejection_reason}`
            });
        }
    }
});
