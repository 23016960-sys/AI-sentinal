// Logic điều khiển hệ thống AI Sentinel Dashboard

// Khai báo biến toàn cục
let threatMap;
let mapLayers = [];
let osChart;
let activityChart;
let currentTab = 'dashboard';
let recentLogsCache = [];

// Khởi tạo ứng dụng
document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    initMap();
    initCharts();
    loadSettings();
    loadDashboardData();
    
    // Cài đặt sự kiện tương tác
    document.getElementById('btn-simulate').addEventListener('click', triggerSimulation);
    document.getElementById('playground-form').addEventListener('submit', handlePlaygroundSubmit);
    document.getElementById('btn-save-settings').addEventListener('click', saveSettings);
    document.getElementById('btn-retrain-model').addEventListener('click', retrainModel);
    document.getElementById('btn-close-drawer').addEventListener('click', closeDrawer);
    
    // Đăng ký sự kiện tự động điền IP khi đổi Thành phố ở Playground
    document.getElementById('play-city').addEventListener('change', autoFillPlaygroundIp);
    autoFillPlaygroundIp(); // Chạy lần đầu

    // Tự động cập nhật dữ liệu Dashboard mỗi 10 giây (giả lập real-time)
    setInterval(() => {
        if (currentTab === 'dashboard') {
            loadDashboardData(true); // silent update
        }
    }, 10000);
});

// --- PHÂN HỆ TABS & GIAO DIỆN ---
function initTabs() {
    const tabs = {
        'btn-tab-dashboard': { id: 'tab-dashboard', title: 'Trung tâm Giám sát Thời gian thực', subtitle: 'Đang theo dõi các luồng đăng nhập hệ thống' },
        'btn-tab-playground': { id: 'tab-playground', title: 'Phòng thí nghiệm Sự kiện (Playground)', subtitle: 'Thử nghiệm giả lập đầu vào và giải thích mô hình AI' },
        'btn-tab-settings': { id: 'tab-settings', title: 'Cấu hình Hệ thống & Huấn luyện', subtitle: 'Tinh chỉnh chính sách bảo mật và tham số mô hình học máy' }
    };

    Object.keys(tabs).forEach(tabBtnId => {
        document.getElementById(tabBtnId).addEventListener('click', (e) => {
            e.preventDefault();
            
            // Xóa active cũ
            Object.keys(tabs).forEach(k => {
                document.getElementById(k).classList.remove('active');
                document.getElementById(tabs[k].id).classList.remove('active');
            });

            // Active mới
            document.getElementById(tabBtnId).classList.add('active');
            const targetTab = tabs[tabBtnId];
            document.getElementById(targetTab.id).classList.add('active');
            
            // Cập nhật tiêu đề header
            document.getElementById('current-tab-title').textContent = targetTab.title;
            document.getElementById('current-tab-subtitle').textContent = targetTab.subtitle;
            
            // Lưu trạng thái tab hiện tại
            currentTab = targetTab.id.replace('tab-', '');
            
            // Nếu chuyển về dashboard, cập nhật lại bản đồ vì kích thước div có thể thay đổi
            if (currentTab === 'dashboard' && threatMap) {
                setTimeout(() => {
                    threatMap.invalidateSize();
                }, 200);
            }
        });
    });
}

// --- PHÂN HỆ BẢN ĐỒ LEAFLET ---
function initMap() {
    // Khởi tạo map tại Việt Nam, chỉnh zoom lên 5 để thấy rõ các quần đảo
    threatMap = L.map('threat-map', {
        zoomControl: true,
        attributionControl: false
    }).setView([15.5, 111.0], 5);

    // Sử dụng OpenStreetMap tile - dùng tên quốc tế chuẩn, KHÔNG dùng tên Trung Quốc
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 18,
        minZoom: 2,
        className: 'map-dark-filter'
    }).addTo(threatMap);
    
    // Khẳng định chủ quyền Hoàng Sa & Trường Sa của Việt Nam
    addVietnameseSovereignty();
}

