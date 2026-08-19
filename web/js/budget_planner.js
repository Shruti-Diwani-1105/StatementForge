/**
 * Monthly Salary & Budget Planner - Frontend Controller (JavaScript)
 * Manages form calculations, dynamic month switching, pure HTML5 Canvas graphs,
 * and IPC bridge communications with Python BudgetService.
 */

let currentBudgetSummary = null;

document.addEventListener('DOMContentLoaded', () => {
    requestBudgetSummary();
    window.addEventListener('resize', () => {
        if (currentBudgetSummary) renderCharts(currentBudgetSummary);
    });
});

function requestBudgetSummary() {
    const monthSelect = document.getElementById('selectMonth');
    const monthKey = (monthSelect && monthSelect.value) ? monthSelect.value : getSelectedMonthKey();
    if (typeof sendAppCommand === 'function') {
        sendAppCommand('budget_get', monthKey);
    }
}

function getSelectedMonthKey() {
    const el = document.getElementById('selectMonth');
    if (el && el.value) return el.value;
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    return `${year}-${month}`;
}

function onMonthChanged() {
    requestBudgetSummary();
}

function createNextMonthBudget() {
    const monthKey = getSelectedMonthKey();
    if (typeof sendAppCommand === 'function') {
        sendAppCommand('budget_create_next_month', monthKey);
    }
}

/**
 * Populates the month selector dropdown dynamically with user's registered months.
 */
function renderAvailableMonths(monthsList, activeMonthKey) {
    const select = document.getElementById('selectMonth');
    if (!select) return;

    select.innerHTML = '';
    const monthNames = ["January", "February", "March", "April", "May", "June", 
                        "July", "August", "September", "October", "November", "December"];

    if (!monthsList || monthsList.length === 0) {
        monthsList = [activeMonthKey || getSelectedMonthKey()];
    }

    monthsList.forEach(mKey => {
        const parts = mKey.split('-');
        let label = mKey;
        if (parts.length === 2) {
            const yr = parts[0];
            const mIdx = parseInt(parts[1], 10) - 1;
            if (mIdx >= 0 && mIdx < 12) {
                label = `${monthNames[mIdx]} ${yr}`;
            }
        }

        const opt = document.createElement('option');
        opt.value = mKey;
        opt.textContent = label;
        if (mKey === activeMonthKey) {
            opt.selected = true;
        }
        select.appendChild(opt);
    });
}

/**
 * Invoked from Python to populate all budget fields, comparison tables, metrics, and charts.
 */
