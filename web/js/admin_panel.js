/**
 * Admin Panel JavaScript Controller for StatementForge
 * Communicates with backend via QWebChannel bridge.
 */

function getBridge() {
    return window.pybridge || window.pyBridge || (typeof pybridge !== 'undefined' ? pybridge : null);
}

document.addEventListener('DOMContentLoaded', () => {
    initAdminPanel();
});
document.addEventListener('pybridgeReady', () => {
    initAdminPanel();
});
document.addEventListener('pyBridgeReady', () => {
    initAdminPanel();
});

let allUsersData = [];
let allStatementsData = [];
let isInitialized = false;

function switchTab(tabName) {
    const cleanTab = tabName ? tabName.replace('tab-', '').replace('admin_', '').toLowerCase() : 'overview';
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.style.display = 'none');

    const titleEl = document.querySelector('.admin-title-group h1 span');
    const descEl = document.querySelector('.admin-title-group p');
    const cardUsers = document.getElementById('stat-card-users');
    const cardActive = document.getElementById('stat-card-active');
    const cardStmts = document.getElementById('stat-card-stmts');
    const cardTxns = document.getElementById('stat-card-txns');

    if (cleanTab === 'users') {
        const targetBtn = document.querySelector(`.tab-btn[data-tab="tab-users"]`);
        if (targetBtn) targetBtn.classList.add('active');
        const targetEl = document.getElementById('tab-users');
        if (targetEl) targetEl.style.display = 'block';

        if (titleEl) titleEl.textContent = 'User Accounts';
        if (descEl) descEl.textContent = 'Management, permissions, and status controls for all registered users.';
        if (cardUsers) cardUsers.style.display = 'flex';
        if (cardActive) cardActive.style.display = 'flex';
        if (cardStmts) cardStmts.style.display = 'none';
        if (cardTxns) cardTxns.style.display = 'none';
    } else if (cleanTab === 'statements') {
        const targetBtn = document.querySelector(`.tab-btn[data-tab="tab-statements"]`);
        if (targetBtn) targetBtn.classList.add('active');
        const targetEl = document.getElementById('tab-statements');
        if (targetEl) targetEl.style.display = 'block';

        if (titleEl) titleEl.textContent = 'Statement Audit Log';
        if (descEl) descEl.textContent = 'Global bank statement parsing logs and transaction audit trails.';
        if (cardUsers) cardUsers.style.display = 'none';
        if (cardActive) cardActive.style.display = 'none';
        if (cardStmts) cardStmts.style.display = 'flex';
        if (cardTxns) cardTxns.style.display = 'flex';
    } else if (cleanTab === 'logs') {
        const targetBtn = document.querySelector(`.tab-btn[data-tab="tab-logs"]`);
        if (targetBtn) targetBtn.classList.add('active');
        const targetEl = document.getElementById('tab-logs');
        if (targetEl) targetEl.style.display = 'block';

        if (titleEl) titleEl.textContent = 'Security & Activity Logs';
        if (descEl) descEl.textContent = 'System access logs, authentication history, and administrative activity.';
        if (cardUsers) cardUsers.style.display = 'flex';
        if (cardActive) cardActive.style.display = 'flex';
        if (cardStmts) cardStmts.style.display = 'flex';
        if (cardTxns) cardTxns.style.display = 'flex';
    } else {
        // 'overview', 'panel', or default
        const targetBtn = document.querySelector(`.tab-btn[data-tab="tab-users"]`);
        if (targetBtn) targetBtn.classList.add('active');
        const targetEl = document.getElementById('tab-users');
        if (targetEl) targetEl.style.display = 'block';

        if (titleEl) titleEl.textContent = 'Admin Control Center';
        if (descEl) descEl.textContent = 'System metrics, user management, global bank statement audits, and security logging.';
        if (cardUsers) cardUsers.style.display = 'flex';
        if (cardActive) cardActive.style.display = 'flex';
        if (cardStmts) cardStmts.style.display = 'flex';
        if (cardTxns) cardTxns.style.display = 'flex';
    }
}