function addVietnameseSovereignty() {
    if (!threatMap) return;
    
    // Icon nhãn chủ quyền
    function makeIslandIcon(label) {
        return L.divIcon({
            className: 'sovereignty-label',
            html: `<div class="island-badge">🇻🇳 ${label}</div>`,
            iconSize: [110, 24],
            iconAnchor: [55, 12]
        });
    }
    
    // --- Quần đảo Hoàng Sa ---
    // Toạ độ trung tâm: khoảng 16.5°N, 112.0°E
    L.circle([16.5, 112.0], {
        radius: 80000,
        color: '#ef4444',
        fillColor: '#ef4444',
        fillOpacity: 0.08,
        weight: 2,
        dashArray: '5, 5'
    }).addTo(threatMap)
      .bindTooltip('Quần đảo Hoàng Sa — Chủ quyền Việt Nam', { sticky: true });
    
    L.marker([16.5, 112.0], { icon: makeIslandIcon('Hoàng Sa (VN)') })
        .addTo(threatMap)
        .bindPopup('<b>🇻🇳 Quần đảo Hoàng Sa</b><br>Thuộc chủ quyền Việt Nam<br><small>Paracel Islands — Vietnam</small>');
    
    // --- Quần đảo Trường Sa ---
    // Toạ độ trung tâm: khoảng 9.5°N, 113.5°E
    L.circle([9.5, 113.5], {
        radius: 150000,
        color: '#ef4444',
        fillColor: '#ef4444',
        fillOpacity: 0.08,
        weight: 2,
        dashArray: '5, 5'
    }).addTo(threatMap)
      .bindTooltip('Quần đảo Trường Sa — Chủ quyền Việt Nam', { sticky: true });
    
    L.marker([9.5, 113.5], { icon: makeIslandIcon('Trường Sa (VN)') })
        .addTo(threatMap)
        .bindPopup('<b>🇻🇳 Quần đảo Trường Sa</b><br>Thuộc chủ quyền Việt Nam<br><small>Spratly Islands — Vietnam</small>');

    // --- Nhãn tên "Biển Đông" ---
    L.marker([13.5, 113.0], {
        icon: L.divIcon({
            className: 'sovereignty-label',
            html: '<div class="sea-label">BIỂN ĐÔNG (Việt Nam)</div>',
            iconSize: [180, 20],
            iconAnchor: [90, 10]
        })
    }).addTo(threatMap);
}

function updateMapData(locations) {
    if (!threatMap) return;

    // Xóa marker và line cũ
    mapLayers.forEach(layer => threatMap.removeLayer(layer));
    mapLayers = [];

    // Nhóm logins theo user để vẽ impossible travel lines nếu có
    const userLogins = {};
    
    locations.forEach(loc => {
        const username = loc.username;
        if (!userLogins[username]) userLogins[username] = [];
        userLogins[username].push(loc);
        
        const lat = parseFloat(loc.latitude);
        const lon = parseFloat(loc.longitude);
        
        if (isNaN(lat) || isNaN(lon)) return;

        // Chọn màu sắc dựa trên rủi ro
        let color = '#10b981'; // Green
        let radius = 6;
        let isAnom = loc.is_anomaly;
        
        if (loc.risk_level === 'CRITICAL') {
            color = '#ef4444'; // Red
            radius = 9;
        } else if (loc.risk_level === 'SUSPICIOUS') {
            color = '#f59e0b'; // Amber
            radius = 8;
        }

        // Tạo vòng tròn nhấp nháy cho điểm bất thường
        if (isAnom) {
            const pulseCircle = L.circle([lat, lon], {
                radius: 120000,
                color: color,
                fillColor: color,
                fillOpacity: 0.15,
                weight: 1,
                className: 'leaflet-pulse-circle'
            }).addTo(threatMap);
            mapLayers.push(pulseCircle);
        }

        // Tạo marker
        const marker = L.circleMarker([lat, lon], {
            radius: radius,
            fillColor: color,
            color: '#ffffff',
            weight: 1.5,
            fillOpacity: 0.95
        }).addTo(threatMap);

        // Tạo Popup thông tin
        const timeStr = loc.timestamp.split(' ')[1] || loc.timestamp;
        const popupText = `
            <div style="font-size: 12px; line-height: 1.4;">
                <strong style="color: ${color};">${loc.risk_level} LOGIN</strong><br/>
                <b>User:</b> ${username}<br/>
                <b>IP:</b> ${loc.ip_address}<br/>
                <b>Vị trí:</b> ${loc.city}, ${loc.country}<br/>
                <b>Thời gian:</b> ${loc.timestamp}
            </div>
        `;
        marker.bindPopup(popupText);
        mapLayers.push(marker);
    });

    // Vẽ đường nối di chuyển bất khả thi (Impossible Travel vectors)
    locations.forEach(loc => {
        if (loc.is_anomaly && loc.reasons && loc.reasons.some(r => r.includes('di chuyển bất khả thi'))) {
            // Tìm bản ghi bình thường ngay trước đó của user này trong cache để vẽ đường kết nối
            const user = loc.username;
            const userHistory = recentLogsCache.filter(x => x.username === user);
            const thisIdx = userHistory.findIndex(x => x.timestamp === loc.timestamp);
            
            // Lấy log trước đó
            if (thisIdx > 0) {
                const prevLoc = userHistory[thisIdx - 1]; // Vì logs sắp xếp ngược, log trước đó là index + 1
                const prevLat = parseFloat(prevLoc.latitude);
                const prevLon = parseFloat(prevLoc.longitude);
                const currLat = parseFloat(loc.latitude);
                const currLon = parseFloat(loc.longitude);
                
                if (!isNaN(prevLat) && !isNaN(prevLon)) {
                    // Vẽ polyline màu đỏ đứt nét
                    const polyline = L.polyline([[prevLat, prevLon], [currLat, currLon]], {
                        color: '#ef4444',
                        weight: 2,
                        dashArray: '5, 8',
                        opacity: 0.8
                    }).addTo(threatMap);
                    
                    // Thêm mũi tên hướng đi hoặc tooltip
                    polyline.bindTooltip(`Impossible Travel Vector: ${prevLoc.city} ➔ ${loc.city}`, { sticky: true });
                    mapLayers.push(polyline);
                }
            }
        }
    });
}

