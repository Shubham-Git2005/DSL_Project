"use strict";

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const state = { evidence: [], capabilities: null, apiKey: "", report: null, activeId: null, history: [], pollTimer: null, deleteId: null, example: false };
const names = {project: "Project", internship: "Internship", certification: "Certification", coding: "Coding", communication: "Communication"};
const icons = {project: "code", internship: "briefcase", certification: "award", coding: "code", communication: "chat"};
const roles = {junior_backend: "Junior backend developer", junior_frontend: "Junior frontend developer", junior_data: "Junior data analyst"};
const labels = {foundation_developing: "Foundation developing", developing_independence: "Developing independence", entry_level_ready: "Entry level ready"};
const tierNames = {foundation:"Foundation", applied:"Applied", independent:"Independent", advanced:"Advanced", unknown:"Level unknown"};
const categories = {supported: "Supported by source", partial: "Partial evidence", not_demonstrated: "Limitation stated", unknown: "Unknown"};
const escapeHTML = (value) => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;"}[c]));
const icon = name => `<svg aria-hidden="true"><use href="#i-${name}"/></svg>`;
const humanDate = value => new Intl.DateTimeFormat(undefined, {day:"numeric",month:"short",hour:"2-digit",minute:"2-digit"}).format(new Date(value));

function announce(message) {
  $("#toast").textContent = message;
  $("#toast").hidden = false;
  clearTimeout(announce.timer);
  announce.timer = setTimeout(() => { $("#toast").hidden = true; }, 4000);
}

function showError(message, target = "#global-error") {
  const element = $(target);
  element.textContent = message;
  element.hidden = !message;
}

async function api(path, options = {}) {
  const headers = {"Content-Type": "application/json", ...options.headers};
  if (state.apiKey) headers["X-API-Key"] = state.apiKey;
  const response = await fetch(path, {...options, headers});
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    let detail = body.detail;
    if (Array.isArray(detail)) detail = detail.map(item => `${item.loc.slice(1).join(" → ")}: ${item.msg}`).join("; ");
    if (response.status === 401) detail = "This workspace requires an API key. Open workspace access to reconnect.";
    throw new Error(typeof detail === "string" ? detail : `Request failed (HTTP ${response.status}).`);
  }
  return response.status === 204 ? null : response.json();
}

function navigate(view, updateHash = true) {
  if (!["workspace", "history", "models", "api"].includes(view)) view = "workspace";
  $$(".view").forEach(element => { element.hidden = element.id !== `view-${view}`; });
  $$(".nav-item").forEach(button => {
    const current = button.dataset.view === view;
    button.classList.toggle("active", current);
    if (current) button.setAttribute("aria-current", "page"); else button.removeAttribute("aria-current");
  });
  $("#page-crumb").textContent = {workspace:"Overview", history:"Assessment history", models:"Model lab", api:"API & integration"}[view];
  if (updateHash) history.replaceState(null, "", `#${view}`);
  if (view === "history") refreshHistory();
  if (view === "models") renderModels();
}

async function connect() {
  try {
    state.capabilities = await api("/v2/capabilities");
    $("#connection-status").textContent = "Workspace connected";
    $("#connection-status").className = "connection online";
    const semantic = state.capabilities.semantic_evaluator;
    $("#evaluator-status").textContent = semantic ? "Semantic available" : "Offline scan";
    $("#evaluator-status").className = `badge ${semantic ? "" : "muted"}`;
    $("#model-status").textContent = state.capabilities.model.available ? "Experimental" : "Awaiting labels";
    $("#status-explanation").textContent = semantic ? "Semantic assessment is available. Source claims still require independent verification." : "Offline mode locates relevant wording. Add a server-side LLM key for semantic assessment.";
    showError("");
    renderModels();
    await refreshHistory();
  } catch (error) {
    $("#connection-status").textContent = "Connection needed";
    $("#connection-status").className = "connection error-state";
    showError(error.message);
  }
}

