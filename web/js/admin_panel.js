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

        if (titleEl) titleEl.textContent = 'Activity Logs';
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
    const bankVal = (document.getElementById('stmt-bank-filter')?.value || 'all').toLowerCase().trim();

    const filtered = allStatementsData.filter(s => {
        const bankName = (s.bank_name || '').toLowerCase();
        const userId = (s.user_id || '').toLowerCase();
        const period = (s.statement_period || '').toLowerCase();

        const matchesSearch = !query || 
            bankName.includes(query) || 
            userId.includes(query) ||
            period.includes(query);

        let matchesBank = (bankVal === 'all');
        if (!matchesBank) {
            if (bankVal === 'hdfc' && bankName.includes('hdfc')) matchesBank = true;
            else if (bankVal === 'icici' && bankName.includes('icici')) matchesBank = true;
            else if (bankVal === 'sbi' && (bankName.includes('sbi') || bankName.includes('state bank'))) matchesBank = true;
            else if (bankVal === 'axis' && bankName.includes('axis')) matchesBank = true;
            else if (bankVal === 'kotak' && bankName.includes('kotak')) matchesBank = true;
            else if (bankName.includes(bankVal)) matchesBank = true;
        }

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

let allAuditLogsData = [];

window.renderAdminLogsData = function(logs) {
    allAuditLogsData = logs || [];
    applyLogFilters();
};

function applyLogFilters() {
    const query = (document.getElementById('log-search-input')?.value || '').toLowerCase().trim();
    const actionVal = (document.getElementById('log-action-filter')?.value || 'all').toLowerCase().trim();

    const filtered = allAuditLogsData.filter(l => {
        const userStr = (l.user || '').toLowerCase();
        const actionStr = (l.action || '').toLowerCase();
        const detailsStr = (l.details || '').toLowerCase();

        const matchesSearch = !query || 
            userStr.includes(query) || 
            actionStr.includes(query) ||
            detailsStr.includes(query);

        let matchesAction = (actionVal === 'all');
        if (!matchesAction) {
            if (actionVal === 'login' && actionStr.includes('login')) matchesAction = true;
            else if (actionVal === 'password' && actionStr.includes('password')) matchesAction = true;
            else if (actionVal === 'role' && actionStr.includes('role')) matchesAction = true;
            else if (actionVal === 'status' && actionStr.includes('status')) matchesAction = true;
            else if (actionVal === 'create' && (actionStr.includes('create') || actionStr.includes('account created'))) matchesAction = true;
            else if (actionVal === 'delete' && (actionStr.includes('delete') || actionStr.includes('purge'))) matchesAction = true;
            else if (actionStr.includes(actionVal)) matchesAction = true;
        }

        return matchesSearch && matchesAction;
    });

    renderLogsTable(filtered);
}

function renderLogsTable(logs) {
    const tbody = document.getElementById('audit-table-body');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (!logs || logs.length === 0) {
        tbody.innerHTML = `<tr><td colspan="4" style="text-align:center; color: var(--text-muted); padding: 24px;">No security or audit events recorded.</td></tr>`;
        return;
    }

    logs.forEach(log => {
        const tr = document.createElement('tr');
        const actionStr = (log.action || 'Event').toLowerCase();
        let badgeClass = 'badge-role-user';
        if (actionStr.includes('login') || actionStr.includes('create')) {
            badgeClass = 'badge-status-active';
        } else if (actionStr.includes('password') || actionStr.includes('role') || actionStr.includes('status') || actionStr.includes('profile')) {
            badgeClass = 'badge-role-admin';
        } else if (actionStr.includes('delete') || actionStr.includes('disable')) {
            badgeClass = 'badge-status-disabled';
        }

        const cleanTs = log.timestamp ? String(log.timestamp).replace('T', ' ').split('.')[0] : 'N/A';

        tr.innerHTML = `
            <td style="font-size:12px; color:var(--text-muted);">${escapeHtml(cleanTs)}</td>
            <td><strong>${escapeHtml(log.user)}</strong></td>
            <td><span class="badge ${badgeClass}">${escapeHtml(log.action)}</span></td>
            <td>${escapeHtml(log.details)}</td>
        `;
        tbody.appendChild(tr);
    });
}

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

    const logSearch = document.getElementById('log-search-input');
    const actionFilter = document.getElementById('log-action-filter');

    if (logSearch) logSearch.addEventListener('input', applyLogFilters);
    if (actionFilter) actionFilter.addEventListener('change', applyLogFilters);
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

let toastTimeout = null;

function showToast(msg) {
    const toast = document.getElementById('toast-notification');
    if (toast) {
        toast.textContent = msg;
        toast.style.display = 'block';
        if (toastTimeout) {
            clearTimeout(toastTimeout);
        }
        toastTimeout = setTimeout(() => {
            toast.style.display = 'none';
        }, 5000);
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

    const newUser = {
        id: email,
        name: name,
        email: email,
        phone: phone,
        username: email.split('@')[0],
        role: role,
        status: status,
        created_at: new Date().toISOString().split('T')[0],
        last_login: 'Never'
    };
    allUsersData.unshift(newUser);
    applyUserFilters();
    closeModal('modal-add-user');
    showToast(`User account ${email} created successfully.`);

    const payload = { name, email, phone, password, role, status };
    const bridge = getBridge();
    if (bridge && typeof bridge.createAdminUser === 'function') {
        bridge.createAdminUser(name, email, phone, password, role, status, (res) => {
            if (res && res.message) {
                showToast(res.message);
            }
            sendAppCommand('get_admin_data', '');
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

    const targetUser = allUsersData.find(u => u.email.toLowerCase() === email.toLowerCase());
    if (targetUser) {
        targetUser.name = name;
        targetUser.phone = phone;
        targetUser.role = role;
        targetUser.status = status;
        applyUserFilters();
    }
    closeModal('modal-edit-user');
    showToast(`User details for ${email} updated successfully.`);

    const payload = { email, name, phone, role, status };
    const bridge = getBridge();
    if (bridge && typeof bridge.updateAdminUser === 'function') {
        bridge.updateAdminUser(email, name, phone, role, status, (res) => {
            if (res && res.message) {
                showToast(res.message);
            }
            sendAppCommand('get_admin_data', '');
        });
    } else if (typeof sendAppCommand === 'function') {
        sendAppCommand('update_admin_user', payload);
    }
}

function submitResetPassword(e) {
    e.preventDefault();
    const email = document.getElementById('reset-pwd-email').value;
    const newPassword = document.getElementById('reset-pwd-new').value;

    closeModal('modal-reset-pwd');
    showToast(`Password for ${email} reset successfully.`);

    const payload = { email, new_password: newPassword };
    const bridge = getBridge();
    if (bridge && typeof bridge.resetAdminUserPassword === 'function') {
        bridge.resetAdminUserPassword(email, newPassword, (res) => {
            if (res && res.message) {
                showToast(res.message);
            }
            sendAppCommand('get_admin_data', '');
        });
    } else if (typeof sendAppCommand === 'function') {
        sendAppCommand('reset_admin_password', payload);
    }
}

function toggleUserRole(email, newRole) {
    const cleanEmail = (email || '').trim().toLowerCase();
    const targetUser = allUsersData.find(u => (u.email || '').trim().toLowerCase() === cleanEmail);
    if (targetUser) {
        targetUser.role = newRole;
        applyUserFilters();
    }
    const roleLabel = (newRole === 'admin' || newRole === 'Administrator') ? 'Administrator' : 'User';
    showToast(`User role for ${email} updated to ${roleLabel}.`);

    const payload = { email, role: newRole };
    const bridge = getBridge();
    if (bridge && typeof bridge.updateUserRole === 'function') {
        bridge.updateUserRole(email, newRole, (res) => {
            if (res && res.message) {
                showToast(res.message);
            }
            sendAppCommand('get_admin_data', '');
        });
    } else if (typeof sendAppCommand === 'function') {
        sendAppCommand('update_user_role', payload);
    }
}

function toggleUserStatus(email, newStatus) {
    const cleanEmail = (email || '').trim().toLowerCase();
    const targetUser = allUsersData.find(u => (u.email || '').trim().toLowerCase() === cleanEmail);
    if (targetUser) {
        targetUser.status = newStatus;
        applyUserFilters();
    }
    const statusLabel = newStatus === 'active' ? 'Active' : 'Disabled';
    showToast(`User status for ${email} updated to ${statusLabel}.`);

    const payload = { email, status: newStatus };
    const bridge = getBridge();
    if (bridge && typeof bridge.updateUserStatus === 'function') {
        bridge.updateUserStatus(email, newStatus, (res) => {
            if (res && res.message) {
                showToast(res.message);
            }
            sendAppCommand('get_admin_data', '');
        });
    } else if (typeof sendAppCommand === 'function') {
        sendAppCommand('update_user_status', payload);
    }
}

function deleteUser(email) {
    if (!confirm(`Are you sure you want to delete account ${email}? This action cannot be undone.`)) {
        return;
    }
    const cleanEmail = (email || '').trim().toLowerCase();
    allUsersData = allUsersData.filter(u => (u.email || '').trim().toLowerCase() !== cleanEmail);
    applyUserFilters();
    showToast(`User account ${email} deleted successfully.`);

    const payload = { email };
    const bridge = getBridge();
    if (bridge && typeof bridge.deleteUserAccount === 'function') {
        bridge.deleteUserAccount(email, (res) => {
            if (res && res.message) {
                showToast(res.message);
            }
            sendAppCommand('get_admin_data', '');
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
