import './style.css';
import type { AuditRequest, Entry, Report, Revision } from './types';
import type { ModelViewer } from './viewer';

const app = document.querySelector<HTMLDivElement>('#app')!;
const esc = (v: unknown) => String(v ?? '—').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]!);
const label = (v: string) => v.replaceAll('_', ' ');
const num = (v?: number | null) => v == null ? 'Unavailable' : v.toFixed(3);
let request: AuditRequest, demo: AuditRequest;
let report: Report | null = null, selection: Entry | null = null, viewer: ModelViewer | null = null;
let viewerQueue = Promise.resolve();
let viewRevision: 'before' | 'after' = 'after';
let showAll = false, busy = false;

app.innerHTML = `
<aside class="sidebar"><a class="brand" href="/"><span class="brand-mark">◈</span><span>OpenBIM<small>ENGINEERING SYSTEMS</small></span></a>
<div class="workspace-label">PILOT WORKSPACE <span>01</span></div>
<nav aria-label="Workspace"><button class="nav-item active" id="audit-tab">▧ <span>Change audit</span></button><button class="nav-item" id="evidence-tab">⌕ <span>Evidence register</span></button></nav>
<div class="sidebar-note"><span class="small-cap">THE WORKFLOW</span><ol><li>Compare model revisions</li><li>Trace BOM lineage</li><li>Reconcile ordered items</li></ol></div><div class="sidebar-footer">● Local pilot<small>Synthetic procurement · v1.0</small></div></aside>
<main><header class="topbar"><span>Engineering / <strong>Revision control</strong></span><span class="local-chip">LOCAL WORKSPACE</span></header>
<div class="page-content"><div class="page-heading"><div><div class="eyebrow">DESIGN CHANGES. DOWNSTREAM CONSEQUENCES.</div><h1>Engineering change audit</h1><p>See what changed, what it affects, and the evidence behind it.</p></div><a id="export" class="button secondary disabled" aria-disabled="true">↓ Export audit</a></div>
<div id="message" class="message" role="alert" hidden></div>
<section class="revision-bar" aria-label="Revision inputs">
<div class="revision-input"><span class="revision-letter">A</span><label>Baseline revision<select id="baseline" aria-label="Baseline revision"></select></label><label class="upload" title="Import baseline IFC">↑<input id="upload-baseline" type="file" accept=".ifc" aria-label="Import baseline IFC"></label></div><span class="revision-arrow">→</span>
<div class="revision-input"><span class="revision-letter revised">B</span><label>Revised model<select id="revised" aria-label="Revised model"></select></label><label class="upload" title="Import revised IFC">↑<input id="upload-revised" type="file" accept=".ifc" aria-label="Import revised IFC"></label></div><button id="run-audit" class="button primary">Run comparison ↗</button></section>
<div class="input-footnote"><span id="procurement-label">Synthetic procurement fixture · 1 cut member per BOM line</span><div><label class="text-link">Import procurement JSON<input id="upload-procurement" type="file" accept=".json" aria-label="Import procurement JSON"></label><button class="text-link" id="control">Run unchanged control</button><button class="text-link" id="reset">Reset demo</button></div></div>
<section class="metrics" id="metrics" aria-label="Audit summary"><div class="metric">Loading audit…</div></section>
<section id="audit-panel"><div class="analysis-grid">
<section class="panel model-panel"><div class="panel-heading"><div><h2>Model context</h2><span class="muted">Equipment support structure</span></div><div class="segmented" aria-label="Displayed revision"><button id="view-before" aria-pressed="false">A · Baseline</button><button id="view-after" class="selected" aria-pressed="true">B · Revised</button></div></div><div id="model-container"><div class="model-watermark">IFC4 / MODEL SPACE</div></div><div class="viewer-status"><span id="viewer-status" role="status">Preparing IFC viewer…</span><button id="fit" class="text-link">Fit model ↗</button></div><div class="legend"><span><i class="changed"></i>Changed</span><span><i class="selected"></i>Selected</span><span><i class="neutral"></i>Unchanged</span><span class="orbit-hint">Drag to orbit · Scroll to zoom</span></div></section>
<section class="panel detail-panel"><div class="panel-heading"><h2>Change details</h2><span class="small-cap">SOURCE EVIDENCE</span></div><div id="detail"></div></section></div>
<section class="panel changes-panel"><div class="panel-heading"><div><h2>Component register <span id="register-count" class="count-pill"></span></h2><span class="muted">Select a row to trace the model and its downstream records.</span></div><label class="check"><input id="show-all" type="checkbox"> Include unchanged</label></div><div class="table-scroll"><table><thead><tr><th>Component</th><th>Revision status</th><th>Changed fields</th><th>Match confidence</th><th>Review state</th><th></th></tr></thead><tbody id="entries"></tbody></table></div></section>
<section class="panel impacts-panel"><div class="panel-heading"><div><h2>Procurement reconciliation</h2><span class="muted">Reasons are grouped by affected purchase-order line.</span></div><span class="synthetic-chip">SYNTHETIC RECORDS</span></div><div id="impacts"></div></section></section>
<section id="evidence-panel" class="panel" hidden><div class="panel-heading"><h2>Evidence register</h2><span class="small-cap">IMMUTABLE SOURCE RECORDS</span></div><div id="evidence"></div></section>
<footer><span>OpenBIM Engineering Change Auditor</span><span>Illustrative rules · Supported fields only · No engineering approval</span></footer></div></main>`;