function evidenceEditor(item, index, open = false) {
  return `<details class="evidence-item" data-id="${item.id}" ${open ? "open" : ""}>
    <summary class="evidence-summary"><span class="evidence-icon">${icon(icons[item.kind])}</span><span class="evidence-text"><strong>${escapeHTML(item.title || `Untitled ${names[item.kind].toLowerCase()}`)}</strong><small>${names[item.kind]} · Student supplied</small></span>${icon("chevron")}</summary>
    <div class="evidence-editor"><div class="editor-top"><label>Evidence type<select data-field="kind" aria-label="Evidence ${index+1} type">${Object.entries(names).map(([key,name]) => `<option value="${key}" ${item.kind===key ? "selected" : ""}>${name}</option>`).join("")}</select></label><label>Title<input data-field="title" value="${escapeHTML(item.title)}" maxlength="160" placeholder="A specific project or experience" aria-label="Evidence ${index+1} title"></label></div>
    <label>What does the evidence show?<textarea data-field="content" maxlength="24000" placeholder="Describe the work, your contribution, and the evidence. You can include source code, assessment feedback, or an internship report." aria-label="Evidence ${index+1} content">${escapeHTML(item.content)}</textarea></label>
    <label>Source URL <span>Optional</span><input data-field="source_url" type="url" value="${escapeHTML(item.source_url || "")}" placeholder="https://github.com/you/project" aria-label="Evidence ${index+1} source URL"></label>
    <div class="editor-actions"><span class="editor-hint">Concrete detail is more useful than a long description.</span><button type="button" class="remove-button" data-remove="${item.id}">Remove</button></div></div></details>`;
}

function renderEvidence(openId) {
  const alreadyOpen = $$(".evidence-item[open]").map(element => element.dataset.id);
  $("#evidence-list").innerHTML = state.evidence.map((item,index) => evidenceEditor(item,index,item.id===openId || alreadyOpen.includes(item.id))).join("");
  $("#evidence-empty").hidden = state.evidence.length > 0;
  $("#evidence-count").textContent = String(state.evidence.length);
  $("#add-evidence").disabled = state.evidence.length >= 12;
}

function addEvidence(data = {}) {
  if (state.evidence.length >= 12) return announce("This prototype supports up to 12 evidence items.");
  const item = {id: crypto.randomUUID(), kind:"project", title:"", content:"", source_url:null, ...data};
  state.evidence.push(item);
  renderEvidence(item.id);
  $(`[data-id="${item.id}"] [data-field="title"]`)?.focus();
}

$("#evidence-list").addEventListener("input", event => {
  const field = event.target.dataset.field;
  if (!field) return;
  const row = event.target.closest(".evidence-item");
  const item = state.evidence.find(item => item.id === row.dataset.id);
  item[field] = event.target.value;
  const summary = $(".evidence-text", row);
  $("strong", summary).textContent = item.title || `Untitled ${names[item.kind].toLowerCase()}`;
  $("small", summary).textContent = `${names[item.kind]} · Student supplied`;
  if (field === "kind") $(".evidence-icon", row).innerHTML = icon(icons[item.kind]);
});

$("#evidence-list").addEventListener("click", event => {
  const button = event.target.closest("[data-remove]");
  if (!button) return;
  state.evidence = state.evidence.filter(item => item.id !== button.dataset.remove);
  renderEvidence();
  $("#add-evidence").focus();
});

async function loadExample() {
  const button = $("#example-button");
  button.disabled = true;
  try {
    const example = await api("/v2/example");
    $("#student-name").value = example.student_name;
    $("#target-role").value = example.target_role;
    $("#cgpa").value = example.cgpa;
    $("#coding-score").value = example.coding_score;
    $("#communication-score").value = example.communication_score;
    state.evidence = example.evidence.map(item => ({...item,id:crypto.randomUUID()}));
    state.example = true;
    $("#example-notice").hidden = false;
    renderEvidence();
    announce("Synthetic example loaded. Review the evidence, then run an assessment.");
  } catch(error) { showError(error.message); }
  finally { button.disabled = false; }
}

function payload() {
  const number = selector => $(selector).value === "" ? null : Number($(selector).value);
  return {student_name:$("#student-name").value.trim(), target_role:$("#target-role").value,
    cgpa:number("#cgpa"), coding_score:number("#coding-score"), communication_score:number("#communication-score"),
    evaluator:$("#evaluator").value, dataset_origin:state.example ? "synthetic_example" : "user_supplied",
    evidence:state.evidence.map(({id, ...item}) => ({...item, source_url:item.source_url || null}))};
}

function setBusy(busy) {
  $("#run-button").disabled = busy;
  $("#run-button").innerHTML = busy ? `Assessment in progress` : `Assess my evidence${icon("arrow")}`;
}

