const API = window.location.origin;
let contractChart = null;

async function apiFetch(path, options) {
  const r = await fetch(`${API}${path}`, options);
  if (r.status === 401) {
    window.location.href = "/login.html";
    throw new Error("Potrebna je prijava");
  }
  return r;
}

async function logout() {
  await fetch(`${API}/auth/logout`, { method: "POST" });
  window.location.href = "/login.html";
}

function fmtMoney(n) {
  return "$" + Number(n || 0).toLocaleString("en-US", { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

function fmtPct(n) {
  return Number(n || 0).toFixed(1) + "%";
}

function riskClass(risk) {
  if (risk > 0.7) return "high";
  if (risk > 0.4) return "med";
  return "low";
}

function riskLabel(risk) {
  if (risk > 0.7) return "Visok";
  if (risk > 0.4) return "Srednji";
  return "Nizak";
}

function renderKPIs(d) {
  document.getElementById("kpiGrid").innerHTML = `
    <div class="kpi-card">
      <div class="kpi-label">Ukupni mjesečni prihod</div>
      <div class="kpi-value">${fmtMoney(d.total_monthly_revenue)}</div>
      <div class="kpi-sub">Godišnje: ${fmtMoney(d.total_annual_revenue)}</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Churn rate</div>
      <div class="kpi-value">${fmtPct(d.churn_rate)}</div>
      <div class="kpi-sub">${d.total_customers} korisnika</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Rizični korisnici</div>
      <div class="kpi-value">${d.at_risk_customers}</div>
      <div class="kpi-sub">Rizik &gt; 70%</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Predviđeni gubitak</div>
      <div class="kpi-value">${fmtMoney(d.predicted_loss)}</div>
      <div class="kpi-sub">Prosj. rizik: ${fmtPct(d.avg_risk * 100)}</div>
    </div>
  `;
}

function renderContractChart(data) {
  const ctx = document.getElementById("contractChart");
  if (contractChart) contractChart.destroy();

  contractChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: data.map(d => d.contract),
      datasets: [
        { label: "Stvarni churn %", data: data.map(d => d.churn_rate), backgroundColor: "#c0392b" },
        { label: "Predviđeni rizik %", data: data.map(d => d.avg_predicted_risk), backgroundColor: "#555" },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { position: "top" } },
      scales: { y: { ticks: { callback: v => v + "%" } } },
    },
  });
}

function renderTopRisk(data) {
  if (!data.length) {
    document.getElementById("topRiskTable").innerHTML = '<div class="loading">Nema podataka</div>';
    return;
  }

  document.getElementById("topRiskTable").innerHTML = `
    <table>
      <thead>
        <tr>
          <th>#</th>
          <th>Korisnik</th>
          <th>Ugovor</th>
          <th>Rizik</th>
          <th>Gubitak</th>
          <th>Akcija</th>
        </tr>
      </thead>
      <tbody>
        ${data.map((c, i) => `
          <tr onclick="showDetail('${c.customerID}', null)">
            <td class="rank">${i + 1}</td>
            <td><strong>${c.customerID}</strong></td>
            <td>${c.contract}</td>
            <td><span class="badge ${riskClass(c.risk)}">${fmtPct(c.risk * 100)}</span></td>
            <td class="loss-cell">${fmtMoney(c.expected_loss)}</td>
            <td>${c.best_action}</td>
          </tr>
        `).join("")}
      </tbody>
    </table>
  `;

  renderRetentionSummary(data);
}

function renderRetentionSummary(topCustomers) {
  const actionCounts = {};
  topCustomers.forEach(c => {
    actionCounts[c.best_action] = (actionCounts[c.best_action] || 0) + 1;
  });
  const totalRoi = topCustomers.reduce((s, c) => s + (c.best_roi || 0), 0);

  document.getElementById("retentionSummary").innerHTML = `
    <div class="retention-stat">
      <div class="rs-value">${topCustomers.length}</div>
      <div class="rs-label">Prioritetnih korisnika</div>
    </div>
    <div class="retention-stat">
      <div class="rs-value">${fmtMoney(topCustomers.reduce((s, c) => s + c.expected_loss, 0))}</div>
      <div class="rs-label">Ukupni rizik gubitka</div>
    </div>
    <div class="retention-stat">
      <div class="rs-value">${fmtMoney(totalRoi)}</div>
      <div class="rs-label">Potencijalni ROI</div>
    </div>
    <div class="retention-actions-list">
      ${Object.entries(actionCounts).map(([action, count]) => `
        <div class="retention-action-chip">
          <span>${action}</span>
          <span>${count} korisnika</span>
        </div>
      `).join("")}
    </div>
  `;
}

async function loadKPIs() {
  const r = await apiFetch(`/dashboard/kpis`);
  renderKPIs(await r.json());
}