// --- PHÂN HỆ BIỂU ĐỒ CHART.JS ---
function initCharts() {
    // 1. OS Donut Chart
    const ctxOs = document.getElementById('os-chart').getContext('2d');
    osChart = new Chart(ctxOs, {
        type: 'doughnut',
        data: {
            labels: ['Windows', 'macOS', 'Linux', 'iOS', 'Android'],
            datasets: [{
                data: [0, 0, 0, 0, 0],
                backgroundColor: [
                    '#06b6d4', // Cyan
                    '#a855f7', // Light Purple
                    '#f59e0b', // Amber
                    '#ec4899', // Pink
                    '#10b981'  // Emerald
                ],
                borderWidth: 1,
                borderColor: '#111827'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: '#9ca3af',
                        font: { family: 'Outfit', size: 11 },
                        padding: 15
                    }
                }
            },
            cutout: '65%'
        }
    });

    // 2. Timeline Activity Stacked Chart
    const ctxAct = document.getElementById('activity-chart').getContext('2d');
    activityChart = new Chart(ctxAct, {
        type: 'bar',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'Bình thường',
                    data: [],
                    backgroundColor: 'rgba(16, 185, 129, 0.65)',
                    borderColor: '#10b981',
                    borderWidth: 1,
                    borderRadius: 4
                },
                {
                    label: 'Bất thường',
                    data: [],
                    backgroundColor: 'rgba(239, 68, 68, 0.7)',
                    borderColor: '#ef4444',
                    borderWidth: 1,
                    borderRadius: 4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        color: '#9ca3af',
                        font: { family: 'Outfit', size: 11 }
                    }
                }
            },
            scales: {
                x: {
                    stacked: true,
                    grid: { color: 'rgba(255, 255, 255, 0.03)' },
                    ticks: { color: '#6b7280', font: { family: 'Outfit', size: 10 } }
                },
                y: {
                    stacked: true,
                    grid: { color: 'rgba(255, 255, 255, 0.03)' },
                    ticks: { color: '#6b7280', font: { family: 'Outfit', size: 10 }, stepSize: 1 }
                }
            }
        }
    });
}

