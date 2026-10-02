const phases = [
  {
    number: "PHASE 00",
    title: "Baseline, environment & claim discipline",
    description: "Establish a reproducible starting point and make every portfolio claim traceable before downstream implementation begins.",
    deliverables: ["Execute the 46-test source validation", "Create environment and one-command targets", "Open decision, execution and claims registers", "Scan tracked text for secrets and false claims"],
    gate: "46 baseline checks pass, zero secrets are tracked, and every stated outcome is explicitly synthetic."
  },
  {
    number: "PHASE 01",
    title: "Data profiling & analytical contract",
    description: "Turn operational files into an explicit contract covering grain, ownership, cardinality, null behavior and KPI logic.",
    deliverables: ["Profile every table and column", "Define facts and conformed dimensions", "Map source-to-star relationships", "Publish metric definitions and denominator rules"],
    gate: "Every source has a grain and key; every relationship has an expected cardinality and automated assertion."
  },
  {
    number: "PHASE 02",
    title: "PostgreSQL warehouse & analytics",
    description: "Build an idempotent, typed warehouse that protects transactional grain and exposes decision-ready procurement marts.",
    deliverables: ["Raw, staging, core, mart, audit and RAG schemas", "Spend, delivery, exception, payment and quality facts", "Three-way match without fanout", "20+ decision-grade SQL analyses"],
    gate: "A fresh database loads twice without duplication; marts reconcile within INR 0.01 and query plans use suitable indexes."
  },
  {
    number: "PHASE 03",
    title: "Power BI semantic decision layer",
    description: "Create a governed star model and eight pages that move from executive signals to record-level investigation.",
    deliverables: ["24+ documented DAX measures", "Eight report pages and drill-through", "Power Query parameters and refresh plan", "RLS for executive, category, AP and audit roles"],
    gate: "Every KPI ties to SQL, relationships are unambiguous, RLS is tested, and each page answers a named decision."
  },
  {
    number: "PHASE 04",
    title: "Invoice anomaly ranking",
    description: "Rank investigative leads using point-in-time evidence and review-capacity metrics rather than misleading aggregate accuracy.",
    deliverables: ["Leakage-safe invoice feature set", "Rules, logistic and tree-model baselines", "Chronological train / validation / test", "Calibrated score, risk band and reason codes"],
    gate: "Leakage tests pass; the test window remains untouched during tuning; the threshold is tied to review capacity."
  },
  {
    number: "PHASE 05",
    title: "Supplier delay & composite risk",
    description: "Predict late delivery from order-time evidence and publish a separate transparent, confidence-aware supplier risk score.",
    deliverables: ["Point-in-time supplier history", "Grouped and time-aware evaluation", "Calibrated delay probabilities", "Weighted delivery, quality, commercial and incident score"],
    gate: "No post-order evidence enters features; cohort metrics and small-sample confidence are visible."
  },
  {
    number: "PHASE 06",
    title: "Contract & policy RAG",
    description: "Retrieve contract and policy evidence through hybrid search, answer with page-level citations and abstain when evidence is weak.",
    deliverables: ["Page-aware extraction and chunking", "Lexical + vector retrieval with metadata filters", "Strict answer, citation and confidence contract", "100+ answerable, adversarial and abstention tests"],
    gate: "No substantive evaluated answer is uncited; unsupported questions abstain and prompt injection cannot override controls."
  },
  {
    number: "PHASE 07",
    title: "Read-only analyst API",
    description: "Expose metrics, investigation traces, model scores and cited contract answers through safe typed interfaces.",
    deliverables: ["FastAPI health, metrics and record endpoints", "Invoice and delay scoring endpoints", "Contract question endpoint with citations", "Pagination, typed errors, correlation IDs and logs"],
    gate: "Input, authorization, timeout and integration tests pass; no SQL injection or arbitrary file access is possible."
  },
  {
    number: "PHASE 08",
    title: "n8n exception-triage agent",
    description: "Enrich, explain and route invoice exceptions while enforcing idempotency, confidence thresholds and a human decision.",
    deliverables: ["Credential-free importable workflow", "Evidence enrichment and investigation brief", "Retry, dead-letter and duplicate suppression", "60+ normal, failure and adversarial fixtures"],
    gate: "Replay creates no duplicate case, every branch ends audibly, and the human gate is technically enforced."
  },
  {
    number: "PHASE 09",
    title: "Power Automate approval",
    description: "Present ranked evidence to a named approver and return an auditable outcome without embedding environment-specific secrets.",
    deliverables: ["Validated intake and idempotency", "Evidence-rich adaptive approval card", "Approve, reject, information, timeout and escalation paths", "Callback and audit persistence"],
    gate: "Duplicate events do not duplicate approval; timeout, rejection and API-failure branches have evidence."
  },
  {
    number: "PHASE 10",
    title: "Observability, security & release",
    description: "Monitor the data, models, retrieval, API and workflows as one operating system—and design for recovery.",
    deliverables: ["Freshness, drift, calibration and latency signals", "RAG citation and abstention monitoring", "Threat model and prohibited-action tests", "Clean build, dependency scan and rollback runbooks"],
    gate: "A clean run passes all tests, no high-severity secret finding remains, and model and prompt versions reproduce."
  },
  {
    number: "PHASE 11",
    title: "Recruiter-grade portfolio proof",
    description: "Convert the engineering system into a concise, honest case study that lets a reviewer verify every claimed capability.",
    deliverables: ["Architecture and lineage diagrams", "Demo and technical walkthrough", "Skills-to-artifacts matrix", "Evidence-backed resume bullets and limitations"],
    gate: "Every portfolio claim maps to a file, test or reproducible metric; no synthetic evaluation is presented as production impact."
  }
];