// Direct IPC Push Handlers (from Python via document.title / runJavaScript)
window.renderAdminUsersData = function(users) {
    allUsersData = users || [];
    applyUserFilters();
};

window.renderAdminStatsData = function(stats) {
    if (!stats) return;
    const totalUsersEl = document.getElementById('stat-total-users');
    const activeUsersEl = document.getElementById('stat-active-users');
    const totalStatementsEl = document.getElementById('stat-total-statements');
    const totalTxnsEl = document.getElementById('stat-total-txns');

    if (totalUsersEl) totalUsersEl.textContent = stats.total_users || 0;
    if (activeUsersEl) activeUsersEl.textContent = stats.active_users || 0;
    if (totalStatementsEl) totalStatementsEl.textContent = stats.total_statements || 0;
    if (totalTxnsEl) totalTxnsEl.textContent = stats.total_transactions || 0;
};

window.renderAdminStatementsData = function(statements) {
    allStatementsData = statements || [];
    applyStatementFilters();
};

function applyStatementFilters() {
    const query = (document.getElementById('stmt-search-input')?.value || '').toLowerCase().trim();
    const bankVal = document.getElementById('stmt-bank-filter')?.value || 'all';

    const filtered = allStatementsData.filter(s => {
        const matchesSearch = !query || 
            (s.bank_name && s.bank_name.toLowerCase().includes(query)) || 
            (s.user_id && s.user_id.toLowerCase().includes(query)) ||
            (s.statement_period && s.statement_period.toLowerCase().includes(query));

        const matchesBank = (bankVal === 'all') ||
            (s.bank_name && s.bank_name.toLowerCase().includes(bankVal.toLowerCase()));

        return matchesSearch && matchesBank;
    });

    renderStatementsTable(filtered);
}