$("#assessment-form").addEventListener("submit", async event => {
  event.preventDefault();
  showError("", "#form-error");
  const invalidIndex = state.evidence.findIndex(item => item.title.trim().length < 2 || item.content.trim().length < 20);
  if (invalidIndex >= 0) {
    const item = state.evidence[invalidIndex];
    renderEvidence(item.id);
    showError(`Evidence ${invalidIndex+1} needs a title of at least 2 characters and at least 20 characters of source content.`, "#form-error");
    $(`[data-id="${item.id}"] textarea`)?.focus();
    return;
  }
  if ($("#evaluator").value === "llm" && !state.capabilities?.semantic_evaluator) {
    showError("The semantic evaluator is not configured. Choose offline text scan, or configure ANTHROPIC_API_KEY and ASSESSOR_MODEL on the server.", "#form-error");
    return;
  }
  setBusy(true);
  $("#report-panel").hidden = true;
  try {
    const created = await api("/v2/assessments", {method:"POST", body:JSON.stringify(payload())});
    state.activeId = created.id;
    $("#processing-panel").hidden = false;
    $("#processing-text").textContent = "Your assessment is queued. Evidence is processed on the server.";
    $("#processing-panel").scrollIntoView({behavior:motionBehavior(), block:"nearest"});
    pollAssessment(created.id, Date.now());
  } catch(error) { showError(error.message,"#form-error"); setBusy(false); }
});

const motionBehavior = () => matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth";

async function pollAssessment(id, started) {
  clearTimeout(state.pollTimer);
  try {
    const result = await api(`/v2/assessments/${id}`);
    if (state.activeId !== id) return;
    if (result.status === "completed") {
      state.report = await api(`/v2/assessments/${id}/report`);
      renderReport();
      $("#processing-panel").hidden = true;
      setBusy(false);
      refreshHistory();
      $("#report-panel").scrollIntoView({behavior:motionBehavior(),block:"start"});
    } else if (result.status === "failed") {
      $("#processing-panel").hidden = true;
      setBusy(false);
      showError(result.error || "Assessment failed. Retry or select offline mode.","#form-error");
      refreshHistory();
    } else if (Date.now()-started > 600000) {
      $("#processing-text").textContent = "This is taking longer than expected. You can check status again or return from assessment history.";
      setBusy(false);
    } else {
      $("#processing-text").textContent = result.status === "processing" ? "Evaluating each artifact and validating its source references." : "Your assessment is waiting for an available worker.";
      state.pollTimer = setTimeout(() => pollAssessment(id,started), 1400);
    }
  } catch(error) {
    $("#processing-text").textContent = `${error.message} Use Check status to try again.`;
    setBusy(false);
  }
}