function renderBudgetSummaryData(data) {
    if (typeof data === 'string') {
        try {
            data = JSON.parse(data);
        } catch (e) {
            console.error('Error parsing budget JSON:', e);
            return;
        }
    }
    currentBudgetSummary = data;

    // 1. Lock state & Banner
    const lockPill = document.getElementById('lockPill');
    const btnToggleEdit = document.getElementById('btnToggleEdit');
    const isLocked = data.is_locked;
    
    if (lockPill) {
        if (isLocked) {
            lockPill.className = 'bp-lock-pill locked';
            lockPill.innerHTML = '🔒 Monthly Budget Locked';
            if (btnToggleEdit) btnToggleEdit.textContent = 'Edit Budget';
        } else {
            lockPill.className = 'bp-lock-pill unlocked';
            lockPill.innerHTML = '🟢 Planning Window Active (1st–7th)';
            if (btnToggleEdit) btnToggleEdit.textContent = data.manual_unlocked ? 'Lock Budget' : 'Edit Budget';
        }
    }

    // Toggle form disabled state based on lock status
    toggleFormDisabledState(isLocked);

    // 2. Metrics Header Cards
    setElementText('valIncome', `₹${formatNumber(data.total_income)}`);
    setElementText('valPlanned', `₹${formatNumber(data.total_planned_expenses)}`);
    setElementText('valActual', `₹${formatNumber(data.total_actual_expenses)}`);
    setElementText('valSavings', `₹${formatNumber(data.planned_savings)}`);
    setElementText('valRemaining', `₹${formatNumber(data.remaining_monthly_budget)}`);

    // 3. Summary Alert Banner
    const alertBanner = document.getElementById('summaryAlertBanner');
    if (alertBanner) {
        alertBanner.textContent = data.summary_alert;
        if (data.total_actual_expenses > data.total_planned_expenses) {
            alertBanner.className = 'bp-summary-alert-banner alert-danger';
        } else {
            alertBanner.className = 'bp-summary-alert-banner alert-success';
        }
    }

    // 4. Populate Forms
    // Income
    const inc = data.income || {};
    setInputValue('inputSalary', inc.salary || 0);
    setInputValue('inputOtherIncome', inc.other || 0);
    setElementText('txtTotalIncome', `₹${formatNumber(data.total_income)}`);

    // Savings
    setInputValue('inputSavings', data.planned_savings || 0);

    // Fixed Expenses Table
    renderFixedExpensesTable(data.fixed_expenses || []);
    setElementText('txtTotalFixed', `₹${formatNumber(data.total_fixed)}`);

    // Family Payments Table
    renderFamilyPaymentsTable(data.family_payments || []);
    setElementText('txtTotalFamily', `₹${formatNumber(data.total_family)}`);

    // Category Budgets Form
    renderCategoryBudgetsInputs(data.category_budgets || []);

    // Actual Expenses Table (without Date column)
    renderActualExpensesTable(data.actual_expenses || []);

    // 5. Planned vs Actual Comparison Table
    renderComparisonTable(data.comparison || [], data.total_actual_expenses, data.total_planned_expenses);

    // 6. Performance Score Box
    setElementText('scoreNum', data.performance_score);
    renderScoreBreakdown(data.good_points || [], data.attention_points || []);

    // 7. Update Pure HTML5 Canvas Charts (Step 11)
    renderCharts(data);
}

function setElementText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
}

function setInputValue(id, val) {
    const el = document.getElementById(id);
    if (el) el.value = val;
}

function formatNumber(num) {
    if (isNaN(num)) return '0';
    return Number(num).toLocaleString('en-IN', { maximumFractionDigits: 0 });
}

function toggleFormDisabledState(disabled) {
    const inputs = document.querySelectorAll('.bp-input-editable');
    inputs.forEach(inp => {
        inp.disabled = disabled;
    });
}

function toggleEditBudget() {
    if (!currentBudgetSummary) return;
    const currentUnlocked = currentBudgetSummary.manual_unlocked;
    const newUnlocked = !currentUnlocked;
    if (typeof sendAppCommand === 'function') {
        sendAppCommand('budget_lock_toggle', JSON.stringify({
            month_key: currentBudgetSummary.month_key,
            unlocked: newUnlocked
        }));
    }
}

/* Dynamic Table Renderers */