// --- TẢI DỮ LIỆU TỪ BACKEND ---
async function loadDashboardData(isSilent = false) {
    try {
        // Tải danh sách logs
        const logsRes = await fetch('/api/logs');
        const logs = await logsRes.json();
        recentLogsCache = logs; // Lưu cache cục bộ
        
        // Cập nhật bảng log
        renderLogsTable(logs);

        // Tải số liệu thống kê
        const statsRes = await fetch('/api/stats');
        const stats = await statsRes.json();
        
        // Cập nhật các thẻ số liệu (Stats cards)
        if (!isSilent) {
            animateValue('stat-total-logins', 0, stats.total_logins, 1000);
            animateValue('stat-anomalies', 0, stats.anomaly_count, 1000);
            animateValue('stat-risk-index', 0, stats.risk_index, 1000);
            animateValue('stat-devices', 0, stats.unique_devices, 1000);
        } else {
            document.getElementById('stat-total-logins').textContent = stats.total_logins;
            document.getElementById('stat-anomalies').textContent = stats.anomaly_count;
            document.getElementById('stat-risk-index').textContent = stats.risk_index + '%';
            document.getElementById('stat-devices').textContent = stats.unique_devices;
        }

        // Cập nhật tỷ lệ bất thường & mức độ rủi ro hệ thống
        const anomalyRate = stats.total_logins > 0 ? ((stats.anomaly_count / stats.total_logins) * 100).toFixed(1) : 0;
        document.getElementById('stat-anomaly-rate').textContent = `${anomalyRate}% tỷ lệ bất thường`;
        
        const riskLevelLabel = document.getElementById('stat-risk-level');
        riskLevelLabel.textContent = stats.risk_index >= 70 ? 'Cảnh báo Rủi ro cao' : stats.risk_index >= 40 ? 'Rủi ro Trung bình' : 'Trạng thái An toàn';
        riskLevelLabel.className = 'stat-trend';
        if (stats.risk_index >= 70) riskLevelLabel.classList.add('trend-down');
        else if (stats.risk_index >= 40) riskLevelLabel.classList.add('trend-neutral');
        else riskLevelLabel.classList.add('trend-up');

        // Cập nhật biểu đồ OS Donut Chart
        const osLabels = ['Windows', 'macOS', 'Linux', 'iOS', 'Android'];
        const osData = osLabels.map(label => stats.device_os[label] || 0);
        osChart.data.datasets[0].data = osData;
        osChart.update();

        // Cập nhật biểu đồ Activity Chart
        activityChart.data.labels = stats.hourly_activity.labels;
        activityChart.data.datasets[0].data = stats.hourly_activity.normal;
        activityChart.data.datasets[1].data = stats.hourly_activity.anomaly;
        activityChart.update();

        // Cập nhật bản đồ đe dọa
        updateMapData(stats.location_distribution);

    } catch (err) {
        console.error('Lỗi khi tải dữ liệu dashboard:', err);
    }
}

// Hàm render bảng log đăng nhập
function renderLogsTable(logs) {
    const tbody = document.getElementById('logs-table-body');
    if (!logs || logs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">Không có dữ liệu đăng nhập nào.</td></tr>';
        return;
    }

    tbody.innerHTML = '';
    logs.forEach(log => {
        const tr = document.createElement('tr');
        tr.dataset.logId = log.timestamp + '_' + log.username;
        tr.addEventListener('click', () => openInspectionDrawer(log));

        // Format thời gian hiển thị gọn
        const dateObj = new Date(log.timestamp);
        const timeFormatted = dateObj.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }) + ' ' + dateObj.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' });

        // Badge mức độ rủi ro
        let levelBadge = `<span class="badge badge-success">Thấp</span>`;
        if (log.risk_level === 'CRITICAL') {
            levelBadge = `<span class="badge badge-danger">Nguy hiểm</span>`;
        } else if (log.risk_level === 'SUSPICIOUS') {
            levelBadge = `<span class="badge badge-warning">Nghi vấn</span>`;
        }

        // Trạng thái Success/Failed
        const statusText = log.login_status === 'success' 
            ? '<span class="text-success">Thành công</span>' 
            : '<span class="text-danger">Thất bại</span>';

        tr.innerHTML = `
            <td class="font-bold">${timeFormatted}</td>
            <td><code>${log.username}</code></td>
            <td>${log.ip_address}</td>
            <td>${log.city}, ${log.country}</td>
            <td><small>${log.device_os} / ${log.device_browser}</small></td>
            <td>${statusText}</td>
            <td>${levelBadge}</td>
        `;
        
        // Thêm màu nền nhạt cho các dòng bất thường nguy hiểm
        if (log.risk_level === 'CRITICAL') {
            tr.style.backgroundColor = 'rgba(239, 68, 68, 0.04)';
        }
        
        tbody.appendChild(tr);
    });
}

// --- MÔ PHỎNG LIVE LOGINS ---
async function triggerSimulation() {
    const simType = document.getElementById('simulation-type').value;
    const btn = document.getElementById('btn-simulate');
    btn.disabled = true;
    btn.innerHTML = '<div class="spinner" style="width: 14px; height: 14px; border-width: 2px;"></div> Đang giả lập...';

    try {
        const res = await fetch('/api/simulate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ anomaly_type: simType })
        });
        const log = await res.json();
        
        // Hiển thị Toast thông báo đăng nhập mới
        showToast(log);
        
        // Tải lại dữ liệu dashboard
        await loadDashboardData(false);
    } catch (err) {
        console.error('Lỗi khi giả lập đăng nhập:', err);
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<span class="btn-icon">⚡</span> Kích hoạt Đăng nhập';
    }
}