function renderReport() {
  const report = state.report;
  if (!report) return;
  const prediction = report.readiness;
  const trained = prediction.status !== "unavailable";
  $("#report-panel").innerHTML = `${report.dataset_origin === "synthetic_example" ? '<div class="demo-note">Synthetic example profile · Findings demonstrate the workflow, not measured student outcomes.</div>' : ""}
    <div class="report-head"><div><div class="report-title">${icon("check")}<h2>Evidence assessment</h2></div><p>${escapeHTML(report.student_name)} · ${escapeHTML(roles[report.target_role])}</p></div><span class="badge ${report.evaluator === "offline" ? "warning" : ""}">${report.evaluator === "offline" ? "Offline text scan" : "Semantic assessment"}</span></div>
    <div class="report-notice"><strong>${trained ? "Experimental readiness category" : "Trained placement baseline"}</strong>${trained ? `<div class="report-label">${escapeHTML(labels[prediction.label] || prediction.label)}</div>` : ""}${escapeHTML(trained ? prediction.reason : "Complete the original academic and activity fields below to run the trained campus model. Evidence findings are assessed separately by Qwen.")}${report.evaluator === "offline" ? " This report locates related wording. It does not judge quality or verify ability." : " Review source quotes and assessment limitations."}</div>
    <div class="findings-list">${report.artifacts.length ? report.artifacts.map((artifact,index) => `<details class="report-artifact" ${index===0 ? "open" : ""}><summary><span class="evidence-icon">${icon(icons[artifact.kind])}</span><div><strong>${escapeHTML(artifact.title)}</strong><small>${names[artifact.kind]} · Source ${index+1} · Not independently verified</small></div>${icon("chevron")}</summary><p class="artifact-summary">${escapeHTML(artifact.summary)}</p><div class="level-assessment"><span class="badge muted">${escapeHTML(tierNames[artifact.level] || "Level unknown")}</span><p>${escapeHTML(artifact.level_reason || "No semantic level assessment was performed.")}</p>${artifact.level_quote ? `<blockquote>“${escapeHTML(artifact.level_quote)}”</blockquote>` : ""}</div>${artifact.findings.map(f => `<div class="finding"><div class="finding-top"><h3>${escapeHTML(f.dimension)}</h3><span class="badge ${f.category === "unknown" ? "muted" : f.category === "partial" ? "warning" : ""}">${categories[f.category]}</span></div><p>${escapeHTML(f.explanation)}</p>${f.quote ? `<blockquote>“${escapeHTML(f.quote)}”<cite>Source: ${escapeHTML(artifact.evidence_id)} · Student supplied text</cite></blockquote>` : ""}</div>`).join("")}</details>`).join("") : '<div class="empty-state"><h3>No evidence was submitted.</h3><p>Add evidence to receive artifact findings.</p></div>'}</div>
    <div class="next-steps"><h3>Make your next step specific.</h3><ol>${report.next_steps.map(step => `<li>${escapeHTML(step)}</li>`).join("")}</ol></div>
    <div class="report-actions"><button class="text-button" id="review-toggle">Request human review ${icon("chat")}</button><button class="button secondary small" id="download-report">${icon("download")}Export report</button></div>
    <form id="review-form" class="review-form" hidden><label>What should a reviewer check?<textarea id="review-note" minlength="10" maxlength="2000" required placeholder="Explain the finding or missing context you would like reviewed."></textarea></label><button class="button small" type="submit">Save review request</button><span id="review-result" class="review-saved" role="status"></span></form>`;
  $("#report-panel").hidden = false;
  if (!trained) mountPlacementPrediction();
  const reportHeading = $("h2", $("#report-panel"));
  reportHeading.setAttribute("tabindex", "-1");
  reportHeading.focus({preventScroll:true});
  announce("Assessment complete. Your evidence report is ready.");
  $("#review-toggle").onclick = () => { $("#review-form").hidden = !$("#review-form").hidden; if (!$("#review-form").hidden) $("#review-note").focus(); };
  $("#download-report").onclick = () => download(report, `skillsbridge-${report.id}.json`);
  $("#review-form").onsubmit = async event => {
    event.preventDefault();
    const button = $("button",event.target); button.disabled=true;
    try {await api(`/v2/assessments/${report.id}/reviews`,{method:"POST",body:JSON.stringify({note:$("#review-note").value})}); $("#review-result").textContent=" Saved in workspace; no notification sent."; announce("Review request saved.");}
    catch(error){$("#review-result").textContent=error.message;}
    finally{button.disabled=false;}
  };
}

async function refreshHistory() {
  try {const response = await api("/v2/assessments"); state.history=response.items; $("#history-count").textContent=String(response.items.length); renderHistory();}
  catch(error){if (!$("#view-history").hidden) showError(error.message);}
}

function renderHistory() {
  const query = $("#history-search").value.trim().toLowerCase();
  const records = state.history.filter(row => row.student_name.toLowerCase().includes(query));
  $("#history-list").innerHTML = records.length ? records.map(row => `<div class="history-row"><div class="history-name"><span class="evidence-icon">${icon("file")}</span><div><strong>${escapeHTML(row.student_name)}</strong><small>${escapeHTML(roles[row.target_role])} · ${escapeHTML(row.status)}${row.review_requested ? " · Review requested" : ""}</small></div></div><span class="history-date">${humanDate(row.created_at)}</span><div class="history-actions"><button class="button secondary small" data-open-report="${row.id}">${row.status === "completed" ? "View report" : "Check status"}</button><button class="icon-button" data-delete="${row.id}" aria-label="Delete assessment for ${escapeHTML(row.student_name)}">${icon("close")}</button></div></div>`).join("") : `<div class="empty-state"><h2>${query ? "No matching assessments." : "Your progress starts with evidence."}</h2><p>${query ? "Try another name." : "Run your first assessment and find it here."}</p>${query ? "" : '<button class="button" data-view="workspace">Build your profile</button>'}</div>`;
}