async function loadContractChart() {
  const r = await apiFetch(`/dashboard/churn-by-contract`);
  renderContractChart(await r.json());
}

async function loadTopRisk() {
  const r = await apiFetch(`/dashboard/top-risk?limit=10`);
  renderTopRisk(await r.json());
}

const PAGE_SIZE = 10;
let customerRows = [];
let customerPage = 1;

async function loadCustomers() {
  const minRisk = document.getElementById("minRisk").value;
  const contract = document.getElementById("contractFilter").value;
  const params = new URLSearchParams({ min_risk: minRisk, contract });
  const r = await apiFetch(`/customers?${params}`);
  customerRows = await r.json();
  customerPage = 1;
  renderCustomerPage();
}

function goToCustomerPage(page) {
  const pages = Math.max(1, Math.ceil(customerRows.length / PAGE_SIZE));
  customerPage = Math.min(Math.max(page, 1), pages);
  renderCustomerPage();
}

function renderCustomerPage() {
  const el = document.getElementById("customerList");
  const pager = document.getElementById("customerPager");

  if (!customerRows.length) {
    el.innerHTML = '<div class="loading">Nema rezultata</div>';
    pager.innerHTML = "";
    return;
  }

  const pages = Math.ceil(customerRows.length / PAGE_SIZE);
  const start = (customerPage - 1) * PAGE_SIZE;
  const rows = customerRows.slice(start, start + PAGE_SIZE);

  el.innerHTML = rows.map(c => {
    const pct = (c.risk * 100).toFixed(0);
    return `
      <div class="list-item" onclick="showDetail('${c.customerID}', this)">
        <div class="top">
          <span class="cid">${c.customerID}</span>
          <span class="badge ${riskClass(c.risk)}">${riskLabel(c.risk)} ${pct}%</span>
        </div>
        <div class="sub">Gubitak: ${fmtMoney(c.expected_loss)} · ${c.contract} · ${c.tenure} mj.</div>
        <div class="sub action-hint">${c.best_action}</div>
      </div>
    `;
  }).join("");
  el.scrollTop = 0;

  pager.innerHTML = `
    <button class="btn btn-sm" onclick="goToCustomerPage(${customerPage - 1})"
            ${customerPage === 1 ? "disabled" : ""}>‹ Prethodna</button>
    <span class="pager-info">Strana ${customerPage} od ${pages}</span>
    <button class="btn btn-sm" onclick="goToCustomerPage(${customerPage + 1})"
            ${customerPage === pages ? "disabled" : ""}>Sljedeća ›</button>
  `;
}

async function showDetail(id, el) {
  if (el) {
    document.querySelectorAll(".list-item").forEach(x => x.classList.remove("active"));
    el.classList.add("active");
  }

  const r = await apiFetch(`/customers/${id}`);
  const c = await r.json();
  if (c.error) return;

  const pct = (c.risk * 100).toFixed(1);
  const color = c.risk > 0.7 ? "#c0392b" : c.risk > 0.4 ? "#b8860b" : "#2e7d32";
  const actions = Object.values(c.actions || {});
  const bestRoi = Math.max(...actions.map(a => a.roi), 0);

  document.getElementById("detail").innerHTML = `
    <h2>${c.customerID}</h2>
    <div class="detail-card">
      <h3>Rizik od odlaska</h3>
      <div class="risk-big" style="color:${color}">${pct}%</div>
      <div class="risk-bar"><div class="risk-fill" style="width:${pct}%;background:${color}"></div></div>
      <p class="detail-meta">
        Predviđeni gubitak: <strong>${fmtMoney(c.expected_loss)}</strong>
        · Ugovor: ${c.contract} · Staž: ${c.tenure} mj. · Mjesečno: ${fmtMoney(c.monthly)}
      </p>
    </div>
    <div class="detail-card">
      <h3>Preporučena akcija</h3>
      <div class="recommended-action">${c.best_action}</div>
      <p class="detail-meta">Očekivani ROI: ${fmtMoney(c.best_roi)}</p>
    </div>
    <div class="detail-card">
      <h3>Ostale opcije</h3>
      <div class="actions">
        ${actions.map(a => `
          <div class="action-row ${a.roi === bestRoi ? 'best' : ''}">
            <div class="name">${a.label}</div>
            <div class="meta">
              Vjerovatnoća nakon: ${(a.new_prob * 100).toFixed(1)}%
              · Trošak: ${fmtMoney(a.cost)}
              · ROI: ${fmtMoney(a.roi)}
            </div>
          </div>
        `).join("")}
      </div>
    </div>
  `;
}

function refreshAll() {
  loadKPIs();
  loadContractChart();
  loadTopRisk();
  loadCustomers();
}

refreshAll();