function renderFixedExpensesTable(items) {
    const tbody = document.getElementById('tbodyFixedExpenses');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (items.length === 0) {
        tbody.innerHTML = '<tr><td colspan="3" style="text-align:center;color:var(--bp-text-muted);">No fixed expenses added yet.</td></tr>';
        return;
    }

    items.forEach(item => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>${escapeHtml(item.name)}</strong></td>
            <td>₹${formatNumber(item.amount)}</td>
            <td style="text-align:right;">
                <button type="button" class="bp-btn-icon" onclick="removeFixedExpense('${item.id}')" title="Delete">✕</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function renderFamilyPaymentsTable(items) {
    const tbody = document.getElementById('tbodyFamilyPayments');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (items.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:var(--bp-text-muted);">No family payments recorded.</td></tr>';
        return;
    }

    items.forEach(item => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>${escapeHtml(item.member)}</strong></td>
            <td>₹${formatNumber(item.amount)}</td>
            <td>${escapeHtml(item.reason || '-')}</td>
            <td style="text-align:right;">
                <button type="button" class="bp-btn-icon" onclick="removeFamilyPayment('${item.id}')" title="Delete">✕</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function renderCategoryBudgetsInputs(catList) {
    const container = document.getElementById('categoryBudgetsGrid');
    if (!container) return;
    container.innerHTML = '';

    catList.forEach(cb => {
        const div = document.createElement('div');
        div.className = 'bp-field-group';
        div.innerHTML = `
            <label class="bp-field-label">${escapeHtml(cb.category)}</label>
            <input type="number" class="bp-input-text bp-input-editable input-cat-budget" data-category="${escapeHtml(cb.category)}" value="${cb.planned}" onchange="onBudgetFormChanged()">
        `;
        container.appendChild(div);
    });
}

function renderActualExpensesTable(expList) {
    const tbody = document.getElementById('tbodyActualExpenses');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (expList.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:var(--bp-text-muted);">No actual expenses recorded for this month.</td></tr>';
        return;
    }

    expList.forEach(exp => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><span class="bp-badge badge-under">${escapeHtml(exp.category)}</span></td>
            <td><strong>₹${formatNumber(exp.amount)}</strong></td>
            <td>${escapeHtml(exp.description || '-')}</td>
            <td style="text-align:right;">
                <button type="button" class="bp-btn-icon" onclick="deleteActualExpense('${exp.id}')" title="Delete">✕</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function renderComparisonTable(compList, totalActual, totalPlanned) {
    const tbody = document.getElementById('tbodyComparison');
    if (!tbody) return;
    tbody.innerHTML = '';

    compList.forEach(item => {
        const tr = document.createElement('tr');
        let badgeClass = 'badge-under';
        if (item.status === 'over') badgeClass = 'badge-over';
        else if (item.status === 'warning') badgeClass = 'badge-warning';

        tr.innerHTML = `
            <td><strong>${escapeHtml(item.category)}</strong></td>
            <td>₹${formatNumber(item.planned)}</td>
            <td>₹${formatNumber(item.actual)}</td>
            <td><span class="bp-badge ${badgeClass}">${item.result}</span></td>
            <td><small style="color:var(--bp-text-muted);">${item.warning}</small></td>
        `;
        tbody.appendChild(tr);
    });

    const footerTr = document.createElement('tr');
    footerTr.style.fontWeight = 'bold';
    footerTr.style.backgroundColor = 'var(--bp-border-subtle)';
    footerTr.innerHTML = `
        <td>Total Category Expenses</td>
        <td>₹${formatNumber(totalPlanned)}</td>
        <td>₹${formatNumber(totalActual)}</td>
        <td colspan="2">${totalActual > totalPlanned ? '<span class="bp-badge badge-over">🔴 Over Budget</span>' : '<span class="bp-badge badge-under">🟢 Under Budget</span>'}</td>
    `;
    tbody.appendChild(footerTr);
}

function renderScoreBreakdown(goodList, attentionList) {
    const container = document.getElementById('scoreBreakdownList');
    if (!container) return;
    container.innerHTML = '';

    let html = '<ul>';
    goodList.forEach(item => {
        html += `<li style="color:var(--bp-success);">${escapeHtml(item)}</li>`;
    });
    attentionList.forEach(item => {
        html += `<li style="color:var(--bp-danger);">${escapeHtml(item)}</li>`;
    });
    html += '</ul>';
    container.innerHTML = html;
}

/* User Form Actions */

function addFixedExpense() {
    const nameInp = document.getElementById('inputFixName');
    const amtInp = document.getElementById('inputFixAmount');
    if (!nameInp || !amtInp) return;

    const name = nameInp.value.trim();
    const amt = parseFloat(amtInp.value);
    if (!name || isNaN(amt) || amt <= 0) {
        alert('Please enter a valid expense name and amount.');
        return;
    }

    if (!currentBudgetSummary) return;
    const raw = currentBudgetSummary.raw_data;
    raw.fixed_expenses.push({
        id: 'fix_' + Date.now(),
        name: name,
        amount: amt
    });

    nameInp.value = '';
    amtInp.value = '';

    saveCurrentBudgetState(raw);
}

function removeFixedExpense(id) {
    if (!currentBudgetSummary) return;
    const raw = currentBudgetSummary.raw_data;
    raw.fixed_expenses = raw.fixed_expenses.filter(e => e.id !== id);
    saveCurrentBudgetState(raw);
}

function addFamilyPayment() {
    const memInp = document.getElementById('inputFamMember');
    const amtInp = document.getElementById('inputFamAmount');
    const reasonInp = document.getElementById('inputFamReason');
    if (!memInp || !amtInp) return;

    const member = memInp.value.trim();
    const amt = parseFloat(amtInp.value);
    const reason = reasonInp ? reasonInp.value.trim() : '';

    if (!member || isNaN(amt) || amt <= 0) {
        alert('Please enter a valid family member name and amount.');
        return;
    }

    if (!currentBudgetSummary) return;
    const raw = currentBudgetSummary.raw_data;
    raw.family_payments.push({
        id: 'fam_' + Date.now(),
        member: member,
        amount: amt,
        reason: reason
    });

    memInp.value = '';
    amtInp.value = '';
    if (reasonInp) reasonInp.value = '';

    saveCurrentBudgetState(raw);
}

function removeFamilyPayment(id) {
    if (!currentBudgetSummary) return;
    const raw = currentBudgetSummary.raw_data;
    raw.family_payments = raw.family_payments.filter(e => e.id !== id);
    saveCurrentBudgetState(raw);
}

function addActualExpense() {
    const catInp = document.getElementById('selectExpCategory');
    const amtInp = document.getElementById('inputExpAmount');
    const descInp = document.getElementById('inputExpDesc');

    if (!amtInp || !catInp) return;

    const category = catInp.value;
    const amt = parseFloat(amtInp.value);
    const desc = descInp ? descInp.value.trim() : '';

    if (isNaN(amt) || amt <= 0) {
        alert('Please enter a valid expense amount.');
        return;
    }

    const payload = {
        month_key: getSelectedMonthKey(),
        expense: {
            category: category,
            amount: amt,
            description: desc
        }
    };

    if (typeof sendAppCommand === 'function') {
        sendAppCommand('budget_add_expense', JSON.stringify(payload));
    }

    amtInp.value = '';
    if (descInp) descInp.value = '';
}

function deleteActualExpense(id) {
    const payload = {
        month_key: getSelectedMonthKey(),
        expense_id: id
    };
    if (typeof sendAppCommand === 'function') {
        sendAppCommand('budget_delete_expense', JSON.stringify(payload));
    }
}

function onBudgetFormChanged() {
    if (!currentBudgetSummary) return;
    const raw = currentBudgetSummary.raw_data;

    // Gather income (Salary + Other Income)
    raw.income = {
        salary: parseFloat(document.getElementById('inputSalary').value) || 0,
        other: parseFloat(document.getElementById('inputOtherIncome').value) || 0
    };

    // Gather savings
    raw.savings = parseFloat(document.getElementById('inputSavings').value) || 0;

    // Gather category budgets
    const catInputs = document.querySelectorAll('.input-cat-budget');
    const newCatBudgets = [];
    catInputs.forEach(inp => {
        newCatBudgets.push({
            category: inp.getAttribute('data-category'),
            planned: parseFloat(inp.value) || 0
        });
    });
    raw.category_budgets = newCatBudgets;

    saveCurrentBudgetState(raw);
}

function saveCurrentBudgetState(rawDoc) {
    if (typeof sendAppCommand === 'function') {
        sendAppCommand('budget_save', JSON.stringify({
            month_key: getSelectedMonthKey(),
            budget: rawDoc
        }));
    }
}

function generateAISummary() {
    const aiContainer = document.getElementById('aiSummaryContent');
    if (aiContainer) {
        aiContainer.innerHTML = '<div style="text-align:center;padding:20px;color:var(--bp-text-muted);">🤖 Generating Gemini AI Financial Analysis... Please wait.</div>';
    }

    if (typeof sendAppCommand === 'function') {
        sendAppCommand('budget_ai_summary', getSelectedMonthKey());
    }
}

function displayAISummary(htmlContent) {
    const aiContainer = document.getElementById('aiSummaryContent');
    if (aiContainer) {
        aiContainer.innerHTML = htmlContent;
    }
}

/* ====================================================
 * STEP 11: PURE HTML5 CANVAS CHARTS (100% RELIABLE LOCAL RENDERER)
 * ==================================================== */

function renderCharts(data) {
    drawPlannedVsActualBarChart(data.comparison || []);
    drawExpenseDistributionDonutChart(data);
    drawSalaryBreakdownPieChart(data);
}

function prepareCanvas(canvasId) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return null;
    const parent = canvas.parentElement;
    if (!parent) return null;

    const width = parent.clientWidth || 320;
    const height = parent.clientHeight || 240;
    const dpr = window.devicePixelRatio || 1;

    canvas.width = width * dpr;
    canvas.height = height * dpr;
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;

    const ctx = canvas.getContext('2d');
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, width, height);

    const isDark = document.body.classList.contains('dark-mode');
    return { ctx, width, height, isDark };
}

/**
 * 1. Category Planned vs Actual Bar Chart
 */
function drawPlannedVsActualBarChart(comparisonList) {
    const setup = prepareCanvas('chartPlannedVsActualCanvas');
    if (!setup) return;
    const { ctx, width, height, isDark } = setup;

    const textColor = isDark ? '#f8fafc' : '#0f172a';
    const subColor = isDark ? '#94a3b8' : '#64748b';
    const gridColor = isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)';

    // Margins
    const margin = { top: 36, right: 16, bottom: 44, left: 46 };
    const chartWidth = width - margin.left - margin.right;
    const chartHeight = height - margin.top - margin.bottom;

    // Legend
    ctx.font = '600 11px sans-serif';
    ctx.fillStyle = textColor;
    // Legend item 1: Planned
    ctx.fillStyle = '#2563eb';
    ctx.fillRect(margin.left, 10, 12, 12);
    ctx.fillStyle = textColor;
    ctx.fillText('Planned (₹)', margin.left + 16, 20);

    // Legend item 2: Actual
    ctx.fillStyle = '#f59e0b';
    ctx.fillRect(margin.left + 110, 10, 12, 12);
    ctx.fillStyle = textColor;
    ctx.fillText('Actual (₹)', margin.left + 126, 20);

    if (!comparisonList || comparisonList.length === 0) {
        ctx.fillStyle = subColor;
        ctx.font = '12px sans-serif';
        ctx.fillText('No category data available.', width / 2 - 60, height / 2);
        return;
    }

    // Find max value for Y scaling
    let maxVal = 0;
    comparisonList.forEach(c => {
        if (c.planned > maxVal) maxVal = c.planned;
        if (c.actual > maxVal) maxVal = c.actual;
    });
    if (maxVal === 0) maxVal = 5000;
    maxVal = Math.ceil(maxVal * 1.15 / 1000) * 1000;

    // Draw Y grid lines
    const ticks = 4;
    ctx.textAlign = 'right';
    ctx.textBaseline = 'middle';
    ctx.font = '10px sans-serif';

    for (let i = 0; i <= ticks; i++) {
        const yVal = (maxVal / ticks) * i;
        const yPos = margin.top + chartHeight - (chartHeight * (i / ticks));

        ctx.fillStyle = subColor;
        ctx.fillText(`₹${formatCompactNumber(yVal)}`, margin.left - 6, yPos);

        ctx.beginPath();
        ctx.strokeStyle = gridColor;
        ctx.lineWidth = 1;
        ctx.moveTo(margin.left, yPos);
        ctx.lineTo(width - margin.right, yPos);
        ctx.stroke();
    }

    // Draw Bars
    const groupWidth = chartWidth / comparisonList.length;
    const barWidth = Math.min(18, (groupWidth - 8) / 2);

    comparisonList.forEach((c, idx) => {
        const groupX = margin.left + (idx * groupWidth) + (groupWidth / 2);

        // Bar 1: Planned (Blue)
        const pHeight = (c.planned / maxVal) * chartHeight;
        const pX = groupX - barWidth - 1;
        const pY = margin.top + chartHeight - pHeight;

        ctx.fillStyle = '#2563eb';
        ctx.beginPath();
        ctx.roundRect ? ctx.roundRect(pX, pY, barWidth, pHeight, [3, 3, 0, 0]) : ctx.fillRect(pX, pY, barWidth, pHeight);
        ctx.fill();

        // Bar 2: Actual (Amber)
        const aHeight = (c.actual / maxVal) * chartHeight;
        const aX = groupX + 1;
        const aY = margin.top + chartHeight - aHeight;

        ctx.fillStyle = '#f59e0b';
        ctx.beginPath();
        ctx.roundRect ? ctx.roundRect(aX, aY, barWidth, aHeight, [3, 3, 0, 0]) : ctx.fillRect(aX, aY, barWidth, aHeight);
        ctx.fill();

        // X Label
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';
        ctx.fillStyle = textColor;
        ctx.font = '500 10px sans-serif';
        let label = c.category;
        if (label.length > 7) label = label.substring(0, 6) + '..';
        ctx.fillText(label, groupX, margin.top + chartHeight + 6);
    });
}

/**
 * 2. Expense Distribution Donut Chart
 */
function drawExpenseDistributionDonutChart(data) {
    const setup = prepareCanvas('chartExpenseDistCanvas');
    if (!setup) return;
    const { ctx, width, height, isDark } = setup;

    const textColor = isDark ? '#f8fafc' : '#0f172a';
    const subColor = isDark ? '#94a3b8' : '#64748b';

    const items = [
        { label: 'Fixed Expenses', value: data.total_fixed, color: '#3b82f6' },
        { label: 'Family Payments', value: data.total_family, color: '#8b5cf6' }
    ];

    if (data.comparison) {
        const catColors = ['#10b981', '#f59e0b', '#ef4444', '#06b6d4', '#ec4899', '#6366f1', '#14b8a6'];
        data.comparison.forEach((c, i) => {
            if (c.actual > 0) {
                items.push({
                    label: c.category,
                    value: c.actual,
                    color: catColors[i % catColors.length]
                });
            }
        });
    }

    const total = items.reduce((sum, item) => sum + item.value, 0);

    if (total === 0) {
        ctx.fillStyle = subColor;
        ctx.font = '12px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('No actual expense data recorded yet.', width / 2, height / 2);
        return;
    }

    const centerX = width * 0.38;
    const centerY = height * 0.5;
    const outerRadius = Math.min(width, height) * 0.38;
    const innerRadius = outerRadius * 0.55;

    let startAngle = -Math.PI / 2;

    items.forEach(item => {
        const sliceAngle = (item.value / total) * (Math.PI * 2);
        const endAngle = startAngle + sliceAngle;

        ctx.beginPath();
        ctx.arc(centerX, centerY, outerRadius, startAngle, endAngle);
        ctx.arc(centerX, centerY, innerRadius, endAngle, startAngle, true);
        ctx.closePath();
        ctx.fillStyle = item.color;
        ctx.fill();

        startAngle = endAngle;
    });

    // Center Text
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillStyle = textColor;
    ctx.font = 'bold 12px sans-serif';
    ctx.fillText('Total Spent', centerX, centerY - 8);
    ctx.font = 'bold 13px sans-serif';
    ctx.fillStyle = '#0037b0';
    ctx.fillText(`₹${formatCompactNumber(total)}`, centerX, centerY + 10);

    // Legend List on Right Side
    const legendX = width * 0.70;
    let legendY = 24;
    ctx.textAlign = 'left';
    ctx.font = '10px sans-serif';

    items.slice(0, 7).forEach(item => {
        ctx.fillStyle = item.color;
        ctx.fillRect(legendX, legendY, 10, 10);
        ctx.fillStyle = textColor;
        let lText = item.label;
        if (lText.length > 10) lText = lText.substring(0, 9) + '..';
        ctx.fillText(`${lText} (₹${formatCompactNumber(item.value)})`, legendX + 14, legendY + 9);
        legendY += 18;
    });
}

/**
 * 3. Salary & Income Breakdown Pie Chart
 */
function drawSalaryBreakdownPieChart(data) {
    const setup = prepareCanvas('chartSalaryDistCanvas');
    if (!setup) return;
    const { ctx, width, height, isDark } = setup;

    const textColor = isDark ? '#f8fafc' : '#0f172a';
    const subColor = isDark ? '#94a3b8' : '#64748b';

    const fixed = data.total_fixed || 0;
    const family = data.total_family || 0;
    const savings = data.planned_savings || 0;
    const catSpend = (data.comparison || []).reduce((sum, c) => sum + c.actual, 0);
    const remaining = Math.max(0, data.remaining_monthly_budget || 0);

    const items = [
        { label: 'Fixed Expenses', value: fixed, color: '#3b82f6' },
        { label: 'Family Payments', value: family, color: '#8b5cf6' },
        { label: 'Planned Savings', value: savings, color: '#10b981' },
        { label: 'Category Spend', value: catSpend, color: '#f59e0b' },
        { label: 'Remaining Money', value: remaining, color: '#0037b0' }
    ].filter(i => i.value > 0);

    const total = items.reduce((sum, item) => sum + item.value, 0);

    if (total === 0) {
        ctx.fillStyle = subColor;
        ctx.font = '12px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('Enter monthly income & budget to view breakdown.', width / 2, height / 2);
        return;
    }

    const centerX = width * 0.36;
    const centerY = height * 0.5;
    const radius = Math.min(width, height) * 0.38;

    let startAngle = -Math.PI / 2;

    items.forEach(item => {
        const sliceAngle = (item.value / total) * (Math.PI * 2);
        const endAngle = startAngle + sliceAngle;

        ctx.beginPath();
        ctx.moveTo(centerX, centerY);
        ctx.arc(centerX, centerY, radius, startAngle, endAngle);
        ctx.closePath();
        ctx.fillStyle = item.color;
        ctx.fill();
        ctx.strokeStyle = isDark ? '#1e293b' : '#ffffff';
        ctx.lineWidth = 1.5;
        ctx.stroke();

        startAngle = endAngle;
    });

    // Legend List on Right Side
    const legendX = width * 0.68;
    let legendY = 24;
    ctx.textAlign = 'left';
    ctx.font = '10px sans-serif';

    items.forEach(item => {
        ctx.fillStyle = item.color;
        ctx.fillRect(legendX, legendY, 10, 10);
        ctx.fillStyle = textColor;
        ctx.fillText(`${item.label} (₹${formatCompactNumber(item.value)})`, legendX + 14, legendY + 9);
        legendY += 20;
    });
}

function formatCompactNumber(num) {
    if (isNaN(num)) return '0';
    if (num >= 100000) return (num / 100000).toFixed(1) + 'L';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'k';
    return num.toLocaleString();
}

function escapeHtml(text) {
    if (!text) return '';
    return String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
