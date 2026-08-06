"use strict";

const cookieValue = (name) => document.cookie.split("; ").find((part) => part.startsWith(`${name}=`))?.split("=").slice(1).join("=") || "";
const state = { review: null, result: null, csrfToken: cookieValue("mlai_csrf"), idToken: "", identityConfig: null };
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
  byId("positioningStatus").textContent = data.positioning.ready ? "Approved positioning ready" : data.positioning.reason;
  byId("strategyStatus").textContent = data.strategy.ready ? "Approved Strategy ready" : data.strategy.reason;
  renderDefinitionList(byId("campaignSummary"), data.campaign_plan);
  renderDefinitionList(byId("briefSummary"), data.marketing_brief);
  renderDefinitionList(byId("positioningSummary"), data.positioning);
  renderDefinitionList(byId("strategySummary"), data.strategy);
  byId("campaignNotes").value = data.campaign_plan.notes || "";
  byId("briefNotes").value = data.marketing_brief.notes || "";
  byId("generateAsset").disabled = !data.generation_ready;
}

async function loadWorkflow() {
  try {
    const data = await api("/v1/pilot/workflow-review", { brand_id:value("brandId"), campaign_id:value("campaignId"), brief_id:value("briefId") });
    renderReview(data); message(data.generation_ready ? "Positioning, Strategy, plan, and brief are approved and ready." : "Approved Positioning, Strategy, Campaign Plan, and Marketing Brief are required before generation.");
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

function identityMessage(text, error = false) {
  const target = byId("identityMessage");
  target.textContent = text;
  target.className = `message ${error ? "error" : "success"}`;
}

function loadGoogleIdentity() {
  return new Promise((resolve, reject) => {
    if (window.google?.accounts?.id) return resolve();
    const script = document.createElement("script");
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.onload = resolve;
    script.onerror = () => reject(new Error("Google sign-in could not be loaded."));
    document.head.append(script);
  });
}

async function exchangeGoogleCredential(credential) {
  const endpoint = `https://identitytoolkit.googleapis.com/v1/accounts:signInWithIdp?key=${encodeURIComponent(state.identityConfig.api_key)}`;
  const response = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      postBody: new URLSearchParams({ id_token: credential, providerId: "google.com" }).toString(),
      requestUri: window.location.origin,
      returnIdpCredential: true,
      returnSecureToken: true
    })
  });
  const payload = await response.json();
  if (!response.ok || !payload.idToken) throw new Error(payload.error?.message || "Identity Platform rejected the Google credential.");
  state.idToken = payload.idToken;
  byId("claimInvitation").disabled = false;
  byId("connectSession").disabled = false;
  identityMessage("Google identity verified. Claim an invitation or connect an existing tenant.");
}

async function initializeIdentity() {
  try {
    const response = await fetch("/v1/pilot/identity/config", { credentials: "same-origin", cache: "no-store" });
    if (!response.ok) throw new Error("Public identity configuration is unavailable.");
    state.identityConfig = await response.json();
    await loadGoogleIdentity();
    window.google.accounts.id.initialize({
      client_id: state.identityConfig.oauth_client_id,
      callback: async ({ credential }) => {
        try { await exchangeGoogleCredential(credential); }
        catch (error) { identityMessage(error.message, true); }
      }
    });
    window.google.accounts.id.renderButton(byId("googleSignIn"), { theme: "outline", size: "large", text: "signin_with" });
    identityMessage("Use an approved OAuth test account to continue.");
  } catch (error) { identityMessage(error.message, true); }
}

async function claimInvitation() {
  try {
    const response = await fetch("/v1/pilot/design-partner/signup", {
      method: "POST",
      headers: { "Authorization": `Bearer ${state.idToken}`, "Content-Type": "application/json" },
      body: JSON.stringify({
        partner_name:value("signupPartner"),
        invitation_code:value("invitationCode"),
        privacy_notice_accepted:byId("privacyConsent").checked,
        synthetic_data_boundary_accepted:byId("syntheticConsent").checked
      })
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error?.message || "Invitation claim failed.");
    byId("tenantId").value = payload.data.tenant_id;
    byId("invitationCode").value = "";
    identityMessage("Founder invitation claimed. Connect the isolated pilot tenant to continue.");
  } catch (error) { identityMessage(error.message, true); }
}

async function connectSession() {
  try {
    const response = await fetch("/v1/pilot/session", {
      method: "POST",
      headers: { "Authorization": `Bearer ${state.idToken}`, "X-Tenant-ID": value("tenantId") },
      credentials: "same-origin"
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error?.message || "Pilot session could not be created.");
    state.csrfToken = payload.csrf_token;
    state.idToken = "";
    byId("onboarding").hidden = false;
    byId("connectSession").disabled = true;
    byId("claimInvitation").disabled = true;
    identityMessage("Secure tenant-bound session established. Google token cleared from browser memory.");
  } catch (error) { identityMessage(error.message, true); }
}

async function assessPartner() {
  try {
    const data = await api("/v1/pilot/design-partner/readiness", {
      partner_name:value("partnerName"),
      evidence:{
        founder_approval:byId("founderApproval").checked,
        privacy_choices_complete:byId("privacyReady").checked,
        external_identity_ready:byId("identityReady").checked,
        backup_recovery_rehearsed:byId("recoveryReady").checked,
        support_owner_assigned:byId("supportReady").checked,
        data_boundary_accepted:byId("dataBoundaryReady").checked
      }
    });
    renderDefinitionList(byId("partnerReadiness"), data);
    message(data.ready_for_activation_decision ? "Readiness evidence is complete. Real-data activation remains a separate founder decision." : "Synthetic rehearsal may continue; real-data activation blockers remain visible.");
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
byId("assessPartner").addEventListener("click", assessPartner);
byId("claimInvitation").addEventListener("click", claimInvitation);
byId("connectSession").addEventListener("click", connectSession);
initializeIdentity();
