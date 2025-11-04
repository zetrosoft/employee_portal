frappe.ui.form.on('Purchase Order', {
    refresh: function(frm) {
        // Always remove the indicator on every refresh to prevent visual artifacts
        frm.page.wrapper.find('.custom-workflow-indicator').remove();

        // Add the indicator back only if it's a saved document with a workflow state
        if (frm.doc.workflow_state && !frm.doc.__islocal) {
            const state = frm.doc.workflow_state;
            let color = {
                "Pending": "orange",
                "Approved": "green",
                "Rejected": "red"
            }[state.split(' ')[0]] || "darkgrey";

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

        // Control Print Button Visibility based on docstatus
        if (frm.doc.docstatus === 1) {
            frm.page.toggle_print_btn(true); // Show print button for Submitted docs
        } else {
            frm.page.toggle_print_btn(false); // Hide print button for Draft/Cancelled docs
        }
    }
});