// --- PHÂN HỆ INSPECTION DRAWER (CHI TIẾT LOG) ---
function openInspectionDrawer(log) {
    const drawer = document.getElementById('inspection-drawer');
    const content = document.getElementById('drawer-content');
    
    // Xác định màu sắc chủ đạo của Drawer theo mức độ rủi ro
    let badgeClass = 'badge-glow-green';
    let riskText = 'AN TOÀN';
    let riskDesc = 'Lượt đăng nhập này khớp hoàn hảo với các thói quen lịch sử của người dùng.';
    
    if (log.risk_level === 'CRITICAL') {
        badgeClass = 'badge-glow-red';
        riskText = 'NGUY HIỂM CỰC ĐỘ';
        riskDesc = 'Đăng nhập bị chặn hoặc cảnh báo khẩn do vi phạm quy tắc bảo mật nghiêm trọng.';
    } else if (log.risk_level === 'SUSPICIOUS') {
        badgeClass = 'badge-glow-amber';
        riskText = 'NGHI VẤN CAO';
        riskDesc = 'Hành vi đăng nhập có sự sai lệch đáng kể so với thói quen thông thường.';
    }

    // Tạo HTML danh sách nguyên nhân
    let reasonsHtml = '';
    if (log.reasons && log.reasons.length > 0) {
        reasonsHtml = log.reasons.map(r => `<li>⚠️ ${r}</li>`).join('');
    } else {
        reasonsHtml = '<li>Hoạt động bình thường.</li>';
    }

    // Render thông tin chi tiết vào Drawer
    content.innerHTML = `
        <div class="risk-gauge-box">
            <div class="risk-gauge-circle ${badgeClass}">
                <span class="risk-gauge-val">${log.risk_score}</span>
                <span class="risk-gauge-lbl">RISK SCORE</span>
            </div>
            <div class="risk-level-tag ${badgeClass}">${riskText}</div>
            <p style="font-size: 12px; color: var(--text-secondary); text-align: center; margin-top: 12px; line-height: 1.4;">
                ${riskDesc}
            </p>
        </div>

        <div class="info-section">
            <h4>Phân tích nguyên nhân bất thường</h4>
            <div class="reasons-list" style="margin-bottom: 0;">
                <ul style="padding-left: 0;">
                    ${reasonsHtml}
                </ul>
            </div>
        </div>

        <div class="info-section">
            <h4>Thông tin Tài khoản & Thiết bị</h4>
            <div class="info-grid">
                <div class="info-row">
                    <span>Tên tài khoản:</span>
                    <span><code>${log.username}</code></span>
                </div>
                <div class="info-row">
                    <span>Thời gian ghi nhận:</span>
                    <span>${log.timestamp}</span>
                </div>
                <div class="info-row">
                    <span>Địa chỉ IP:</span>
                    <span>${log.ip_address}</span>
                </div>
                <div class="info-row">
                    <span>Vị trí địa lý:</span>
                    <span>${log.city}, ${log.country}</span>
                </div>
                <div class="info-row">
                    <span>Hệ điều hành:</span>
                    <span>${log.device_os}</span>
                </div>
                <div class="info-row">
                    <span>Trình duyệt:</span>
                    <span>${log.device_browser}</span>
                </div>
            </div>
        </div>

        <div class="info-section">
            <h4>Chỉ số Phân tích Học máy (Features)</h4>
            <div class="feature-analysis-grid">
                <div class="feature-metric-card">
                    <span class="metric-name">Khoảng cách tới tâm vị trí thường lệ</span>
                    <span class="metric-val">${log.features ? log.features.dist_from_centroid.toFixed(1) : 0} km</span>
                </div>
                <div class="feature-metric-card">
                    <span class="metric-name">Vận tốc di chuyển tính toán</span>
                    <span class="metric-val">${log.features ? log.features.travel_speed.toFixed(1) : 0} km/h</span>
                </div>
                <div class="feature-metric-card">
                    <span class="metric-name">Thiết bị lạ (Hệ điều hành mới)</span>
                    <span class="metric-val">${log.features && log.features.is_new_os ? 'Đúng (1)' : 'Không (0)'}</span>
                </div>
                <div class="feature-metric-card">
                    <span class="metric-name">Trình duyệt lạ (Browser mới)</span>
                    <span class="metric-val">${log.features && log.features.is_new_browser ? 'Đúng (1)' : 'Không (0)'}</span>
                </div>
                <div class="feature-metric-card">
                    <span class="metric-name">Đăng nhập lỗi liên tiếp trước đó</span>
                    <span class="metric-val">${log.consecutive_failures} lần</span>
                </div>
                <div class="feature-metric-card">
                    <span class="metric-name">Kết quả lần này</span>
                    <span class="metric-val text-success">${log.login_status.toUpperCase()}</span>
                </div>
            </div>
        </div>
    `;

    drawer.classList.add('open');
}

function closeDrawer() {
    document.getElementById('inspection-drawer').classList.remove('open');
}

