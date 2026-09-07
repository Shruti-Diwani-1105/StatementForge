/**
 * Admin Panel JavaScript Controller for StatementForge
 * Communicates with backend via QWebChannel bridge.
 */

document.addEventListener('DOMContentLoaded', () => {
    // Wait for QWebChannel bridge initialization
    if (window.pyBridge) {
        initAdminPanel();
    } else {
        document.addEventListener('pyBridgeReady', () => {
            initAdminPanel();
        });
    }
});

let allUsersData = [];
let allStatementsData = [];

function switchTab(tabName) {
    const cleanTab = tabName.replace('tab-', '').replace('admin_', '');
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.style.display = 'none');

    const targetBtn = document.querySelector(`.tab-btn[data-tab="tab-${cleanTab}"]`);
    if (targetBtn) targetBtn.classList.add('active');

    const targetEl = document.getElementById(`tab-${cleanTab}`);
    if (targetEl) targetEl.style.display = 'block';
}

function initAdminPanel() {
    loadSystemStats();
    loadUsers();
    loadStatements();
    loadAuditLogs();

    // Tab Switching
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.style.display = 'none');
            
            btn.classList.add('active');
            const targetId = btn.getAttribute('data-tab');
            const targetEl = document.getElementById(targetId);
            if (targetEl) targetEl.style.display = 'block';
        });
    });

    // User Search Input
    const userSearch = document.getElementById('user-search-input');
    if (userSearch) {
        userSearch.addEventListener('input', (e) => {
            const query = e.target.value.toLowerCase();
            renderUsersTable(allUsersData.filter(u => 
                u.name.toLowerCase().includes(query) || 
                u.email.toLowerCase().includes(query) ||
                u.username.toLowerCase().includes(query)
            ));
        });
    }
}

function showToast(msg) {
    const toast = document.getElementById('toast-notification');
    if (toast) {
        toast.textContent = msg;
        toast.style.display = 'block';
        setTimeout(() => {
            toast.style.display = 'none';
        }, 3000);
    }
}

// 1. System Stats
function loadSystemStats() {
    if (!window.pyBridge || !window.pyBridge.getAdminStats) return;
    window.pyBridge.getAdminStats((stats) => {
        if (stats) {
            document.getElementById('stat-total-users').textContent = stats.total_users || 0;
            document.getElementById('stat-active-users').textContent = stats.active_users || 0;
            document.getElementById('stat-total-statements').textContent = stats.total_statements || 0;
            document.getElementById('stat-total-txns').textContent = stats.total_transactions || 0;
            
            const dbBadge = document.getElementById('stat-db-status');
            if (dbBadge) {
                dbBadge.textContent = stats.db_connected ? 'Connected' : 'In-Memory Fallback';
                dbBadge.className = 'badge ' + (stats.db_connected ? 'badge-status-active' : 'badge-role-user');
            }
        }
    });
}

// 2. Load Users
function loadUsers() {
    if (!window.pyBridge || !window.pyBridge.getAdminUsers) return;
    window.pyBridge.getAdminUsers((users) => {
        allUsersData = users || [];
        renderUsersTable(allUsersData);
    });
}