$("#history-list").addEventListener("click", async event => {
  const remove = event.target.closest("[data-delete]");
  if (remove) {state.deleteId=remove.dataset.delete; $("#delete-dialog").showModal(); return;}
  const button = event.target.closest("[data-open-report]");
  if (!button) return;
  button.disabled=true;
  try {
    const id=button.dataset.openReport;
    const status=await api(`/v2/assessments/${id}`);
    state.activeId=id;
    if(status.status === "completed") {state.report=await api(`/v2/assessments/${id}/report`); navigate("workspace"); renderReport(); $("#report-panel").scrollIntoView({behavior:motionBehavior(),block:"start"});}
    else if(status.status === "failed") {showError(status.error || "Assessment failed. Submit a new assessment.");}
    else {navigate("workspace"); $("#report-panel").hidden=true; $("#processing-panel").hidden=false; setBusy(true); pollAssessment(id,Date.now());}
  }catch(error){showError(error.message);}finally{button.disabled=false;}
});

function renderModels() {
  const status = state.capabilities?.model;
  const semantic = state.capabilities?.semantic_evaluator;
  const available = status?.available;
  $("#model-content").innerHTML = `<div class="model-layout"><section class="surface model-section"><span class="badge ${available ? "warning" : "muted"}">${available ? "Experimental model installed" : "Awaiting expert labels"}</span><h2>${available ? escapeHTML(status.selected_model) : "An honest starting point."}</h2><p>${available ? "A trained model is installed. Its holdout metrics measure the supplied expert labels, not real placement outcomes." : "There is no labelled evidence dataset in this project yet. The prototype can assess evidence, but cannot report a validated readiness prediction."}</p><div class="status-table"><div><span>Semantic evaluator</span><strong>${semantic ? "Configured" : "Not configured"}</strong></div><div><span>Offline evaluator</span><strong>Text scan available</strong></div><div><span>Training data</span><strong>${available ? `${status.rows} records` : "Not supplied"}</strong></div><div><span>Model comparison</span><strong>${available ? "Completed" : "Pipeline ready"}</strong></div><div><span>Placement probability</span><strong>Not validated</strong></div></div>${available ? `<table class="metric-table"><thead><tr><th>Candidate</th><th>CV macro F1</th></tr></thead><tbody>${status.candidates.map(c=>`<tr><td>${escapeHTML(c.model)}</td><td>${c.cv_macro_f1.toFixed(3)}</td></tr>`).join("")}</tbody></table><p class="field-hint">Untouched holdout macro F1: ${status.holdout.macro_f1.toFixed(3)}. These are experimental, dataset-specific results.</p>` : ""}</section><section class="surface model-instructions"><h2>The path to a measured model</h2><ol><li><strong>Collect independent assessments</strong><p>Faculty label student readiness using a defined role rubric and practical evidence.</p></li><li><strong>Freeze the evaluator</strong><p>Use one model, prompt, and rubric version. Keep test profiles out of examples.</p></li><li><strong>Compare three model families</strong><p>Logistic regression, random forest, and extra trees. Select using grouped cross-validation.</p></li><li><strong>Evaluate the untouched holdout</strong><p>Keep students and duplicate artifacts in the same leakage group. Inspect errors by class.</p></li><li><strong>Install a versioned model</strong><p>Compatible feature and evaluator signatures are required before predictions are enabled.</p></li></ol></section></div><div class="model-callout">${icon("lab")}<div><h3>Accuracy is earned with independent data.</h3><p>Synthetic fixtures test software behaviour. They never establish student readiness accuracy. The training command and dataset format are documented in prototype/README.md.</p></div></div>`;
}

function download(value, filename) {
  const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type:"application/json"}));
  const link=document.createElement("a"); link.href=url; link.download=filename; link.click();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
}

$("#github-fetch").onclick=async()=>{
  const button=$("#github-fetch"); button.disabled=true; button.textContent="Importing";
  try{const result=await api("/v2/import/github",{method:"POST",body:JSON.stringify({repository:$("#github-repo").value.trim()})}); addEvidence(result.evidence); $("#github-import").hidden=true; announce(result.scope);}
  catch(error){showError(error.message,"#form-error");}finally{button.disabled=false;button.textContent="Import README";}
};