const $ = <T extends HTMLElement = HTMLElement>(id: string) => document.getElementById(id) as T;
function message(text = '') { $('message').textContent = text; $('message').hidden = !text; }
async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, options);
  if (!response.ok) {
    const data = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail));
  }
  return response.json();
}
function setBusy(value: boolean) {
  busy = value;
  for (const id of ['run-audit', 'control', 'reset', 'baseline', 'revised', 'upload-baseline', 'upload-revised', 'upload-procurement']) ($(id) as HTMLButtonElement).disabled = value;
  $('run-audit').textContent = value ? 'Comparing…' : 'Run comparison ↗';
}
async function refreshRevisions() {
  const revisions = await api<Revision[]>('/revisions');
  for (const [id, selected] of [['baseline', request.baseline_id], ['revised', request.revised_id]]) {
    $<HTMLSelectElement>(id!).innerHTML = revisions.map(r => `<option value="${r.id}" ${r.id === selected ? 'selected' : ''}>${esc(r.filename)} · ${r.id.slice(0, 7)}</option>`).join('');
  }
}
async function runAudit() {
  if (busy) return;
  message(); setBusy(true);
  try {
    request.baseline_id = $<HTMLSelectElement>('baseline').value;
    request.revised_id = $<HTMLSelectElement>('revised').value;
    report = await api<Report>('/audits', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(request) });
    selection = report.entries.find(e => e.kind !== 'unchanged' || e.review_state !== 'no_discrepancy') ?? report.entries[0] ?? null;
    renderReport(); queueViewer();
  } catch (error) { message(`Comparison failed: ${String(error)}`); }
  finally { setBusy(false); }
}
function renderReport() {
  if (!report) return;
  if (report.diagnostics.length) message(`Reconciliation incomplete: ${report.diagnostics.join('; ')}`);
  const s = report.summary;
  $('metrics').innerHTML = [
    ['Modified components', s.modified, `${s.unchanged} unchanged · ${s.added} added · ${s.removed} removed`, 'amber'],
    ['Affected BOM lines', s.affected_bom_lines, 'Linked to manufacturing records', ''],
    ['Flagged PO lines', s.flagged_po_lines, `${s.impact_reasons} recorded review reasons`, 'amber'],
    ['Uncertain components', s.uncertain_components, s.uncertain_components ? 'Resolve source data or identity' : 'All component matches evaluated', s.uncertain_components ? 'amber' : 'teal'],
  ].map(([title, count, detail, tone]) => `<article class="metric ${tone}"><span>${title}</span><strong>${count}</strong><small>${detail}</small></article>`).join('');
  const exportLink = $<HTMLAnchorElement>('export');
  exportLink.href = `/api/audits/${report.id}/export`; exportLink.classList.remove('disabled'); exportLink.setAttribute('aria-disabled', 'false');
  renderEntries(); renderDetail(); renderImpacts(); renderEvidence();
}
function renderEntries() {
  if (!report) return;
  const entries = report.entries.filter(e => showAll || e.kind !== 'unchanged' || e.review_state !== 'no_discrepancy');
  $('register-count').textContent = String(entries.length);
  $('entries').innerHTML = entries.map(e => {
    const c = e.after || e.before!;
    return `<tr class="${e.id === selection?.id ? 'selected-row' : ''}"><td><button class="member-button" data-select="${e.id}">${esc(c.tag || c.guid || 'Unidentified member')}</button><small>${esc(c.class)}</small></td><td><span class="badge ${e.kind}">${esc(label(e.kind))}</span></td><td>${esc(e.changes.map(c => label(c.field)).join(', ') || '—')}</td><td>${e.confidence === 'exact' ? '● Exact identity' : '◐ Review identity'}</td><td>${esc(label(e.review_state))}</td><td>↗</td></tr>`;
  }).join('') || '<tr><td colspan="6" class="empty">No changed or uncertain components. The unchanged-model control is clean.</td></tr>';
  for (const button of document.querySelectorAll<HTMLButtonElement>('[data-select]')) button.onclick = () => selectEntry(button.dataset.select!);
}
function selectEntry(id: string) {
  selection = report?.entries.find(e => e.id === id) ?? null;
  if (selection?.kind === 'removed') viewRevision = 'before';
  if (selection?.kind === 'added') viewRevision = 'after';
  renderEntries(); renderDetail(); queueViewer();
}
function renderDetail() {
  if (!selection || !report) { $('detail').innerHTML = '<p class="empty">No components found in these revisions.</p>'; return; }
  const e = selection, a = e.before, b = e.after, c = b || a!;
  const field = (title: string, before: string, after: string, key: string) => `<tr><th>${title}</th><td>${before}</td><td class="${e.changes.some(c => c.field === key) ? 'value-changed' : ''}">${after}</td></tr>`;
  $('detail').innerHTML = `<div class="detail-title"><div class="small-cap">${esc(c.class)} / ${esc(label(e.kind))}</div><h3>${esc(c.tag || 'Unidentified member')}</h3><span class="badge ${e.review_state === 'no_discrepancy' ? 'unchanged' : 'modified'}">${esc(label(e.review_state))}</span></div>
  <table class="comparison-table"><thead><tr><th>Property</th><th>A · Baseline</th><th>B · Revised</th></tr></thead><tbody>
  ${field('Length (m)', num(a?.geometry?.length_m), num(b?.geometry?.length_m), 'length_m')}
  ${field('Volume (m³)', num(a?.geometry?.volume_m3), num(b?.geometry?.volume_m3), 'volume_m3')}
  ${field('Specification', esc(a?.specification), esc(b?.specification), 'specification')}
  ${field('Piece count', a ? '1' : '—', b ? '1' : '—', '')}</tbody></table>
  ${e.changes.some(c => c.field === 'length_m') ? `<div class="delta-note"><span>QUANTITY DELTA</span><strong>${num(b!.geometry!.length_m - a!.geometry!.length_m)} m</strong><small>${num(b!.geometry!.volume_m3 - a!.geometry!.volume_m3)} m³ modeled volume</small></div>` : ''}
  <div class="lineage"><span class="small-cap">RECORD LINEAGE</span><div>${esc(c.tag || 'IFC member')} <span>→</span> ${esc(e.bom_line_ids.join(', ') || 'No linked BOM')}</div><small>${esc([...new Set(report.impacts.filter(i => i.change_id === e.id && i.po_line_id).map(i => i.po_line_id))].join(', ') || 'No flagged purchase-order line')}</small></div>
  ${e.issues.length ? `<div class="diagnostics"><strong>Review source data</strong><ul>${e.issues.map(i => `<li>${esc(i)}</li>`).join('')}</ul></div>` : ''}
  <details class="source-details"><summary>Source identifiers and measurement evidence</summary><dl><dt>Match method</dt><dd>${esc(e.match_method)}</dd><dt>GlobalId</dt><dd>${esc(c.guid)}</dd><dt>IFC source</dt><dd>#${c.source.step_id} · ${esc(c.source.file)}</dd><dt>Geometry</dt><dd>${esc(c.geometry?.source_path || 'Unsupported / unavailable')}</dd><dt>Material source</dt><dd>${esc(c.material_source.map(m => `#${m.step_id}: ${m.name}`).join('; '))}</dd><dt>Revision SHA-256</dt><dd>${esc(c.source.revision_id)}</dd></dl></details>`;
}
function renderImpacts() {
  if (!report) return;
  if (!report.impacts.length && report.diagnostics.length) {
    $('impacts').innerHTML = `<div class="diagnostics"><strong>Reconciliation incomplete</strong><ul>${report.diagnostics.map(d => `<li>${esc(d)}</li>`).join('')}</ul></div>`;
    return;
  }
  const groups = new Map<string, typeof report.impacts>();
  for (const i of report.impacts) { const key = i.po_line_id || i.bom_line_id || i.change_id; groups.set(key, [...(groups.get(key) || []), i]); }
  $('impacts').innerHTML = [...groups].map(([key, impacts]) => `<article class="impact-card"><div class="impact-label"><span class="impact-icon">!</span><div><h3>${esc(key)}</h3><small>${esc(impacts[0]!.tag)} · ${esc(impacts[0]!.bom_line_id || 'Source review')}</small></div><span class="badge modified">${impacts.some(i => i.state === 'undetermined') ? 'Undetermined' : 'Review required'}</span></div><ul>${impacts.map(i => `<li><strong>${esc(i.message)}</strong><small>${esc(i.rule)} · ${esc(report!.engine_version)}${i.ordered ? ` · Ordered: ${num(i.ordered.length_m)} m / ${esc(i.ordered.specification)}` : ''}</small></li>`).join('')}</ul><button class="text-link" data-impact-select="${impacts[0]!.change_id}">Inspect component evidence ↗</button></article>`).join('') || '<div class="clean-result"><span>✓</span><div><strong>No procurement discrepancies detected</strong><p>Evaluated records agree under the pilot rules. This is not a manufacturing release.</p></div></div>';
  for (const button of document.querySelectorAll<HTMLButtonElement>('[data-impact-select]')) button.onclick = () => { selectEntry(button.dataset.impactSelect!); $('detail').scrollIntoView({ behavior: 'smooth', block: 'center' }); };
}
function renderEvidence() {
  if (!report) return;
  $('evidence').innerHTML = `<p>Every audit preserves its original IFC sources, canonical snapshots, baseline and revised BOMs, and rule evidence.</p><div class="evidence-grid">${[report.baseline, report.revised].map((r, i) => `<article><span class="small-cap">${i ? 'B · REVISED' : 'A · BASELINE'}</span><h3>${esc(r.filename)}</h3><code>${r.id}</code><p>${r.schema} · Source length scale: ${r.length_unit_to_m} m</p><a href="/api/revisions/${r.id}/source" class="text-link">Download original IFC ↓</a></article>`).join('')}</div><dl><dt>Audit hash</dt><dd>${report.id}</dd><dt>Procurement hash</dt><dd>${report.procurement_sha256}</dd><dt>Engine / rules</dt><dd>${report.engine_version}</dd><dt>Tolerances</dt><dd>${report.tolerances.length_m} m length · ${report.tolerances.volume_m3} m³ volume</dd><dt>Scope</dt><dd>${esc(report.scope)}</dd></dl><a class="button secondary" href="/api/audits/${report.id}/export">Download complete evidence JSON ↓</a>`;
}
function queueViewer() {
  viewerQueue = viewerQueue.then(async () => {
    if (!report) return;
    $('viewer-status').textContent = 'Loading source IFC…';
    try {
      if (!viewer) {
        const { ModelViewer } = await import('./viewer');
        const instance = new ModelViewer($('model-container'), guid => {
          const e = report?.entries.find(e => (viewRevision === 'before' ? e.before : e.after)?.guid === guid);
          if (e) { showAll = true; $<HTMLInputElement>('show-all').checked = true; selectEntry(e.id); }
        });
        await instance.init(); viewer = instance;
      }
      const side = viewRevision, revision = side === 'before' ? report.baseline : report.revised;
      const changed = report.entries.filter(e => e.kind !== 'unchanged').map(e => (side === 'before' ? e.before : e.after)?.guid).filter((id): id is string => !!id);
      await viewer.load(revision.id, changed);
      const component = selection ? (side === 'before' ? selection.before : selection.after) : null;
      const found = await viewer.select(component?.guid || null);
      $('viewer-status').textContent = `${side === 'before' ? 'Baseline' : 'Revised'} IFC loaded${component?.guid && !found ? ' · Selection unavailable in viewer' : ' · Source geometry'}`;
      $('model-container').dataset.ready = 'true';
    } catch (error) { $('viewer-status').textContent = `3D unavailable: ${String(error)}. Audit evidence remains available.`; }
    for (const side of ['before', 'after'] as const) { $(`view-${side}`).classList.toggle('selected', viewRevision === side); $(`view-${side}`).setAttribute('aria-pressed', String(viewRevision === side)); }
  }).catch(error => { $('viewer-status').textContent = String(error); });
}

