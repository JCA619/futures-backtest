// Global App State
let currentTimeframe = 'hourly';
let currentSize = '0.0005';
let currentRr = '2.0';
let activeData = null;

// Table Pagination & Filter State
let currentPage = 1;
const rowsPerPage = 10;
let filteredTrades = [];

// Chart Instances (to destroy and recreate)
let equityChart = null;
let hourlyChart = null;
let sessionChart = null;

// DOM Elements
const tfSelect = document.getElementById('timeframe-select');
const sizeSelect = document.getElementById('size-select');
const rrSelect = document.getElementById('rr-select');

const statTotalTrades = document.getElementById('stat-total-trades');
const statWinRate = document.getElementById('stat-win-rate');
const statNetProfit = document.getElementById('stat-net-profit');
const statProfitFactor = document.getElementById('stat-profit-factor');
const statMaxDrawdown = document.getElementById('stat-max-drawdown');
const statAvgRatio = document.getElementById('stat-avg-ratio');

const bestSessionVal = document.getElementById('best-session-val');
const bestHourVal = document.getElementById('best-hour-val');

const searchInput = document.getElementById('table-search');
const filterDirection = document.getElementById('filter-direction');
const filterResult = document.getElementById('filter-result');
const tableBody = document.getElementById('trades-table-body');
const logCountLabel = document.getElementById('log-count');
const pageIndicator = document.getElementById('page-indicator');
const btnPrev = document.getElementById('btn-prev');
const btnNext = document.getElementById('btn-next');

// Initial Setup
document.addEventListener('DOMContentLoaded', () => {
    updateSizeOptions();
    loadDashboardData();
    setupEventListeners();
});

// Setup Sizes based on Timeframe
function updateSizeOptions() {
    sizeSelect.innerHTML = '';
    if (currentTimeframe === 'hourly') {
        const options = [
            { value: '0.0002', label: '0.02% of Close' },
            { value: '0.0005', label: '0.05% of Close (Default)' },
            { value: '0.0010', label: '0.10% of Close' }
        ];
        options.forEach(opt => {
            const el = document.createElement('option');
            el.value = opt.value;
            el.textContent = opt.label;
            if (opt.value === '0.0005') el.selected = true;
            sizeSelect.appendChild(el);
        });
        currentSize = '0.0005';
    } else {
        const options = [
            { value: '0.001', label: '0.10% of Close' },
            { value: '0.003', label: '0.30% of Close (Default)' },
            { value: '0.005', label: '0.50% of Close' }
        ];
        options.forEach(opt => {
            const el = document.createElement('option');
            el.value = opt.value;
            el.textContent = opt.label;
            if (opt.value === '0.003') el.selected = true;
            sizeSelect.appendChild(el);
        });
        currentSize = '0.003';
    }
}

// Setup Listeners
function setupEventListeners() {
    tfSelect.addEventListener('change', (e) => {
        currentTimeframe = e.target.value;
        updateSizeOptions();
        loadDashboardData();
    });

    sizeSelect.addEventListener('change', (e) => {
        currentSize = e.target.value;
        loadDashboardData();
    });

    rrSelect.addEventListener('change', (e) => {
        currentRr = e.target.value;
        loadDashboardData();
    });

    // Table Filters
    searchInput.addEventListener('input', () => {
        currentPage = 1;
        applyFiltersAndRenderTable();
    });
    filterDirection.addEventListener('change', () => {
        currentPage = 1;
        applyFiltersAndRenderTable();
    });
    filterResult.addEventListener('change', () => {
        currentPage = 1;
        applyFiltersAndRenderTable();
    });

    // Pagination
    btnPrev.addEventListener('click', () => {
        if (currentPage > 1) {
            currentPage--;
            renderTable();
        }
    });
    btnNext.addEventListener('click', () => {
        const totalPages = Math.ceil(filteredTrades.length / rowsPerPage);
        if (currentPage < totalPages) {
            currentPage++;
            renderTable();
        }
    });
}