$("#file-import").onchange=async event=>{
  const file=event.target.files[0]; if(!file)return;
  if(file.size>96000){showError("Choose a text file smaller than 96 KB.","#form-error");event.target.value="";return;}
  try{const text=await file.text();if(text.includes("\u0000"))throw new Error("This appears to be a binary file. Use plain text or source code.");if(text.length>24000)throw new Error("The file exceeds 24,000 characters. Select a representative excerpt.");addEvidence({title:file.name,content:text});announce("Text file added as student supplied evidence.");}
  catch(error){showError(error.message,"#form-error");}finally{event.target.value="";}
};

document.addEventListener("click",event=>{const button=event.target.closest("[data-view]");if(button)navigate(button.dataset.view);});
$("#file-trigger").onclick=()=>$("#file-import").click();
$("#add-evidence").onclick=()=>addEvidence();
$("#first-evidence").onclick=()=>addEvidence();
$("#example-button").onclick=loadExample;
$("#github-toggle").onclick=()=>{$("#github-import").hidden=!$("#github-import").hidden;if(!$("#github-import").hidden)$("#github-repo").focus();};
$("#check-status").onclick=()=>{if(state.activeId)pollAssessment(state.activeId,Date.now());};
$("#history-search").oninput=renderHistory;
$("#refresh-history").onclick=refreshHistory;
$("#settings-button").onclick=$("#api-settings").onclick=()=>$("#settings-dialog").showModal();
$("#close-settings").onclick=()=>$("#settings-dialog").close();
$("#settings-form").onsubmit=event=>{event.preventDefault();state.apiKey=$("#api-key").value;$("#api-key").value="";$("#settings-dialog").close();connect();};
$("#cancel-delete").onclick=()=>$("#delete-dialog").close();
$("#confirm-delete").onclick=async()=>{
  const button=$("#confirm-delete");button.disabled=true;
  try{await api(`/v2/assessments/${state.deleteId}`,{method:"DELETE"});if(state.report?.id===state.deleteId){state.report=null;$("#report-panel").hidden=true;}if(state.activeId===state.deleteId){clearTimeout(state.pollTimer);state.activeId=null;$("#processing-panel").hidden=true;setBusy(false);}$("#delete-dialog").close();await refreshHistory();announce("Assessment deleted.");}
  catch(error){showError(error.message);}finally{button.disabled=false;}
};

$("#integration-code").textContent=`import httpx\nimport time\n\nbase = "${location.origin}"\nheaders = {"X-API-Key": "YOUR_WORKSPACE_KEY"}\n\nwith httpx.Client(headers=headers) as client:\n    response = client.post(\n        f"{base}/v2/assessments",\n        json={\n            "student_name": "Aarav Deshmukh",\n            "target_role": "junior_backend",\n            "evaluator": "auto",\n            "evidence": [{\n                "kind": "project",\n                "title": "Campus equipment exchange",\n                "content": "I built a reservation API. "\n                           "Tests cover booking conflicts."\n            }]\n        },\n    )\n    response.raise_for_status()\n    key = response.json()["id"]\n\n    for _ in range(120):\n        status = client.get(\n            f"{base}/v2/assessments/{key}"\n        )\n        status.raise_for_status()\n        job = status.json()\n        if job["status"] == "completed":\n            break\n        if job["status"] == "failed":\n            raise RuntimeError(job["error"])\n        time.sleep(2)\n    else:\n        raise TimeoutError("Assessment still running")\n\n    report = client.get(\n        f"{base}/v2/assessments/{key}/report"\n    )\n    report.raise_for_status()\n    print(report.json())`;
$("#copy-code").onclick=async()=>{try{await navigator.clipboard.writeText($("#integration-code").textContent);announce("Integration example copied.");}catch{announce("Clipboard unavailable. Select and copy the example.");}};
window.addEventListener("hashchange",()=>navigate(location.hash.slice(1),false));
renderEvidence();
navigate(location.hash.slice(1)||"workspace",false);
connect();