const panel = document.getElementById("phasePanel");
const tabs = [...document.querySelectorAll(".phase-tab")];

function renderPhase(index) {
  const phase = phases[index];
  const statuses = [
    "VERIFIED FOUNDATION",
    "DATA CONTRACT VERIFIED",
    "POSTGRESQL BUILT · 68 SQL TESTS",
    "PBIX BUILT · 28/28 KPIs RECONCILED",
    "MODEL PASSED · NO LIFT OVER REFINED RULES",
    "MODEL PASSED · NO LIFT OVER BASELINE",
    "RAG 151/151 · UNSEEN FIRST RUN 56%",
    "API PASSED · 27 TESTS",
    "WORKFLOW PASSED · 67 FIXTURES",
    "ALL BRANCHES EXECUTED · TENANT PENDING",
    "0 SECRETS · RESTORE DRILL PASSED",
    "EVIDENCE UPDATED · DEMO PENDING"
  ];
  const status = statuses[index];
  panel.innerHTML = `
    <div class="phase-meta"><span class="phase-number">${phase.number}</span><span class="phase-status">${status}</span></div>
    <h3>${phase.title}</h3>
    <p>${phase.description}</p>
    <div class="phase-deliverables">${phase.deliverables.map(item => `<span>${item}</span>`).join("")}</div>
    <div class="phase-gate"><small>QUALITY GATE</small><b>${phase.gate}</b></div>`;
  tabs.forEach((tab, tabIndex) => {
    const active = tabIndex === index;
    tab.classList.toggle("active", active);
    tab.setAttribute("aria-selected", String(active));
    tab.setAttribute("tabindex", active ? "0" : "-1");
  });
  panel.setAttribute("aria-labelledby", tabs[index].id);
}