// Fetch JSON Data and Update Dashboard
async function loadDashboardData() {
    // Construct JSON path based on current state
    const prefix = currentTimeframe === 'hourly' ? 'hourly' : 'daily';
    const jsonPath = `data/results_${prefix}_${currentSize}_${currentRr}.json`;

    try {
        const response = await fetch(jsonPath);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        activeData = data;
        
        // Update summary cards
        updateSummaryCards(data.summary);
        
        // Render Charts
        renderEquityChart(data.equity_curve);
        renderHourlyChart(data.hourly_stats);
        renderSessionChart(data.session_stats);
        
        // Set up trade log table data
        filteredTrades = [...data.trades];
        currentPage = 1;
        applyFiltersAndRenderTable();
        
    } catch (error) {
        console.error("Failed to load backtest data:", error);
        clearDashboardData();
    }
}

// Update text statistics
function updateSummaryCards(summary) {
    statTotalTrades.textContent = summary.total_trades;
    statWinRate.textContent = `${(summary.win_rate * 100).toFixed(1)}%`;
    statNetProfit.textContent = summary.net_profit.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 });
    statProfitFactor.textContent = summary.profit_factor.toFixed(2);
    statMaxDrawdown.textContent = summary.max_drawdown.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 });
    
    // Average Ratio calculation
    const avgWin = summary.avg_win;
    const avgLoss = Math.abs(summary.avg_loss);
    if (avgLoss > 0) {
        statAvgRatio.textContent = `${avgWin.toFixed(1)} / -${avgLoss.toFixed(1)} pts (${(avgWin/avgLoss).toFixed(2)}x)`;
    } else {
        statAvgRatio.textContent = 'N/A';
    }
    
    // Optimal sessions
    bestSessionVal.textContent = summary.optimal_session || 'N/A';
    bestHourVal.textContent = summary.optimal_hour || 'N/A';
}

// Empty state handler
function clearDashboardData() {
    statTotalTrades.textContent = '0';
    statWinRate.textContent = '0.0%';
    statNetProfit.textContent = '0.0';
    statProfitFactor.textContent = '0.00';
    statMaxDrawdown.textContent = '0.0';
    statAvgRatio.textContent = 'N/A';
    bestSessionVal.textContent = 'N/A';
    bestHourVal.textContent = 'N/A';
    logCountLabel.textContent = 'Showing 0 trades';
    tableBody.innerHTML = '<tr><td colspan="10" style="text-align: center;">No trades found for this configuration. Run python3 run.py first.</td></tr>';
}

// Apply table search & filters
function applyFiltersAndRenderTable() {
    if (!activeData || !activeData.trades) return;
    
    const searchVal = searchInput.value.toLowerCase().trim();
    const directionVal = filterDirection.value;
    const resultVal = filterResult.value;
    
    filteredTrades = activeData.trades.filter(trade => {
        // Search matches
        const matchesSearch = searchVal === '' || 
            trade.entry_time.toLowerCase().includes(searchVal) ||
            trade.fvg_time.toLowerCase().includes(searchVal) ||
            String(trade.entry_price).includes(searchVal) ||
            String(trade.pnl).includes(searchVal);
            
        // Direction matches
        const matchesDirection = directionVal === 'all' || trade.direction === directionVal;
        
        // Result matches
        const matchesResult = resultVal === 'all' || 
            (resultVal === 'win' && trade.win === 1) || 
            (resultVal === 'loss' && trade.win === 0);
            
        return matchesSearch && matchesDirection && matchesResult;
    });
    
    renderTable();
}