async function mountPlacementPrediction() {
  const host = document.createElement("section");
  host.className = "baseline-panel";
  document.querySelector(".report-notice").after(host);
  host.textContent = "Loading trained model fields…";
  try {
    const info = await api("/v2/baselines/campus");
    const names = {cgpa:"CGPA (0–10)", internship_count:"Completed internships", project_count:"Completed projects", workshop_certification_count:"Workshops and certifications", aptitude_test_score:"Aptitude test (0–100)", soft_skills_rating_original:"Soft skills rating (0–5)", ssc_marks:"SSC marks (%)", hsc_marks:"HSC marks (%)", extracurricular_activities:"Extracurricular activities", placement_training:"Completed placement training"};
    host.innerHTML = `<h3>Campus placement prediction</h3><p class="field-hint">Random Forest · ${ (info.holdout.accuracy*100).toFixed(2)}% test accuracy on published data. This experimental result predicts its Placed/NotPlaced label; it is not a verified personal placement probability.</p><form id="baseline-form"><div class="baseline-fields">${info.numeric_features.map(name => `<label>${names[name]}<input name="${name}" type="number" min="0" ${name==="cgpa" ? 'max="10"' : name==="soft_skills_rating_original" ? 'max="5"' : name.endsWith("score") || name.endsWith("marks") ? 'max="100"' : ''} step="any" required></label>`).join("")}${info.categorical_features.map(name => `<label>${names[name]}<select name="${name}" required><option value="">Choose an answer</option><option>Yes</option><option>No</option></select></label>`).join("")}</div><button class="button" type="submit">Predict placement label</button><p id="baseline-result" role="status" class="baseline-result"></p></form>`;
    const controls = document.createElement("div");
    controls.className = "standardization-controls";
    controls.innerHTML = `<button type="button" class="button secondary" id="extract-measurements">Extract inputs from my evidence</button><p class="field-hint">Qwen extracts stated measurements and preserves their source quotes. Missing values stay blank. Your saved model performs numerical normalization.</p><div id="extraction-findings" aria-live="polite"></div>`;
    host.querySelector("form").before(controls);
    const renderExtracted = data => {
      const rows = Object.entries(data.fields);
      for (const [name, entry] of rows) {
        const input = host.querySelector(`[name="${name}"]`);
        if (input && entry.value !== null) input.value = entry.value;
      }
      host.querySelector("#extraction-findings").innerHTML = `<p>${escapeHTML(data.conflicts.join(" ") || "Review extracted values before prediction. No missing measurement has been estimated.")}</p><details><summary>View extracted facts and source quotes</summary>${rows.map(([name,entry]) => `<p><strong>${escapeHTML(names[name])}: ${escapeHTML(entry.value ?? "Unknown")}</strong><br>${escapeHTML(entry.quote || entry.source)}</p>`).join("")}</details>`;
      state.report.standardized_inputs = data;
    };
    host.querySelector("#extract-measurements").onclick = async event => {
      const button = event.currentTarget;
      button.disabled = true; button.textContent = "Extracting source measurements…";
      try {renderExtracted(await api(`/v2/assessments/${state.report.id}/standardize`,{method:"POST"}));}
      catch(error) {host.querySelector("#extraction-findings").textContent = error.message;}
      finally {button.disabled = false; button.textContent = "Extract inputs from my evidence";}
    };
    if (state.report.standardized_inputs) renderExtracted(state.report.standardized_inputs);
    const semantic = document.createElement("details");
    semantic.className = "feature-review";
    semantic.innerHTML = `<summary>Standardized semantic features</summary><p class="field-hint">These role-specific evidence categories are available for the new classifier. They are never substituted for the campus model's count or test-score fields.</p>${Object.entries(state.report.features).map(([name,value])=>`<p><strong>${escapeHTML(name)}</strong>: ${escapeHTML(value ?? "Unknown")}</p>`).join("")}`;
    controls.append(semantic);
    if (state.report.features.cgpa != null) host.querySelector('[name="cgpa"]').value = state.report.features.cgpa;
    host.querySelector("form").onsubmit = async event => {
      event.preventDefault();
      const button=host.querySelector("button"), result=host.querySelector("#baseline-result");
      button.disabled=true;result.textContent="Running the trained model…";
      try {
        const values=Object.fromEntries(new FormData(event.target));
        info.numeric_features.forEach(name=>values[name]=Number(values[name]));
        const prediction=await api("/v2/baselines/campus/predict",{method:"POST",body:JSON.stringify({features:values})});
        state.report.baseline_prediction={inputs:values,...prediction};
        result.textContent=`${prediction.label === "Placed" ? "Placed" : "Not placed"} — model score for Placed: ${(prediction.probabilities.Placed*100).toFixed(1)}%. Experimental campus baseline; source outcomes are not independently verified.`;
      } catch(error) {result.textContent=error.message;}
      finally {button.disabled=false;}
    };
  } catch(error) {host.textContent=`Placement model could not load: ${error.message}`;}
}