// --- Giao diện Toast ---
function showToast(log) {
    const toast = document.getElementById('toast-notification');
    const msg = document.getElementById('toast-message');
    
    // Set màu sắc và icon theo rủi ro
    toast.className = 'toast-notification show';
    let icon = 'ℹ️';
    
    if (log.risk_level === 'CRITICAL') {
        toast.classList.add('toast-danger');
        icon = '🚨';
        msg.innerHTML = `<strong>Cảnh báo Nguy hiểm:</strong> Tài khoản <code>${log.username}</code> đăng nhập bất thường!`;
    } else if (log.risk_level === 'SUSPICIOUS') {
        toast.classList.add('toast-warning');
        icon = '⚠️';
        msg.innerHTML = `<strong>Nghi ngờ:</strong> Có lượt đăng nhập lạ từ <code>${log.username}</code>.`;
    } else {
        toast.classList.add('toast-success');
        icon = '🔑';
        msg.innerHTML = `Đăng nhập thành công: <code>${log.username}</code>.`;
    }
    
    document.querySelector('.toast-icon').textContent = icon;

    // Tự động tắt sau 4 giây
    setTimeout(() => {
        toast.classList.remove('show');
    }, 4000);
}

// --- TAB 2: INTERACTIVE PLAYGROUND ---
const PLAYGROUND_IPS = {
    "Hanoi": "113.190.23.104",
    "Ho Chi Minh City": "14.161.85.92",
    "Da Nang": "27.72.10.45",
    "Can Tho": "115.79.231.14",
    "New York": "100.1.55.201",
    "Moscow": "185.120.40.11",
    "Tokyo": "122.211.89.67",
    "London": "82.165.12.98"
};

function autoFillPlaygroundIp() {
    const city = document.getElementById('play-city').value;
    const ipInput = document.getElementById('play-ip');
    ipInput.value = PLAYGROUND_IPS[city] || "";
}