// Render paginated table rows
function renderTable() {
    tableBody.innerHTML = '';
    
    const totalTradesCount = filteredTrades.length;
    logCountLabel.textContent = `Showing ${totalTradesCount} trades`;
    
    if (totalTradesCount === 0) {
        tableBody.innerHTML = '<tr><td colspan="10" style="text-align: center; color: var(--text-muted);">No trades matching the filters.</td></tr>';
        pageIndicator.textContent = 'Page 1 of 1';
        btnPrev.disabled = true;
        btnNext.disabled = true;
        return;
    }
    
    const totalPages = Math.ceil(totalTradesCount / rowsPerPage);
    if (currentPage > totalPages) currentPage = totalPages;
    if (currentPage < 1) currentPage = 1;
    
    const startIndex = (currentPage - 1) * rowsPerPage;
    const endIndex = Math.min(startIndex + rowsPerPage, totalTradesCount);
    
    pageIndicator.textContent = `Page ${currentPage} of ${totalPages}`;
    btnPrev.disabled = currentPage === 1;
    btnNext.disabled = currentPage === totalPages;
    
    const pageTrades = filteredTrades.slice(startIndex, endIndex);
    
    pageTrades.forEach(trade => {
        const row = document.createElement('tr');
        
        // Format dates: strip milliseconds & timezone info for compactness
        const formatTime = (timeStr) => {
            if (!timeStr) return '-';
            return timeStr.split('.')[0].replace('T', ' ');
        };
        
        const dirClass = trade.direction === 'long' ? 'tag long' : 'tag short';
        const resClass = trade.win === 1 ? 'tag win' : 'tag loss';
        const resText = trade.win === 1 ? 'Win' : 'Loss';
        
        const pnlFormatted = trade.pnl.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 });
        const pnlColorClass = trade.pnl > 0 ? 'text-green' : trade.pnl < 0 ? 'text-red' : '';
        
        row.innerHTML = `
            <td style="color: var(--text-secondary);">${formatTime(trade.fvg_time)}</td>
            <td><strong>${formatTime(trade.entry_time)}</strong></td>
            <td><span class="${dirClass}">${trade.direction}</span></td>
            <td>${trade.entry_price.toFixed(1)}</td>
            <td>${trade.sl.toFixed(1)}</td>
            <td>${trade.tp.toFixed(1)}</td>
            <td>${trade.exit_price ? trade.exit_price.toFixed(1) : '-'}</td>
            <td style="color: var(--text-muted);">${trade.exit_reason || '-'}</td>
            <td class="${pnlColorClass}" style="font-weight: 600;">${pnlFormatted}</td>
            <td><span class="${resClass}">${resText}</span></td>
        `;
        tableBody.appendChild(row);
    });
}

// ---------------- CHART RENDERING ----------------

function renderEquityChart(equityData) {
    if (equityChart) equityChart.destroy();
    
    const ctx = document.getElementById('equityChart').getContext('2d');
    
    // Create gradient
    const gradient = ctx.createLinearGradient(0, 0, 0, 300);
    gradient.addColorStop(0, 'rgba(59, 130, 246, 0.25)');
    gradient.addColorStop(1, 'rgba(59, 130, 246, 0.00)');
    
    const labels = equityData.map(d => d.time.split(' ')[0] || d.time);
    const dataPoints = equityData.map(d => d.pnl);
    
    equityChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Cumulative PnL (Points)',
                data: dataPoints,
                borderColor: '#3b82f6',
                borderWidth: 2.5,
                fill: true,
                backgroundColor: gradient,
                tension: 0.2,
                pointRadius: labels.length > 500 ? 0 : 2,
                pointHoverRadius: 6,
                pointHitRadius: 10
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    backgroundColor: 'rgba(15, 23, 42, 0.95)',
                    titleColor: '#fff',
                    bodyColor: '#f8fafc',
                    borderColor: 'rgba(255, 255, 255, 0.08)',
                    borderWidth: 1,
                    padding: 10,
                    displayColors: false
                }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.02)' },
                    ticks: {
                        color: '#64748b',
                        maxTicksLimit: 12
                    }
                },
                y: {
                    grid: { color: 'rgba(255, 255, 255, 0.04)' },
                    ticks: { color: '#64748b' }
                }
            }
        }
    });
}