$('run-audit').onclick = () => void runAudit();
$('show-all').onchange = () => { showAll = $<HTMLInputElement>('show-all').checked; renderEntries(); };
$('fit').onclick = () => { void viewer?.fit().catch(error => { $('viewer-status').textContent = String(error); }); };
for (const side of ['before', 'after'] as const) $(`view-${side}`).onclick = () => { viewRevision = side; queueViewer(); };
$('control').onclick = () => { $<HTMLSelectElement>('revised').value = $<HTMLSelectElement>('baseline').value; void runAudit(); };
$('reset').onclick = () => { void (async () => { request = { ...demo }; await refreshRevisions(); $('procurement-label').textContent = 'Synthetic procurement fixture · 1 cut member per BOM line'; await runAudit(); })().catch(error => message(String(error))); };
for (const side of ['baseline', 'revised'] as const) $(`upload-${side}`).onchange = () => { void (async () => {
  const input = $<HTMLInputElement>(`upload-${side}`), file = input.files?.[0]; if (!file) return;
  message(); setBusy(true);
  try { const form = new FormData(); form.set('file', file); const r = await api<Revision>('/revisions', { method: 'POST', body: form }); request[`${side}_id`] = r.id; await refreshRevisions(); message(`${file.name} imported. Run comparison to evaluate it against the selected procurement records.`); }
  finally { setBusy(false); input.value = ''; }
})().catch(error => message(`Import failed: ${String(error)}`)); };
$('upload-procurement').onchange = () => { void (async () => {
  const input = $<HTMLInputElement>('upload-procurement'), file = input.files?.[0]; if (!file) return;
  setBusy(true);
  try { if (file.size > 1024 * 1024) throw new Error('Maximum procurement JSON size is 1 MiB'); const result = await api<{ id: string }>('/procurement', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(JSON.parse(await file.text())) }); request.procurement_id = result.id; $('procurement-label').textContent = `Synthetic procurement: ${file.name}`; message('Procurement imported. Run comparison to evaluate the updated inputs.'); }
  finally { setBusy(false); input.value = ''; }
})().catch(error => message(`Procurement import failed: ${String(error)}`)); };
for (const tab of ['audit', 'evidence']) $(`${tab}-tab`).onclick = () => { $('audit-panel').hidden = tab !== 'audit'; $('evidence-panel').hidden = tab !== 'evidence'; $('audit-tab').classList.toggle('active', tab === 'audit'); $('evidence-tab').classList.toggle('active', tab === 'evidence'); };
for (const id of ['baseline', 'revised']) $(id).onchange = () => message('Inputs changed. The report below still shows the previous comparison; run comparison to update it.');
void (async () => { demo = await api<AuditRequest>('/demo'); request = { ...demo }; await refreshRevisions(); await runAudit(); })().catch(error => message(`Unable to start: ${String(error)}. Start the Python API on port 8000.`));