function renderStatementsTable(statements) {
    const tbody = document.getElementById('statements-table-body');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (!statements || statements.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color: var(--text-muted); padding: 24px;">No parsed statement logs found.</td></tr>`;
        return;
    }

    statements.forEach(stmt => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>${escapeHtml(stmt.bank_name)}</strong></td>
            <td>${escapeHtml(stmt.user_id)}</td>
            <td><span class="badge badge-role-admin">${stmt.total_transactions} txns</span></td>
            <td>${escapeHtml(stmt.statement_period)}</td>
            <td>${stmt.processing_time ? (typeof stmt.processing_time === 'number' ? stmt.processing_time.toFixed(2) : stmt.processing_time) : '0.00'}s</td>
            <td>${escapeHtml(stmt.upload_date)}</td>
        `;
        tbody.appendChild(tr);
    });
}

window.renderAdminLogsData = function(logs) {
    const tbody = document.getElementById('audit-table-body');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (!logs || logs.length === 0) {
        tbody.innerHTML = `<tr><td colspan="4" style="text-align:center; color: var(--text-muted); padding: 24px;">No security or audit events recorded.</td></tr>`;
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
};

window.onAdminActionComplete = function(actionType, success, message) {
    if (message) showToast(message);
    if (actionType === 'add_user') closeModal('modal-add-user');
    if (actionType === 'edit_user') closeModal('modal-edit-user');
    if (actionType === 'reset_pwd') closeModal('modal-reset-pwd');
    
    if (typeof sendAppCommand === 'function') {
        sendAppCommand('get_admin_data', '');
    }
};

function initAdminPanel() {
    if (typeof sendAppCommand === 'function') {
        sendAppCommand('get_admin_data', '');
    }

    loadSystemStats();
    loadUsers();
    loadStatements();
    loadAuditLogs();

    if (isInitialized) return;
    isInitialized = true;

    // Tab Switching
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const targetId = btn.getAttribute('data-tab');
            if (targetId) switchTab(targetId);
        });
    });

    // Search and Filter Listeners
    const userSearch = document.getElementById('user-search-input');
    const roleFilter = document.getElementById('user-role-filter');
    const statusFilter = document.getElementById('user-status-filter');

    if (userSearch) userSearch.addEventListener('input', applyUserFilters);
    if (roleFilter) roleFilter.addEventListener('change', applyUserFilters);
    if (statusFilter) statusFilter.addEventListener('change', applyUserFilters);

    const stmtSearch = document.getElementById('stmt-search-input');
    const bankFilter = document.getElementById('stmt-bank-filter');

    if (stmtSearch) stmtSearch.addEventListener('input', applyStatementFilters);
    if (bankFilter) bankFilter.addEventListener('change', applyStatementFilters);
}

function applyUserFilters() {
    const query = (document.getElementById('user-search-input')?.value || '').toLowerCase().trim();
    const roleVal = document.getElementById('user-role-filter')?.value || 'all';
    const statusVal = document.getElementById('user-status-filter')?.value || 'all';

    const filtered = allUsersData.filter(u => {
        const matchesSearch = !query || 
            (u.name && u.name.toLowerCase().includes(query)) || 
            (u.email && u.email.toLowerCase().includes(query)) ||
            (u.username && u.username.toLowerCase().includes(query));

        const isUserAdmin = (u.role === 'admin' || u.role === 'Administrator');
        const matchesRole = (roleVal === 'all') ||
            (roleVal === 'admin' && isUserAdmin) ||
            (roleVal === 'user' && !isUserAdmin);

        const isActive = (u.status === 'active');
        const matchesStatus = (statusVal === 'all') ||
            (statusVal === 'active' && isActive) ||
            (statusVal === 'disabled' && !isActive);

        return matchesSearch && matchesRole && matchesStatus;
    });

    renderUsersTable(filtered);
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
let statsRetryCount = 0;
function loadSystemStats() {
    const bridge = getBridge();
    if (!bridge || typeof bridge.getAdminStats !== 'function') {
        if (statsRetryCount < 20) {
            statsRetryCount++;
            setTimeout(loadSystemStats, 200);
        }
        return;
    }
    statsRetryCount = 0;
    bridge.getAdminStats((stats) => {
        if (stats) {
            const totalUsersEl = document.getElementById('stat-total-users');
            const activeUsersEl = document.getElementById('stat-active-users');
            const totalStatementsEl = document.getElementById('stat-total-statements');
            const totalTxnsEl = document.getElementById('stat-total-txns');

            if (totalUsersEl) totalUsersEl.textContent = stats.total_users || 0;
            if (activeUsersEl) activeUsersEl.textContent = stats.active_users || 0;
            if (totalStatementsEl) totalStatementsEl.textContent = stats.total_statements || 0;
            if (totalTxnsEl) totalTxnsEl.textContent = stats.total_transactions || 0;
        }
    });
}

// 2. Load Users
let usersRetryCount = 0;
function loadUsers() {
    const bridge = getBridge();
    if (!bridge || typeof bridge.getAdminUsers !== 'function') {
        if (usersRetryCount < 20) {
            usersRetryCount++;
            setTimeout(loadUsers, 200);
        }
        return;
    }
    usersRetryCount = 0;
    bridge.getAdminUsers((users) => {
        allUsersData = users || [];
        applyUserFilters();
    });
}

function renderUsersTable(users) {
    const tbody = document.getElementById('users-table-body');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (!users || users.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; color: var(--text-muted); padding: 24px;">No registered user accounts found.</td></tr>`;
        return;
    }

    users.forEach(user => {
        const tr = document.createElement('tr');
        
        const isUserAdmin = (user.role === 'admin' || user.role === 'Administrator');
        const isActive = (user.status === 'active');
        const createdDate = user.created_at ? user.created_at.split('T')[0] : 'N/A';
        const lastLoginDate = user.last_login ? user.last_login.replace('T', ' ').split('.')[0] : 'Never';

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
            <td style="font-size:12px; color:var(--text-muted);">${createdDate}</td>
            <td style="font-size:12px; color:var(--text-muted);">${lastLoginDate}</td>
            <td>
                <div class="action-btn-group">
                    <button class="btn-sm" onclick="openEditUserModal('${user.email}')" title="Edit Profile">Edit</button>
                    <button class="btn-sm" onclick="openResetPwdModal('${user.email}')" title="Reset Password">Reset Pwd</button>
                    <button class="btn-sm" onclick="toggleUserRole('${user.email}', '${isUserAdmin ? 'user' : 'admin'}')">
                        ${isUserAdmin ? 'Demote' : 'Promote'}
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

// 3. User Modals & Actions
function openAddUserModal() {
    document.getElementById('form-add-user')?.reset();
    const modal = document.getElementById('modal-add-user');
    if (modal) modal.style.display = 'flex';
}

function openEditUserModal(email) {
    const user = allUsersData.find(u => u.email.toLowerCase() === email.toLowerCase());
    if (!user) return;

    document.getElementById('edit-user-email').value = user.email;
    document.getElementById('edit-user-email-display').value = user.email;
    document.getElementById('edit-user-name').value = user.name;
    document.getElementById('edit-user-phone').value = user.phone || '';
    document.getElementById('edit-user-role').value = (user.role === 'admin' || user.role === 'Administrator') ? 'admin' : 'user';
    document.getElementById('edit-user-status').value = user.status || 'active';

    const modal = document.getElementById('modal-edit-user');
    if (modal) modal.style.display = 'flex';
}

function openResetPwdModal(email) {
    document.getElementById('form-reset-pwd')?.reset();
    document.getElementById('reset-pwd-email').value = email;
    document.getElementById('reset-pwd-email-display').value = email;
    const modal = document.getElementById('modal-reset-pwd');
    if (modal) modal.style.display = 'flex';
}

function closeModal(modalId) {
    const el = document.getElementById(modalId);
    if (el) el.style.display = 'none';
}

function submitAddUser(e) {
    e.preventDefault();
    const name = document.getElementById('add-user-name').value.trim();
    const email = document.getElementById('add-user-email').value.trim();
    const phone = document.getElementById('add-user-phone').value.trim();
    const password = document.getElementById('add-user-password').value;
    const role = document.getElementById('add-user-role').value;
    const status = document.getElementById('add-user-status').value;

    const payload = { name, email, phone, password, role, status };
    const bridge = getBridge();
    if (bridge && typeof bridge.createAdminUser === 'function') {
        bridge.createAdminUser(name, email, phone, password, role, status, (res) => {
            if (res && res.success) {
                showToast(res.message);
                closeModal('modal-add-user');
                sendAppCommand('get_admin_data', '');
            } else {
                showToast(res ? res.message : 'Failed to create user account.');
            }
        });
    } else if (typeof sendAppCommand === 'function') {
        sendAppCommand('create_admin_user', payload);
    }
}

function submitEditUser(e) {
    e.preventDefault();
    const email = document.getElementById('edit-user-email').value;
    const name = document.getElementById('edit-user-name').value.trim();
    const phone = document.getElementById('edit-user-phone').value.trim();
    const role = document.getElementById('edit-user-role').value;
    const status = document.getElementById('edit-user-status').value;

    const payload = { email, name, phone, role, status };
    const bridge = getBridge();
    if (bridge && typeof bridge.updateAdminUser === 'function') {
        bridge.updateAdminUser(email, name, phone, role, status, (res) => {
            if (res && res.success) {
                showToast(res.message);
                closeModal('modal-edit-user');
                sendAppCommand('get_admin_data', '');
            } else {
                showToast(res ? res.message : 'Failed to update user details.');
            }
        });
    } else if (typeof sendAppCommand === 'function') {
        sendAppCommand('update_admin_user', payload);
    }
}

function submitResetPassword(e) {
    e.preventDefault();
    const email = document.getElementById('reset-pwd-email').value;
    const newPassword = document.getElementById('reset-pwd-new').value;

    const payload = { email, new_password: newPassword };
    const bridge = getBridge();
    if (bridge && typeof bridge.resetAdminUserPassword === 'function') {
        bridge.resetAdminUserPassword(email, newPassword, (res) => {
            if (res && res.success) {
                showToast(res.message);
                closeModal('modal-reset-pwd');
            } else {
                showToast(res ? res.message : 'Failed to reset password.');
            }
        });
    } else if (typeof sendAppCommand === 'function') {
        sendAppCommand('reset_admin_password', payload);
    }
}

function toggleUserRole(email, newRole) {
    const payload = { email, role: newRole };
    const bridge = getBridge();
    if (bridge && typeof bridge.updateUserRole === 'function') {
        bridge.updateUserRole(email, newRole, (res) => {
            if (res && res.success) {
                showToast(res.message);
                sendAppCommand('get_admin_data', '');
            } else {
                showToast(res ? res.message : 'Failed to update user role.');
            }
        });
    } else if (typeof sendAppCommand === 'function') {
        sendAppCommand('update_user_role', payload);
    }
}

function toggleUserStatus(email, newStatus) {
    const payload = { email, status: newStatus };
    const bridge = getBridge();
    if (bridge && typeof bridge.updateUserStatus === 'function') {
        bridge.updateUserStatus(email, newStatus, (res) => {
            if (res && res.success) {
                showToast(res.message);
                sendAppCommand('get_admin_data', '');
            } else {
                showToast(res ? res.message : 'Failed to update user status.');
            }
        });
    } else if (typeof sendAppCommand === 'function') {
        sendAppCommand('update_user_status', payload);
    }
}

function deleteUser(email) {
    if (!confirm(`Are you sure you want to delete account ${email}? This action cannot be undone.`)) {
        return;
    }
    const payload = { email };
    const bridge = getBridge();
    if (bridge && typeof bridge.deleteUserAccount === 'function') {
        bridge.deleteUserAccount(email, (res) => {
            if (res && res.success) {
                showToast(res.message);
                sendAppCommand('get_admin_data', '');
            } else {
                showToast(res ? res.message : 'Failed to delete user.');
            }
        });
    } else if (typeof sendAppCommand === 'function') {
        sendAppCommand('delete_user_account', payload);
    }
}

// 4. Statements Audit
let stmtRetryCount = 0;
function loadStatements() {
    const bridge = getBridge();
    if (!bridge || typeof bridge.getAdminStatements !== 'function') {
        if (stmtRetryCount < 20) {
            stmtRetryCount++;
            setTimeout(loadStatements, 200);
        }
        return;
    }
    stmtRetryCount = 0;
    bridge.getAdminStatements((statements) => {
        allStatementsData = statements || [];
        const tbody = document.getElementById('statements-table-body');
        if (!tbody) return;
        tbody.innerHTML = '';

        if (!statements || statements.length === 0) {
            tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color: var(--text-muted); padding: 24px;">No parsed statement logs found.</td></tr>`;
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
let logRetryCount = 0;
function loadAuditLogs() {
    const bridge = getBridge();
    if (!bridge || typeof bridge.getAdminAuditLogs !== 'function') {
        if (logRetryCount < 20) {
            logRetryCount++;
            setTimeout(loadAuditLogs, 200);
        }
        return;
    }
    logRetryCount = 0;
    bridge.getAdminAuditLogs((logs) => {
        const tbody = document.getElementById('audit-table-body');
        if (!tbody) return;
        tbody.innerHTML = '';

        if (!logs || logs.length === 0) {
            tbody.innerHTML = `<tr><td colspan="4" style="text-align:center; color: var(--text-muted); padding: 24px;">No security or audit events recorded.</td></tr>`;
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