function renderHourlyChart(hourlyData) {
    if (hourlyChart) hourlyChart.destroy();
    
    const ctx = document.getElementById('hourlyChart').getContext('2d');
    
    const labels = hourlyData.map(d => `${d.hour}:00`);
    const netProfits = hourlyData.map(d => d.net_profit);
    const winRates = hourlyData.map(d => d.win_rate * 100);
    
    // Dynamic color: green for positive hours, red for negative
    const barColors = netProfits.map(val => val >= 0 ? 'rgba(16, 185, 129, 0.7)' : 'rgba(239, 68, 68, 0.7)');
    
    hourlyChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Net Profit (Points)',
                    data: netProfits,
                    backgroundColor: barColors,
                    borderRadius: 6,
                    yAxisID: 'y'
                },
                {
                    label: 'Win Rate (%)',
                    data: winRates,
                    type: 'line',
                    borderColor: '#8b5cf6',
                    borderWidth: 2,
                    pointBackgroundColor: '#8b5cf6',
                    pointRadius: 3,
                    tension: 0.3,
                    fill: false,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                tooltip: {
                    backgroundColor: 'rgba(15, 23, 42, 0.95)',
                    padding: 10,
                    borderWidth: 1,
                    borderColor: 'rgba(255, 255, 255, 0.08)'
                },
                legend: {
                    labels: { color: '#94a3b8', boxWidth: 12 }
                }
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { color: '#64748b', maxTicksLimit: 12 }
                },
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    grid: { color: 'rgba(255, 255, 255, 0.04)' },
                    ticks: { color: '#64748b' },
                    title: {
                        display: true,
                        text: 'Points PnL',
                        color: '#64748b'
                    }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    grid: { drawOnChartArea: false },
                    ticks: {
                        color: '#64748b',
                        callback: value => `${value}%`
                    },
                    title: {
                        display: true,
                        text: 'Win Rate',
                        color: '#64748b'
                    },
                    min: 0,
                    max: 100
                }
            }
        }
    });
}

function renderSessionChart(sessionData) {
    if (sessionChart) sessionChart.destroy();
    
    const ctx = document.getElementById('sessionChart').getContext('2d');
    
    // Sort sessions in typical order
    const orderedSessions = [
        "London Session", "NY Pre-Market", "NY Morning", 
        "NY Lunch", "NY Afternoon", "Post-Market", "Globex Overnight"
    ];
    
    const mapping = {};
    sessionData.forEach(d => {
        mapping[d.session] = d;
    });
    
    const labels = [];
    const profits = [];
    const winRates = [];
    
    orderedSessions.forEach(sess => {
        if (mapping[sess]) {
            labels.push(sess);
            profits.push(mapping[sess].net_profit);
            winRates.push(mapping[sess].win_rate * 100);
        }
    });
    
    const sessionColors = profits.map(p => p >= 0 ? 'rgba(6, 182, 212, 0.75)' : 'rgba(239, 68, 68, 0.75)');
    
    sessionChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Net Profit (Points)',
                    data: profits,
                    backgroundColor: sessionColors,
                    borderRadius: 6,
                    yAxisID: 'y'
                },
                {
                    label: 'Win Rate (%)',
                    data: winRates,
                    type: 'line',
                    borderColor: '#f59e0b',
                    borderWidth: 2,
                    pointBackgroundColor: '#f59e0b',
                    pointRadius: 4,
                    tension: 0.1,
                    fill: false,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                tooltip: {
                    backgroundColor: 'rgba(15, 23, 42, 0.95)',
                    padding: 10,
                    borderWidth: 1,
                    borderColor: 'rgba(255, 255, 255, 0.08)'
                },
                legend: {
                    labels: { color: '#94a3b8', boxWidth: 12 }
                }
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { color: '#64748b' }
                },
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    grid: { color: 'rgba(255, 255, 255, 0.04)' },
                    ticks: { color: '#64748b' }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    grid: { drawOnChartArea: false },
                    ticks: {
                        color: '#64748b',
                        callback: value => `${value}%`
                    },
                    min: 0,
                    max: 100
                }
            }
        }
    });
}
