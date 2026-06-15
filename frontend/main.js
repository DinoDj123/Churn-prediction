const API = "http://localhost:8000";

async function loadStats() {
  const r = await fetch(`${API}/stats`);
  const d = await r.json();
  document.getElementById("stats").innerHTML = `
    <div class="stat"><div class="num">${d.total}</div><div class="lbl">Korisnika</div></div>
    <div class="stat"><div class="num">${d.high_risk}</div><div class="lbl">Visok rizik (&gt;70%)</div></div>
    <div class="stat"><div class="num">${(d.avg_risk*100).toFixed(1)}%</div><div class="lbl">Prosječni rizik</div></div>
    <div class="stat"><div class="num">$${d.total_expected_loss.toLocaleString()}</div><div class="lbl">Očekivani godišnji gubitak</div></div>
  `;
}

async function loadCustomers() {
  const minRisk = document.getElementById("minRisk").value;
  const contract = document.getElementById("contractFilter").value;
  const params = new URLSearchParams({ min_risk: minRisk, contract });
  const r = await fetch(`${API}/customers?${params}`);
  const customers = await r.json();

  const list = document.getElementById("customerList");
  if (!customers.length) {
    list.innerHTML = '<div class="loading">Nema rezultata</div>';
    return;
  }

  list.innerHTML = customers.map(c => {
    const pct = (c.risk * 100).toFixed(0);
    const cls = c.risk > 0.7 ? "high" : c.risk > 0.4 ? "med" : "low";
    const lbl = c.risk > 0.7 ? "Visok" : c.risk > 0.4 ? "Srednji" : "Nizak";
    return `
      <div class="list-item" onclick="showDetail('${c.customerID}', this)">
        <div class="top">
          <span class="cid">${c.customerID}</span>
          <span class="badge ${cls}">${lbl} ${pct}%</span>
        </div>
        <div class="sub">Gubitak: $${c.expected_loss} · ${c.contract} · ${c.tenure} mj.</div>
      </div>
    `;
  }).join("");
}

async function showDetail(id, el) {
  document.querySelectorAll(".list-item").forEach(x => x.classList.remove("active"));
  el.classList.add("active");

  const r = await fetch(`${API}/customers/${id}`);
  const c = await r.json();

  const pct = (c.risk * 100).toFixed(1);
  const color = c.risk > 0.7 ? "#e74c3c" : c.risk > 0.4 ? "#f39c12" : "#27ae60";

  const actions = Object.values(c.actions || {});
  const bestRoi = Math.max(...actions.map(a => a.roi));

  const actionsHtml = actions.map(a => `
    <div class="action-row ${a.roi === bestRoi ? 'best' : ''}">
      <div class="name">${a.label}</div>
      <div class="meta">
        Vjerovatnoća nakon: ${(a.new_prob*100).toFixed(1)}%
        · Trošak: $${a.cost}
        · ROI: <strong style="color:${a.roi>0?'#27ae60':'#e74c3c'}">$${a.roi}</strong>
      </div>
    </div>
  `).join("");

  const factors = (c.top_factors || []).map(f => `
    <li><span class="dot"></span>${f.replace(/_/g, " ")}</li>
  `).join("");

  document.getElementById("detail").innerHTML = `
    <h2>Korisnik: ${c.customerID}</h2>

    <div class="detail-card">
      <h3>Rizik od odlaska</h3>
      <div style="font-size:28px;font-weight:bold;color:${color};margin-bottom:8px">${pct}%</div>
      <div class="risk-bar-wrap">
        <div class="risk-bar"><div class="risk-fill" style="width:${pct}%;background:${color}"></div></div>
      </div>
      <p style="font-size:12px;color:#666;margin-top:8px">
        Očekivani godišnji gubitak: <strong>$${c.expected_loss}</strong>
        · Ugovor: ${c.contract} · Staž: ${c.tenure} mj. · Mjesečno: $${c.monthly}
      </p>
    </div>

    <div class="detail-card">
      <h3>Ključni faktori rizika</h3>
      <ul class="factors">${factors}</ul>
    </div>

    <div class="detail-card">
      <h3>Preporučene akcije</h3>
      <div class="actions">${actionsHtml}</div>
    </div>
  `;
}

loadStats();
loadCustomers();