tabs.forEach((tab, index) => {
  tab.id = `phase-tab-${index}`;
  tab.setAttribute("aria-controls", "phasePanel");
  tab.addEventListener("click", () => renderPhase(index));
  tab.addEventListener("keydown", (event) => {
    if (!["ArrowDown", "ArrowUp", "ArrowRight", "ArrowLeft", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    const direction = ["ArrowDown", "ArrowRight"].includes(event.key) ? 1 : -1;
    const next = event.key === "Home" ? 0 : event.key === "End" ? tabs.length - 1 : (index + direction + tabs.length) % tabs.length;
    tabs[next].focus();
    renderPhase(next);
  });
});
renderPhase(0);

const releases = [
  { number: "01", title: "Decision-ready warehouse", description: "Conformed outputs, seven decision marts and reconciliation tests protect transaction grain from source through analysis.", evidence: "PostgreSQL 16 · 24 decision analyses", gate: "68 SQL tests passed twice", boundary: "Local Docker run, not a hosted server" },
  { number: "02", title: "Governed semantic layer", description: "A nine-page Power BI report (a briefing plus eight decision pages), built in Desktop and published live, connects decision questions to explicit measures, relationships, parameters and role rules.", evidence: "32 DAX measures · 5 security roles", gate: "28/28 KPIs · 7/7 RLS cases", boundary: "Not published to a Power BI tenant" },
  { number: "03", title: "Risk ranking with context", description: "Chronological models publish probabilities, review-capacity metrics, calibration, cohort behavior, reason codes and versioned scores.", evidence: "Invoice 1.00 vs rules 0.48 · Delay 0.56 vs 0.56", gate: "Leakage + calibration checks passed", boundary: "Injected anomalies are rule-detectable: no model lift claimed" },
  { number: "04", title: "Citation-first retrieval", description: "Document-scoped extraction prevents cross-contract contamination; conflicts, missing evidence and prompt injection have explicit safe outcomes.", evidence: "402 PDFs · 3,772 chunks", gate: "151/151 tuned cases · 56% on first unseen run", boundary: "Tuned on its own evaluation set; unseen accuracy reported as is" },
  { number: "05", title: "Read-only evidence API", description: "Authenticated endpoints expose scores, traces, pagination, readiness, versions and cited answers with request-level correlation IDs.", evidence: "Health · metrics · traces · RAG", gate: "27 tests passed", boundary: "Local service, not a public production API" },
  { number: "06", title: "Resilient triage orchestration", description: "A credential-free n8n export enriches evidence, suppresses replay, retries failures and pauses at a true wait/resume human gate.", evidence: "42 nodes · 67 fixtures", gate: "Normal + failure + adversarial paths", boundary: "Live instance import pending" },
  { number: "07", title: "Human decision, fully audited", description: "The approval design covers approve, reject, needs-information, timeout, callback failure and immutable audit fields—without executing payment.", evidence: "12 audit fields · 4 prohibited actions", gate: "Every branch executed in simulation", boundary: "Microsoft tenant connection pending" },
  { number: "08", title: "Release evidence that can be rerun", description: "Profiles, manifests, SBOM, secret scan, drift checks and per-gate logs are composed into one local regression command.", evidence: "One command · about 10 minutes", gate: "12 / 12 phase gates passed", boundary: "Native cross-system demo pending" }
];
const releasePanel = document.getElementById("releasePanel");
const releaseTabs = [...document.querySelectorAll(".release-tab")];
function renderRelease(index) {
  const item = releases[index];
  releasePanel.innerHTML = `<div><span>RELEASE ${item.number} · VERIFIED</span><h3>${item.title}</h3><p>${item.description}</p></div><dl><div><dt>EVIDENCE</dt><dd>${item.evidence}</dd></div><div><dt>GATE</dt><dd>${item.gate}</dd></div><div><dt>BOUNDARY</dt><dd>${item.boundary}</dd></div></dl>`;
  releaseTabs.forEach((tab, i) => {
    const active=i===index;
    tab.classList.toggle("active",active);
    tab.setAttribute("aria-selected",String(active));
    tab.setAttribute("tabindex",active?"0":"-1");
  });
  releasePanel.setAttribute("aria-labelledby", releaseTabs[index].id);
}
releaseTabs.forEach((tab,index)=>{
  tab.id=`release-tab-${index}`;
  tab.setAttribute("aria-controls","releasePanel");
  tab.addEventListener("click",()=>renderRelease(index));
  tab.addEventListener("keydown",event=>{
    if(!["ArrowDown","ArrowUp","ArrowRight","ArrowLeft","Home","End"].includes(event.key)) return;
    event.preventDefault();
    const direction=["ArrowDown","ArrowRight"].includes(event.key)?1:-1;
    const next=event.key==="Home"?0:event.key==="End"?releaseTabs.length-1:(index+direction+releaseTabs.length)%releaseTabs.length;
    releaseTabs[next].focus();renderRelease(next);
  });
});
renderRelease(0);

const cockpitViews = [
  () => `<div class="pulse-kpis">
      <article><small>REALIZED NET SPEND</small><strong>₹9.89B</strong><span>48,000 invoices</span></article>
      <article><small>OFF-CONTRACT SPEND</small><strong>₹4.27B</strong><span>43.1% of net spend</span></article>
      <article><small>LINE-WEIGHTED OTIF</small><strong>54.0%</strong><span>217,377 eligible lines</span></article>
      <article><small>EXCEPTION VALUE</small><strong>₹5.32B</strong><span>20,256 invoice exceptions</span></article>
    </div>
    <div class="pulse-grid">
      <article class="pulse-chart"><div class="view-label"><span>DECISION SIGNAL</span><b>Service reliability needs intervention</b></div>
        <div class="service-bars"><div><span>On time</span><i><b style="--value:60.9%"></b></i><strong>60.9%</strong></div><div><span>In full</span><i><b style="--value:88.7%"></b></i><strong>88.7%</strong></div><div><span>OTIF</span><i><b class="critical" style="--value:54%"></b></i><strong>54.0%</strong></div></div>
      </article>
      <article class="priority-card"><div class="view-label"><span>PRIORITY QUEUE</span><b>What should leadership ask next?</b></div>
        <ol><li><b>01</b><span>Which suppliers drive missed OTIF?</span><i>Supplier 360 →</i></li><li><b>02</b><span>Where is off-contract spend concentrated?</span><i>Category view →</i></li><li><b>03</b><span>Which invoices need review first?</span><i>Exception queue →</i></li></ol>
      </article>
    </div>`,
  () => `<div class="workbench-grid">
      <article class="queue-panel"><div class="queue-head"><span>REVIEW QUEUE</span><small>open critical cases · largest exposure first</small></div>
        <div class="queue-row active"><b>INV0036211</b><span>SUP0091 · ₹1,502,606.93</span><i>CRITICAL</i></div>
        <div class="queue-row"><b>INV0003173</b><span>SUP0074 · ₹1,481,091.51</span><i>CRITICAL</i></div>
        <div class="queue-row"><b>INV0027594</b><span>SUP0124 · ₹1,204,303.02</span><i>CRITICAL</i></div>
        <div class="queue-row"><b>INV0019880</b><span>SUP0055 · ₹1,193,826.41</span><i>CRITICAL</i></div>
        <div class="queue-row"><b>INV0001446</b><span>SUP0052 · ₹1,165,263.64</span><i>CRITICAL</i></div>
      </article>
      <article class="case-panel"><div class="case-head"><span>SELECTED CASE</span><small>2025 chronological holdout</small></div>
        <div class="case-summary"><div><small>INV0036211 · SUMMIT TRADING 91</small><h3>Evidence before action</h3><p>The model ranks the case; deterministic controls explain why a human must review it.</p></div><div class="risk-chip"><strong style="font-size:1.25rem">CRITICAL</strong><small>RISK BAND</small></div></div>
        <div class="case-facts"><div><small>GROSS EXPOSURE</small><b>₹1,502,606.93</b></div><div><small>PRIMARY REASON</small><b>Missing PO reference</b></div><div><small>SECOND REASON</small><b>Above ₹10 lakh</b></div><div><small>PAYMENT STATE</small><b>Unpaid · fully exposed</b></div></div>
        <div class="case-outcome"><span>Observed workflow outcome</span><strong>REQUEST INFORMATION · 114 HOURS</strong></div>
      </article>
    </div>`,
  () => `<div class="rag-layout">
      <article class="rag-query"><span>REVIEWER QUESTION</span><blockquote>“What is the termination notice period in contract CTR00142?”</blockquote><div class="query-meta"><span>DOCUMENT FILTER · CTR00142</span><span>TYPE · CONTRACT</span><span>MODE · HYBRID</span></div></article>
      <article class="rag-answer"><div class="rag-head"><span>GROUNDED ANSWER</span><small>citation validator passed</small></div><span class="answer-state">ANSWERED · HIGH CONFIDENCE</span><h3>45 days</h3><p>The answer is extracted from the scoped contract rather than generated from general knowledge. If supporting text is missing or contradictory, the system abstains.</p><div class="citation-proof"><b>Exact evidence path</b><span>[documents/contracts/CTR00142.pdf, page 1]</span></div><div class="safety-strip"><span>✓ DOCUMENT SCOPED</span><span>✓ PAGE CITED</span><span>✓ INJECTION REFUSED</span></div></article>
    </div>`,
  () => `<div class="approval-layout">
      <article class="approval-map"><div class="approval-head"><span>CONTROLLED AUTOMATION</span><small>agent drafts · human decides</small></div><div class="approval-flow"><div><small>01 · n8n</small><b>Validate and deduplicate event</b></div><div><small>02 · EVIDENCE</small><b>Enrich score, reasons and citation</b></div><div class="human"><small>03 · HUMAN GATE</small><b>Approve, reject or request information</b></div><div><small>04 · AUDIT</small><b>Persist outcome and correlation ID</b></div></div></article>
      <article class="approval-detail"><div class="approval-head"><span>GOVERNANCE PROOF</span><small>verified fixtures</small></div><dl><div><dt>n8n paths</dt><dd class="pass">67 PASSED</dd></div><div><dt>Approval branches</dt><dd class="pass">ALL EXECUTED</dd></div><div><dt>Idempotent replay</dt><dd class="pass">ENFORCED</dd></div><div><dt>Retries + dead letter</dt><dd class="pass">TESTED</dd></div><div><dt>Autonomous payment</dt><dd>PROHIBITED</dd></div><div><dt>Native cloud run</dt><dd>PENDING</dd></div></dl></article>
    </div>`
];

const cockpitView = document.getElementById("cockpitView");
const cockpitTabs = [...document.querySelectorAll(".cockpit-tab")];
function renderCockpit(index) {
  cockpitView.innerHTML = cockpitViews[index]();
  cockpitTabs.forEach((tab, tabIndex) => {
    const active = tabIndex === index;
    tab.classList.toggle("active", active);
    tab.setAttribute("aria-selected", String(active));
    tab.setAttribute("tabindex", active ? "0" : "-1");
  });
  cockpitView.setAttribute("aria-labelledby", cockpitTabs[index].id);
}
cockpitTabs.forEach((tab, index) => {
  tab.id = `cockpit-tab-${index}`;
  tab.setAttribute("aria-controls", "cockpitView");
  tab.addEventListener("click", () => renderCockpit(index));
  tab.addEventListener("keydown", event => {
    if (!["ArrowRight", "ArrowLeft", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    const next = event.key === "Home" ? 0 : event.key === "End" ? cockpitTabs.length - 1 : (index + (event.key === "ArrowRight" ? 1 : -1) + cockpitTabs.length) % cockpitTabs.length;
    cockpitTabs[next].focus();
    renderCockpit(next);
  });
});
renderCockpit(0);

const fullSpecDetails = document.getElementById("fullSpecDetails");
const fullSpecContent = document.getElementById("fullSpecContent");
let specificationLoaded = false;
fullSpecDetails.addEventListener("toggle", async () => {
  if (!fullSpecDetails.open || specificationLoaded) return;
  try {
    const response = await fetch("technical-specification.md");
    if (!response.ok) throw new Error("Specification unavailable");
    fullSpecContent.textContent = await response.text();
    specificationLoaded = true;
  } catch (error) {
    fullSpecContent.textContent = "The full specification could not be loaded in this view.";
  }
});

const revealObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add("visible");
      revealObserver.unobserve(entry.target);
    }
  });
}, { threshold: .12 });
document.querySelectorAll(".reveal").forEach(element => revealObserver.observe(element));

const scrollBar = document.getElementById("scrollBar");
function updateProgress() {
  const max = document.documentElement.scrollHeight - window.innerHeight;
  scrollBar.style.width = `${max > 0 ? (window.scrollY / max) * 100 : 0}%`;
}
window.addEventListener("scroll", updateProgress, { passive: true });
updateProgress();
