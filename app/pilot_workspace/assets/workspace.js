"use strict";

const cookieValue = (name) => document.cookie.split("; ").find((part) => part.startsWith(`${name}=`))?.split("=").slice(1).join("=") || "";
const state = { review: null, result: null, csrfToken: cookieValue("mlai_csrf") };
const byId = (id) => document.getElementById(id);
const value = (id) => byId(id).value.trim();
const requestKey = (operation) => `${operation}-${crypto.randomUUID()}`;

async function api(path, body, operation = "") {
  const headers = { "Content-Type": "application/json", "X-Tenant-ID": value("tenantId"), "X-CSRF-Token": state.csrfToken };
  if (operation) headers["Idempotency-Key"] = requestKey(operation);
  const response = await fetch(path, { method: "POST", headers, credentials: "same-origin", body: JSON.stringify(body) });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error?.message || "The pilot request failed.");
  return payload.data;
}

function message(text, error = false) {
  const target = byId("workspaceMessage");
  target.textContent = text;
  target.className = `message ${error ? "error" : "success"}`;
}

function renderDefinitionList(target, values) {
  target.replaceChildren();
  Object.entries(values).forEach(([name, raw]) => {
    const term = document.createElement("dt");
    const detail = document.createElement("dd");
    term.textContent = name.replaceAll("_", " ");
    detail.textContent = typeof raw === "object" ? JSON.stringify(raw) : String(raw || "Not provided");
    target.append(term, detail);
  });
}

function renderReview(data) {
  state.review = data;
  byId("contextPanel").hidden = false;
  byId("reviewPanel").hidden = false;
  byId("generationPanel").hidden = false;
  const indicators = byId("contextIndicators");
  indicators.replaceChildren();
  Object.entries(data.context.missing).forEach(([name, missing]) => {
    const card = document.createElement("div");
    card.className = `indicator ${missing ? "missing" : ""}`;
    card.textContent = `${name}: ${missing ? "Missing" : "Available"}`;
    indicators.append(card);
  });
  byId("campaignStatus").textContent = `Version ${data.campaign_plan.version} · ${data.campaign_plan.status}`;
  byId("briefStatus").textContent = `Version ${data.marketing_brief.version} · ${data.marketing_brief.status}`;
  renderDefinitionList(byId("campaignSummary"), data.campaign_plan);
  renderDefinitionList(byId("briefSummary"), data.marketing_brief);
  byId("campaignNotes").value = data.campaign_plan.notes || "";
  byId("briefNotes").value = data.marketing_brief.notes || "";
  byId("generateAsset").disabled = !data.generation_ready;
}

async function loadWorkflow() {
  try {
    const data = await api("/v1/pilot/workflow-review", { brand_id:value("brandId"), campaign_id:value("campaignId"), brief_id:value("briefId") });
    renderReview(data); message(data.generation_ready ? "Workflow is approved and ready." : "Review and approve both governance artifacts before generation.");
  } catch (error) { message(error.message, true); }
}

async function saveOnboarding() {
  try {
    await api("/v1/pilot/onboarding/context", {
      brand_id:value("brandId"),
      business:{ revenue_model:value("revenueModel"), geographic_markets:[value("market")], business_goals:[value("businessGoal")] },
      customer:{ segment_id:value("segmentId"), name:value("segmentName"), summary:value("customerSummary"), description:value("customerSummary"), evidence_source:value("customerEvidence") },
      product:{ product_id:value("productId"), name:value("productName"), product_type:value("productType"), evidence_source:value("productEvidence"), features:[], benefits:[], limitations:[], prohibited_claims:[] }
    }, "onboarding");
    message("Verified synthetic context saved. Load the workflow to refresh readiness.");
  } catch (error) { message(error.message, true); }
}

async function lifecycle(resource, action, version, changes = null) {
  const plural = resource === "campaign-plans" ? "campaign-plans" : "marketing-briefs";
  const id = resource === "campaign-plans" ? value("campaignId") : value("briefId");
  const body = changes ? { expected_version:version, changes } : { expected_version:version };
  await api(`/v1/pilot/${plural}/${encodeURIComponent(id)}/${action}`, body, `${action}-${resource}`);
  await loadWorkflow();
}

async function generate() {
  const plan = state.review.campaign_plan, brief = state.review.marketing_brief;
  try {
    state.result = await api("/v1/pilot/generate", { brand_id:value("brandId"), campaign_id:plan.campaign_id, campaign_version:plan.version, brief_id:brief.brief_id, brief_version:brief.version, task:value("generationTask"), instructions:value("generationInstructions") }, "generate");
    byId("resultPanel").hidden = false;
    byId("generatedContent").textContent = state.result.content;
    renderDefinitionList(byId("complianceResult"), state.result.compliance);
    const limitations = byId("limitations"); limitations.replaceChildren();
    state.result.limitations.forEach((text) => { const item=document.createElement("li"); item.textContent=text; limitations.append(item); });
    renderDefinitionList(byId("auditMetadata"), state.result.audit);
    message("Generated content is ready for human and compliance review.");
  } catch (error) { message(error.message, true); }
}

async function safeExport() {
  try {
    await api("/v1/pilot/exports/authorize", { resource_type:"campaign_plan", resource_id:value("campaignId") }, "export");
    const blob = new Blob([JSON.stringify(state.result, null, 2)], { type:"application/json" });
    const link = document.createElement("a"); link.href=URL.createObjectURL(blob); link.download=`marketinglabai-${state.result.asset_id}.json`; link.click(); URL.revokeObjectURL(link.href);
    message("Safe review record exported. Nothing was published.");
  } catch (error) { message(error.message, true); }
}

byId("loadWorkflow").addEventListener("click", loadWorkflow);
byId("saveOnboarding").addEventListener("click", saveOnboarding);
byId("approveCampaign").addEventListener("click", () => lifecycle("campaign-plans", "approve", state.review.campaign_plan.version));
byId("approveBrief").addEventListener("click", () => lifecycle("marketing-briefs", "approve", state.review.marketing_brief.version));
byId("reviseCampaign").addEventListener("click", () => lifecycle("campaign-plans", "revise", state.review.campaign_plan.version, { notes:value("campaignNotes") }));
byId("reviseBrief").addEventListener("click", () => lifecycle("marketing-briefs", "revise", state.review.marketing_brief.version, { notes:value("briefNotes") }));
byId("generateAsset").addEventListener("click", generate);
byId("reviseGeneration").addEventListener("click", () => { byId("generationInstructions").focus(); byId("resultPanel").hidden=true; });
byId("safeExport").addEventListener("click", safeExport);
