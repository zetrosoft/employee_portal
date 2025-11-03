frappe.ui.form.on('Sales Order', {
    refresh: function(frm) {
        if (frm.doc.workflow_state && frm.doc.__islocal !== 1) {
            // Clear previous custom indicator
            frm.page.wrapper.find('.custom-workflow-indicator').remove();

            const state = frm.doc.workflow_state;
            let color = {
                "Draft": "darkgrey",
                "Pending Approval (Sales Manager)": "orange",
                "Pending Approval (Finance Manager)": "orange",
                "Pending Approval (Director)": "orange",
                "Approved": "green",
                "Rejected": "red"
            }[state] || "darkgrey";

            // Create the new indicator HTML that mimics Frappe's own indicator style
            let indicator_html = `
                <span class="custom-workflow-indicator indicator-pill whitespace-nowrap ml-2 ${color}">
                    <span class="indicator-dot"></span>
                    <span class="hidden-xs ml-1">${state}</span>
                </span>
            `;
            
            // Find the standard status indicator and append the new indicator after it
            frm.page.wrapper.find('.indicator-pill').last().after(indicator_html);
        }
    }
});