async function handlePlaygroundSubmit(e) {
    e.preventDefault();
    
    const user = document.getElementById('play-user').value;
    const city = document.getElementById('play-city').value;
    const ip = document.getElementById('play-ip').value;
    const os = document.getElementById('play-os').value;
    const browser = document.getElementById('play-browser').value;
    const timeVal = document.getElementById('play-time').value;
    const failures = document.getElementById('play-failures').value;
    const status = document.getElementById('play-status').value;
    
    // Giả lập tọa độ từ danh mục LOCATIONS của data_generator.py
    const playLocations = {
        "Hanoi": { lat: 21.0285, lon: 105.8542, country: "Vietnam" },
        "Ho Chi Minh City": { lat: 10.8231, lon: 106.6297, country: "Vietnam" },
        "Da Nang": { lat: 16.0544, lon: 108.2022, country: "Vietnam" },
        "Can Tho": { lat: 10.0452, lon: 105.7469, country: "Vietnam" },
        "New York": { lat: 40.7128, lon: -74.0060, country: "United States" },
        "Moscow": { lat: 55.7558, lon: 37.6173, country: "Russia" },
        "Tokyo": { lat: 35.6762, lon: 139.6503, country: "Japan" },
        "London": { lat: 51.5074, lon: -0.1278, country: "United Kingdom" }
    };
    
    const loc = playLocations[city];
    
    // Đóng gói data gửi lên API predict
    const payload = {
        username: user,
        ip_address: ip,
        latitude: loc.lat,
        longitude: loc.lon,
        city: city,
        country: loc.country,
        device_os: os,
        device_browser: browser,
        login_status: status,
        consecutive_failures: parseInt(failures),
        user_agent: `Mozilla/5.0 (${os}; Touch) AppleWebKit/537.36 (${browser})`
    };

    const submitBtn = document.getElementById('btn-submit-playground');
    submitBtn.disabled = true;
    submitBtn.textContent = '🕵️ Đang phân tích dữ liệu...';

    try {
        const res = await fetch('/api/predict', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        const result = await res.json();
        renderPlaygroundResult(result, payload);
    } catch (err) {
        console.error('Lỗi khi gửi login playground:', err);
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = '🔬 Phân tích sự kiện bằng AI Engine';
    }
}

// Render kết quả phân tích playground
function renderPlaygroundResult(res, input) {
    const resultBox = document.getElementById('playground-result-body');
    
    let badgeClass = 'badge-success';
    let labelText = 'AN TOÀN (LOW RISK)';
    
    if (res.risk_level === 'CRITICAL') {
        badgeClass = 'badge-danger';
        labelText = 'NGUY HIỂM (CRITICAL)';
    } else if (res.risk_level === 'SUSPICIOUS') {
        badgeClass = 'badge-warning';
        labelText = 'NGHI VẤN (SUSPICIOUS)';
    }

    // Danh sách lý do giải thích
    const reasonsHtml = res.reasons.map(r => `<li>⚠️ ${r}</li>`).join('');

    resultBox.innerHTML = `
        <div class="result-header">
            <span class="badge ${badgeClass} result-badge">${labelText}</span>
            <div class="result-score-container">
                <span class="result-score-label">ML Risk Score</span>
                <span class="result-score-value text-${badgeClass.split('-')[1]}">${res.risk_score}%</span>
            </div>
        </div>

        <div class="reasons-list">
            <h5>Giải thích phân tích từ AI Engine:</h5>
            <ul style="padding-left: 0; margin-bottom: 0;">
                ${reasonsHtml}
            </ul>
        </div>

        <h5 style="font-size: 13px; color: var(--text-secondary); margin-bottom: 12px;">Đặc trưng tính toán (Feature Engineering):</h5>
        <div class="feature-analysis-grid">
            <div class="feature-metric-card">
                <span class="metric-name">Khoảng cách tới baseline centroid</span>
                <span class="metric-val">${res.features.dist_from_centroid.toFixed(1)} km</span>
            </div>
            <div class="feature-metric-card">
                <span class="metric-name">Vận tốc di chuyển ước tính</span>
                <span class="metric-val">${res.features.travel_speed.toFixed(1)} km/h</span>
            </div>
            <div class="feature-metric-card">
                <span class="metric-name">Thiết bị lạ (Hệ điều hành lạ)</span>
                <span class="metric-val">${res.features.is_new_os ? 'Đúng (1)' : 'Không (0)'}</span>
            </div>
            <div class="feature-metric-card">
                <span class="metric-name">Trình duyệt lạ (Browser lạ)</span>
                <span class="metric-val">${res.features.is_new_browser ? 'Đúng (1)' : 'Không (0)'}</span>
            </div>
            <div class="feature-metric-card">
                <span class="metric-name">Consecutive Failures</span>
                <span class="metric-val">${input.consecutive_failures} lần</span>
            </div>
            <div class="feature-metric-card">
                <span class="metric-name">Kết quả đăng nhập</span>
                <span class="metric-val">${input.login_status.toUpperCase()}</span>
            </div>
        </div>
        
        <p style="font-size: 11px; color: var(--text-muted); margin-top: 16px; text-align: center; line-height: 1.4;">
            *Điểm số học máy được xác định bởi mô hình Isolation Forest sau khi chuẩn hóa đầu vào thông qua Z-score scaler.
        </p>
    `;
}

// --- TAB 3: CONFIG & MODEL SETTINGS ---
async function loadSettings() {
    try {
        const res = await fetch('/api/settings');
        const settings = await res.json();
        
        document.getElementById('setting-enable-ml').checked = settings.enable_ml;
        document.getElementById('setting-enable-impossible-travel').checked = settings.enable_impossible_travel;
        document.getElementById('setting-enable-brute-force').checked = settings.enable_brute_force;
        
        document.getElementById('setting-ml-threshold').value = settings.ml_threshold;
        document.getElementById('setting-ml-threshold-val').textContent = settings.ml_threshold;
        
        // Setup slider live label change
        document.getElementById('setting-ml-threshold').addEventListener('input', (e) => {
            document.getElementById('setting-ml-threshold-val').textContent = e.target.value;
        });

        // Load feature importance
        loadFeatureImportancePlaceholder();
    } catch (err) {
        console.error('Lỗi tải cấu hình settings:', err);
    }
}

async function saveSettings() {
    const payload = {
        enable_ml: document.getElementById('setting-enable-ml').checked,
        enable_impossible_travel: document.getElementById('setting-enable-impossible-travel').checked,
        enable_brute_force: document.getElementById('setting-enable-brute-force').checked,
        ml_threshold: parseInt(document.getElementById('setting-ml-threshold').value)
    };

    const btn = document.getElementById('btn-save-settings');
    btn.disabled = true;
    btn.textContent = 'Saving...';

    try {
        const res = await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        
        // Show Toast Success
        const mockLog = { risk_level: 'LOW', username: 'SYSTEM', login_status: 'success' };
        showToast(mockLog);
        document.getElementById('toast-message').textContent = 'Đã cập nhật chính sách bảo mật thành công!';
        
        // Update stats again
        loadDashboardData(true);
    } catch (err) {
        console.error('Lỗi lưu cài đặt settings:', err);
    } finally {
        btn.disabled = false;
        btn.textContent = '💾 Lưu cấu hình chính sách';
    }
}

// Tải độ quan trọng đặc trưng (Feature Importance) lên Model Panel
function loadFeatureImportancePlaceholder(importanceData = null) {
    const barsContainer = document.getElementById('feature-importance-bars');
    
    // Mặc định hoặc dữ liệu thực từ huấn luyện
    const importance = importanceData || {
        "hour_cos": 35.98,
        "hour_sin": 24.05,
        "dist_from_centroid": 23.79,
        "travel_speed": 9.36,
        "is_failed": 2.89,
        "day_of_week": 1.96,
        "consecutive_failures": 1.96,
        "is_new_os": 0.0,
        "is_new_browser": 0.0
    };
    
    // Ánh xạ tên tiếng Việt cho thân thiện
    const labelsMap = {
        "dist_from_centroid": "Khoảng cách tới Vị trí Thường lệ (Centroid Distance)",
        "travel_speed": "Vận tốc di chuyển (Impossible Travel Velocity)",
        "hour_cos": "Khung giờ đăng nhập (Thời gian biểu Cosine)",
        "hour_sin": "Khung giờ đăng nhập (Thời gian biểu Sine)",
        "is_new_os": "Hệ điều hành thiết bị mới lạ (OS Anomaly)",
        "is_new_browser": "Trình duyệt thiết bị mới lạ (Browser Anomaly)",
        "day_of_week": "Ngày trong tuần (Weekday Pattern)",
        "consecutive_failures": "Số lần đăng nhập lỗi liên tiếp",
        "is_failed": "Trạng thái đăng nhập lỗi của lần hiện tại"
    };

    barsContainer.innerHTML = '';
    
    // Sắp xếp giảm dần theo giá trị
    const sortedFeatures = Object.entries(importance).sort((a, b) => b[1] - a[1]);
    
    sortedFeatures.forEach(([feat, val]) => {
        const friendlyName = labelsMap[feat] || feat;
        const row = document.createElement('div');
        row.className = 'feature-bar-row';
        row.innerHTML = `
            <div class="feature-bar-labels">
                <span>${friendlyName}</span>
                <span class="font-bold">${val}%</span>
            </div>
            <div class="feature-bar-bg">
                <div class="feature-bar-fill" style="width: ${val}%;"></div>
            </div>
        `;
        barsContainer.appendChild(row);
    });
}

// --- HUẤN LUYỆN LẠI MÔ HÌNH ---
async function retrainModel() {
    const contamination = document.getElementById('train-contamination').value;
    const loader = document.getElementById('train-loader');
    const btn = document.getElementById('btn-retrain-model');
    
    // Hiển thị loader và khóa button
    loader.classList.remove('hidden');
    btn.disabled = true;

    try {
        const res = await fetch('/api/train', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ contamination: parseFloat(contamination) })
        });
        
        const data = await res.json();
        
        if (data.status === 'success') {
            // Cập nhật lại chỉ số huấn luyện trên UI
            document.getElementById('model-accuracy').textContent = (data.metrics.accuracy * 100).toFixed(1) + '%';
            
            // Vẽ lại biểu đồ Feature Importance thực từ Backend
            loadFeatureImportancePlaceholder(data.metrics.feature_importance);
            
            // Thông báo thành công
            const mockLog = { risk_level: 'LOW', username: 'SYSTEM', login_status: 'success' };
            showToast(mockLog);
            document.getElementById('toast-message').textContent = 'Huấn luyện lại mô hình Isolation Forest thành công!';
            
            // Tải lại toàn bộ dữ liệu dashboard để cập nhật các dự đoán mới
            await loadDashboardData(false);
        }
    } catch (err) {
        console.error('Lỗi khi huấn luyện lại mô hình:', err);
        alert('Có lỗi xảy ra khi huấn luyện lại mô hình học máy.');
    } finally {
        loader.classList.add('hidden');
        btn.disabled = false;
    }
}

// --- TIỆN ÍCH ANIME GIÁ TRỊ SỐ ---
function animateValue(id, start, end, duration) {
    const obj = document.getElementById(id);
    if (!obj) return;
    
    // Nếu end = 0 hoặc rỗng
    if (isNaN(end) || end === null || end === undefined) {
        obj.textContent = '-';
        return;
    }
    
    let startTimestamp = null;
    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        const val = Math.floor(progress * (end - start) + start);
        
        // Thêm hậu tố % cho Risk Index
        if (id === 'stat-risk-index') {
            obj.textContent = val + '%';
        } else {
            obj.textContent = val.toLocaleString('vi-VN');
        }
        
        if (progress < 1) {
            window.requestAnimationFrame(step);
        }
    };
    window.requestAnimationFrame(step);
}