function renderUsersTable(users) {
    const tbody = document.getElementById('users-table-body');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (!users || users.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; color: var(--text-muted);">No registered users found.</td></tr>`;
        return;
    }

    users.forEach(user => {
        const tr = document.createElement('tr');
        
        const isUserAdmin = (user.role === 'admin' || user.role === 'Administrator');
        const isActive = (user.status === 'active');

        tr.innerHTML = `
            <td><strong>${escapeHtml(user.name)}</strong><br><small style="color:var(--text-muted);">${escapeHtml(user.username)}</small></td>
            <td>${escapeHtml(user.email)}</td>
            <td>${escapeHtml(user.phone || 'N/A')}</td>
            <td>
                <span class="badge ${isUserAdmin ? 'badge-role-admin' : 'badge-role-user'}">${isUserAdmin ? 'ADMIN' : 'USER'}</span>
            </td>
            <td>
                <span class="badge ${isActive ? 'badge-status-active' : 'badge-status-disabled'}">${isActive ? 'ACTIVE' : 'DISABLED'}</span>
            </td>
            <td style="font-size:12px; color:var(--text-muted);">${user.created_at.split('T')[0]}</td>
            <td>
                <div class="action-btn-group">
                    <button class="btn-sm" onclick="toggleUserRole('${user.email}', '${isUserAdmin ? 'user' : 'admin'}')">
                        ${isUserAdmin ? 'Make User' : 'Make Admin'}
                    </button>
                    <button class="btn-sm" onclick="toggleUserStatus('${user.email}', '${isActive ? 'disabled' : 'active'}')">
                        ${isActive ? 'Disable' : 'Enable'}
                    </button>
                    <button class="btn-sm btn-danger" onclick="deleteUser('${user.email}')">Delete</button>
                </div>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

// 3. User Actions
function toggleUserRole(email, newRole) {
    if (!window.pyBridge || !window.pyBridge.updateUserRole) return;
    window.pyBridge.updateUserRole(email, newRole, (res) => {
        if (res && res.success) {
            showToast(res.message);
            loadUsers();
            loadSystemStats();
        } else {
            showToast(res ? res.message : 'Failed to update user role.');
        }
    });
}

function toggleUserStatus(email, newStatus) {
    if (!window.pyBridge || !window.pyBridge.updateUserStatus) return;
    window.pyBridge.updateUserStatus(email, newStatus, (res) => {
        if (res && res.success) {
            showToast(res.message);
            loadUsers();
            loadSystemStats();
        } else {
            showToast(res ? res.message : 'Failed to update user status.');
        }
    });
}

function deleteUser(email) {
    if (!confirm(`Are you sure you want to delete user ${email}? This action cannot be undone.`)) {
        return;
    }
    if (!window.pyBridge || !window.pyBridge.deleteUserAccount) return;
    window.pyBridge.deleteUserAccount(email, (res) => {
        if (res && res.success) {
            showToast(res.message);
            loadUsers();
            loadSystemStats();
        } else {
            showToast(res ? res.message : 'Failed to delete user.');
        }
    });
}

// 4. Statements Audit
function loadStatements() {
    if (!window.pyBridge || !window.pyBridge.getAdminStatements) return;
    window.pyBridge.getAdminStatements((statements) => {
        allStatementsData = statements || [];
        const tbody = document.getElementById('statements-table-body');
        if (!tbody) return;
        tbody.innerHTML = '';

        if (!statements || statements.length === 0) {
            tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color: var(--text-muted);">No parsed statement logs found.</td></tr>`;
            return;
        }

        statements.forEach(stmt => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><strong>${escapeHtml(stmt.bank_name)}</strong></td>
                <td>${escapeHtml(stmt.user_id)}</td>
                <td><span class="badge badge-role-admin">${stmt.total_transactions} txns</span></td>
                <td>${escapeHtml(stmt.statement_period)}</td>
                <td>${stmt.processing_time.toFixed(2)}s</td>
                <td>${escapeHtml(stmt.upload_date)}</td>
            `;
            tbody.appendChild(tr);
        });
    });
}

// 5. Audit Logs
function loadAuditLogs() {
    if (!window.pyBridge || !window.pyBridge.getAdminAuditLogs) return;
    window.pyBridge.getAdminAuditLogs((logs) => {
        const tbody = document.getElementById('audit-table-body');
        if (!tbody) return;
        tbody.innerHTML = '';

        if (!logs || logs.length === 0) {
            tbody.innerHTML = `<tr><td colspan="4" style="text-align:center; color: var(--text-muted);">No security or audit events recorded.</td></tr>`;
            return;
        }

        logs.forEach(log => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${escapeHtml(log.timestamp)}</td>
                <td><strong>${escapeHtml(log.user)}</strong></td>
                <td><span class="badge badge-status-active">${escapeHtml(log.action)}</span></td>
                <td>${escapeHtml(log.details)}</td>
            `;
            tbody.appendChild(tr);
        });
    });
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}
