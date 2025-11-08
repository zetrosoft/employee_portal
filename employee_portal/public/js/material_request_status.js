frappe.ui.form.on('Material Request', {
    refresh: function(frm) {
        // Untuk dokumen baru, pastikan status alur kerja kosong dan dapat diedit.
        if (frm.is_new()) {
            frm.set_df_property('workflow_state', 'read_only', 0);
            frm.set_value('workflow_state', null); // Menggunakan null lebih kuat untuk mengosongkan
            frm.refresh_field('workflow_state');
            
            // Hapus juga indikator kustom jika ada
            frm.page.wrapper.find('.custom-workflow-indicator').remove();
            return; 
        }

        // Logika Indikator Status Kustom (hanya untuk dokumen yang sudah disimpan)
        if (frm.doc.workflow_state) {
            // Hapus indikator kustom sebelumnya untuk mencegah duplikasi
            frm.page.wrapper.find('.custom-workflow-indicator').remove();

            const state = frm.doc.workflow_state;
            const status_group = state.split(' ')[0];

            // Pemetaan warna untuk grup status
            const color_map = {
                "Pending": "orange",
                "Submitted": "green", 
                "Rejected": "red"
            };
            const color = color_map[status_group] || "darkgrey";

            // Buat HTML indikator baru (dengan escape untuk keamanan)
            const indicator_html = `
                <span class="custom-workflow-indicator indicator-pill whitespace-nowrap ml-2 ${color}">
                    <span class="indicator-dot"></span>
                    <span class="hidden-xs ml-1">${frappe.utils.escape_html(state)}</span>
                </span>
            `;
            
            // Tambahkan indikator kustom setelah indikator standar terakhir
            frm.page.wrapper.find('.indicator-pill').last().after(indicator_html);
        } else {
            // Jika tidak ada status alur kerja pada dokumen yang disimpan, pastikan tidak ada indikator yang ditampilkan
            frm.page.wrapper.find('.custom-workflow-indicator').remove();
        }
    }
});