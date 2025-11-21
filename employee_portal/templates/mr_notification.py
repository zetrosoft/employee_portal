import frappe


# --- Helper Function untuk Mendapatkan Role Penerima ---
def get_recipients_by_role(role_name):
    """Mengambil daftar email pengguna berdasarkan nama peran (Role Profile)."""
    return frappe.get_list('User', filters={'role_profile_name': role_name, 'enabled': 1}, pluck='email')

# --- 1. Fungsi untuk Tombol 'Submit' (Transisi Draft ke Pending Approval) ---
def handle_submit_transition(doc, method):
    """Dipicu saat tombol 'Submit' diklik dari status Draft."""

    # DEBUG: Cek apakah hook 'submit' dieksekusi
    frappe.log_error(f"WORKFLOW HOOK: 'submit' dipicu untuk MR {doc.name}", "MR WORKFLOW DEBUG")

    # Notifikasi hanya dikirim jika dokumen berpindah ke status PENDING

    # KASUS 1: Pending Stock Manager
    if doc.workflow_state == 'Pending SM Approval':

        recipients = get_recipients_by_role('Stock Manager')
        # DEBUG: Cek apakah kondisi terpenuhi dan siapa penerimanya
        frappe.log_error(f"LOGIC: Transisi ke Pending SM. Penerima: {recipients}", "MR WORKFLOW DEBUG")

        frappe.send_notification(
            title=f"MR {doc.name} Menunggu Persetujuan Anda (Gudang)",
            message=f"Material Request (Gudang) dari {doc.owner_name} memerlukan persetujuan Anda.",
            recipients=recipients,
            doctype=doc.doctype,
            name=doc.name,
            notification_type='System Notification'
        )

    # KASUS 2: Pending Production Manager
    elif doc.workflow_state == 'Pending PM Approval':

        recipients = get_recipients_by_role('Production Manager')
        # DEBUG: Cek apakah kondisi terpenuhi dan siapa penerimanya
        frappe.log_error(f"LOGIC: Transisi ke Pending PM. Penerima: {recipients}", "MR WORKFLOW DEBUG")

        frappe.send_notification(
            title=f"MR {doc.name} Menunggu Persetujuan Anda (Produksi)",
            message=f"Material Request (Produksi) dari {doc.owner_name} memerlukan persetujuan Anda.",
            recipients=recipients,
            doctype=doc.doctype,
            name=doc.name,
            notification_type='System Notification'
        )

# --- 2. Fungsi untuk Tombol 'Approve' (Transisi dari Pending ke Submitted/Status Akhir) ---
def handle_approval_transition(doc, method):
    """Dipicu saat tombol 'Approve' diklik."""

    # DEBUG: Cek apakah hook 'approve' dieksekusi
    frappe.log_error(f"WORKFLOW HOOK: 'approve' dipicu untuk MR {doc.name}", "MR WORKFLOW DEBUG")

    # Notifikasi SUBMITTED (ke Pembuat)
    if doc.workflow_state in ('Submitted - Stock User', 'Submitted - Production User'):

        # DEBUG: Cek apakah kondisi terpenuhi
        frappe.log_error(f"LOGIC: Transisi ke Submitted. Penerima: {doc.owner}", "MR WORKFLOW DEBUG")

        frappe.send_notification(
            title=f"MR {doc.name} Telah Disetujui!",
            message=f"Material Request Anda ({doc.name}) telah disetujui oleh {frappe.session.user}.",
            recipients=[doc.owner], # Kirim ke pemilik/pembuat dokumen
            doctype=doc.doctype,
            name=doc.name,
            notification_type='System Notification'
        )

# --- 3. Fungsi untuk Tombol 'Reject' (Transisi ke Rejected) ---
def handle_rejection_transition(doc, method):
    """Dipicu saat tombol 'Reject' diklik (ke status Rejected)."""

    # DEBUG: Cek apakah hook 'reject' dieksekusi
    frappe.log_error(f"WORKFLOW HOOK: 'reject' dipicu untuk MR {doc.name}", "MR WORKFLOW DEBUG")

    # Notifikasi REJECTED (ke Pembuat)
    if doc.workflow_state in ('Rejected - Stock User', 'Rejected - Production User'):

        # DEBUG: Cek apakah kondisi terpenuhi
        frappe.log_error(f"LOGIC: Transisi ke Rejected. Penerima: {doc.owner}", "MR WORKFLOW DEBUG")

        frappe.send_notification(
            title=f"MR {doc.name} Ditolak",
            message=f"Material Request Anda ({doc.name}) telah ditolak oleh {frappe.session.user}.",
            recipients=[doc.owner],
            doctype=doc.doctype,
            name=doc.name,
            notification_type='System Notification'
        )
