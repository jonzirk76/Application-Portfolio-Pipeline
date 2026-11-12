import './style.css';
import './enclosure.css';
import type { ModelViewer } from './viewer';

type Component = { guid: string; tag: string; assembly: string; role: string; material: string;
  dimensions: Record<string, number> | null; issues: string[]; geometry_source: string; source: { step_id: number; revision_id: string } };
type Entry = { guid: string; kind: string; before: Component | null; after: Component | null;
  changes: { field: string; before: unknown; after: unknown; delta: number | null }[]; issues: string[] };
type Report = { id: string; baseline_id: string; revised_id: string; summary: Record<string, number>; entries: Entry[];
  drawing_findings: { document_id: string; title: string; guids: string[]; reason: string }[];
  alignment_findings: { assembly: string; guids: string[]; reasons: string[]; state: string }[] };
type Package = { id: string; source_revision: string; issue_revision: string; status: string;
  schedule: { mark: string; assembly: string; role: string; dimensions_in: Record<string, number>; volume_m3: number }[] };
type Demo = { baseline_id: string; revised_id: string; misaligned_id: string; package_id: string };
type Revision = { id: string; filename: string };
const $ = <T extends HTMLElement = HTMLElement>(id: string) => document.getElementById(id) as T;
const esc = (value: unknown) => String(value ?? '—').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]!);
const number = (value: number) => Number(value.toFixed(4)).toString();
const fieldName = (field: string) => field.replace(/_m3$/, ' (m³)').replace(/_m$/, ' (in)').replaceAll('_', ' ');
let demo: Demo, report: Report, issued: Package, revisions: Revision[] = [], packages: Package[] = [];
let selection: Entry | undefined, viewer: ModelViewer | null = null, viewerQueue = Promise.resolve();
let side: 'before' | 'after' = 'after', busy = false;
document.body.classList.add('enclosure-page');
$('app').innerHTML = `
<aside class="sidebar"><a class="brand" href="/"><span class="brand-mark">◈</span><span>OpenBIM<small>ENGINEERING SYSTEMS</small></span></a>
<div class="workspace-label">DETAILING WORKSPACE <span>02</span></div><nav aria-label="Workspace"><a class="nav-item" href="/">▧ Procurement audit</a><a class="nav-item active" href="/enclosure.html">▧ Enclosure details</a></nav>
<div class="sidebar-note"><span class="small-cap">THE WORKFLOW</span><ol><li>Compare support assemblies</li><li>Review affected drawings</li><li>Generate a current package</li></ol></div><div class="sidebar-footer">● Local pilot<small>Illustrative enclosure assembly</small></div></aside>
<main><header class="topbar"><span>Structural / <strong>Drawing coordination</strong></span><span class="local-chip">LOCAL WORKSPACE</span></header>
<div class="page-content"><div class="page-heading"><div><div class="eyebrow">MODEL REVISIONS. COORDINATED DETAILS.</div><h1>Enclosure foundation details</h1><p>Trace footing and post changes into plans, details, and schedules.</p></div><a id="export" class="button secondary disabled">↓ Export audit</a></div>
<div id="message" class="message" role="alert" hidden></div>
<section class="panel enclosure-controls" aria-label="Model revisions"><label>Baseline IFC<select id="baseline"></select></label><label>Revised IFC<select id="revised"></select></label><label class="upload-label button secondary">Import revised IFC<input id="upload" type="file" accept=".ifc" aria-label="Import revised IFC"></label><button id="compare" class="button primary">Compare revisions ↗</button></section>
<div class="enclosure-actions"><button id="diameter" class="text-link">Footing diameter example</button><button id="alignment" class="text-link">Post alignment example</button><button id="control" class="text-link">Unchanged control</button></div>
<p class="enclosure-help">Two supports with 4 × 4-inch HSS posts and 10 × 10-inch base plates. Other dimensions are illustrative. The diameter example changes F-01 from 24 to 30 inches; AS-02 remains unchanged.</p>
<section class="metrics" id="metrics" aria-label="Detail audit summary"><div class="metric">Loading enclosure audit…</div></section>
<div class="analysis-grid"><section class="panel model-panel"><div class="panel-heading"><div><h2>Support assembly</h2><span class="muted">Cylindrical concrete · base plate · hollow post</span></div><div class="segmented"><button id="view-before">A · Baseline</button><button id="view-after" class="selected">B · Revised</button></div></div><div id="model-container"><div class="model-watermark">IFC4 / MODEL SPACE</div></div><div class="viewer-status"><span id="viewer-status" role="status">Preparing viewer…</span><button id="fit" class="text-link">Fit model ↗</button></div><div class="legend"><span><i class="changed"></i>Changed</span><span><i class="selected"></i>Selected</span><span>Drag to orbit · Scroll to zoom</span></div></section>
<section class="panel"><div class="panel-heading"><h2>Component evidence</h2><span class="small-cap">MEASURED FROM IFC</span></div><div id="detail" class="enclosure-detail"></div></section></div>
<section class="panel enclosure-section"><div class="panel-heading"><h2>Component register</h2><span class="small-cap">SUPPORT ASSEMBLIES</span></div><div class="table-scroll"><table><thead><tr><th>Mark</th><th>Assembly</th><th>Revision state</th><th>Changed fields</th></tr></thead><tbody id="components"></tbody></table></div></section>
<section class="panel enclosure-section"><div class="panel-heading"><h2>Drawing and alignment review</h2><span id="finding-status" class="badge modified"></span></div><div id="findings" class="enclosure-findings"></div></section>
<section class="panel enclosure-section"><div class="panel-heading"><h2>Drawing issue register</h2><a id="download-package" class="button secondary">↓ Download package</a></div>
<div class="enclosure-controls"><label>Issued package<select id="package"></select></label><label class="issue-label">New revision<input id="issue" value="B" maxlength="20" pattern="[A-Za-z0-9._-]+"></label><button id="generate" class="button primary">Generate current package ↗</button></div>
<div class="drawing-tools"><label for="sheet">Drawing</label><select id="sheet"><option value="S-101">S-101 · Plan and plate details</option><option value="S-501">S-501 · Sections and elevations</option></select><a id="svg-link" class="text-link" target="_blank" rel="noopener">Open SVG ↗</a><a id="dxf-link" class="text-link">Download editable DXF ↓</a><span id="drawing-status" class="badge"></span></div>
<p id="drawing-caption" class="drawing-caption"></p><img id="drawing" class="enclosure-drawing" alt="Issued enclosure drawing" />
<div class="panel-heading"><h2>Issued component schedule</h2><a id="schedule-link" class="text-link">Download CSV ↓</a></div><div class="table-scroll"><table><thead><tr><th>Mark</th><th>Assembly</th><th>Dimensions (in)</th><th>Volume (m³)</th></tr></thead><tbody id="schedule"></tbody></table></div></section>
<section class="panel enclosure-section"><div class="panel-heading"><h2>Source and issue evidence</h2><span class="small-cap">IMMUTABLE RECORDS</span></div><div id="sources" class="enclosure-source"></div></section>
<footer><span>OpenBIM · Enclosure detailing extension</span><span>Review draft · Illustrative dimensions · No structural approval</span></footer></div></main>`;

async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`/api/enclosure${path}`, options);
  if (!response.ok) { const data = await response.json(); throw new Error(typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail)); }
  return response.json();
}
const post = <T>(path: string, body: unknown) => api<T>(path, { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(body) });
function message(text = '') { $('message').textContent = text; $('message').hidden = !text; }
function setBusy(value: boolean) {
  busy = value;
  for (const id of ['baseline','revised','package','issue','compare','generate','upload','diameter','alignment','control']) $<HTMLButtonElement>(id).disabled = value;
}
async function action(work: () => Promise<void>) {
  if (busy) return;
  setBusy(true); message();
  try { await work(); } catch (error) { message(String(error)); } finally { setBusy(false); }
}
function populate(baselineId: string, revisedId: string, packageId: string) {
  for (const [id, value] of [['baseline',baselineId],['revised',revisedId]]) {
    $<HTMLSelectElement>(id!).innerHTML = revisions.map(r => `<option value="${r.id}">${esc(r.filename)} · ${r.id.slice(0,7)}</option>`).join('');
    $<HTMLSelectElement>(id!).value = value!;
  }
  $<HTMLSelectElement>('package').innerHTML = packages.map(p => `<option value="${p.id}">Issue ${esc(p.issue_revision)} · model ${p.source_revision.slice(0,7)} · ${p.id.slice(0,7)}</option>`).join('');
  $<HTMLSelectElement>('package').value = packageId;
}
async function compare() {
  issued = packages.find(p => p.id === $<HTMLSelectElement>('package').value)!;
  report = await post<Report>('/audits', {baseline_id: $<HTMLSelectElement>('baseline').value,
    revised_id: $<HTMLSelectElement>('revised').value, package_id: issued.id});
  selection = report.entries.find(e => e.kind !== 'unchanged') ?? report.entries[0];
  render(); queueViewer();
}
function select(guid: string) {
  selection = report.entries.find(e => e.guid === guid);
  if (selection?.kind === 'removed') side = 'before';
  renderComponents(); renderDetail(); queueViewer();
}
function render() {
  const s = report.summary;
  $('metrics').innerHTML = [
    ['Changed components', s.modified+s.added+s.removed, `${s.unchanged} unchanged`, 'amber'],
    ['Stale documents', s.stale_documents, 'Plan · sections · schedule', s.stale_documents ? 'amber':'teal'],
    ['Alignment findings', s.alignment_findings, 'Declared support layout', s.alignment_findings ? 'amber':'teal'],
    ['Uncertain components', s.uncertain_components, 'Unsupported or missing source data', s.uncertain_components ? 'amber':'teal'],
  ].map(([title, count, note, tone]) => `<article class="metric ${tone}"><span>${title}</span><strong>${count}</strong><small>${note}</small></article>`).join('');
  $<HTMLAnchorElement>('export').href = `/api/enclosure/audits/${report.id}/export`;
  $('export').classList.remove('disabled');
  renderComponents(); renderDetail(); renderDrawing();
  const findings = [...report.drawing_findings.map(f => `<article><h3>${esc(f.document_id)} · ${esc(f.title)}</h3><p>${esc(f.reason)} — issued revision ${esc(issued.issue_revision)}.</p><button class="text-link" data-finding="${f.guids[0]}">Inspect affected component ↗</button></article>`),
    ...report.alignment_findings.map(f => `<article><h3>${esc(f.assembly)} · ${esc(f.state.replaceAll('_',' '))}</h3><ul>${f.reasons.map(r=>`<li>${esc(r)}</li>`).join('')}</ul><button class="text-link" data-finding="${f.guids.find(g => report.entries.find(e=>e.guid===g)?.after?.role === 'post') ?? f.guids[0]}">Inspect post ↗</button></article>`),
    ...report.entries.filter(e=>e.issues.length).map(e=>`<article><h3>${esc((e.after??e.before)?.tag)} · Source review</h3><p>${esc(e.issues.join('; '))}</p></article>`)];
  $('findings').innerHTML = findings.join('') || '<article><h3>No detail discrepancies detected</h3><p>The measured fields agree with the selected package. Owner drawing review remains required.</p></article>';
  $('finding-status').textContent = findings.length ? 'Review required' : 'Consistent';
  for (const button of document.querySelectorAll<HTMLButtonElement>('[data-finding]')) button.onclick=()=>select(button.dataset.finding!);
  $('sources').innerHTML = `<p>Exact GlobalId matching within one project. Changed or missing IDs are reported as added/removed components.</p>${[['Baseline',report.baseline_id],['Revised',report.revised_id]].map(([label,id])=>`<p>${label} SHA-256</p><code>${id}</code><a class="text-link" href="/api/enclosure/revisions/${id}/source">Download ${label!.toLowerCase()} IFC ↓</a>`).join('')}<p>Drawing package SHA-256</p><code>${issued.id}</code><a class="text-link" href="/api/enclosure/packages/${issued.id}" target="_blank" rel="noopener">Open issue manifest ↗</a><p>Package includes source IFC, editable DXFs, SVG sheets, schedule, and artifact hashes. Generating a package records a review draft; it does not approve the design.</p>`;
}
function renderComponents() {
  $('components').innerHTML = report.entries.map(e=>{const c=e.after??e.before!;return `<tr class="${selection?.guid===e.guid?'selected-row':''}"><td><button class="member-button" data-guid="${e.guid}">${esc(c.tag)}</button><small>${esc(c.role)}</small></td><td>${esc(c.assembly)}</td><td>${esc(e.kind)}</td><td>${esc(e.changes.map(c=>fieldName(c.field)).join(', ')||'—')}</td></tr>`;}).join('');
  for (const button of document.querySelectorAll<HTMLButtonElement>('[data-guid]')) button.onclick=()=>select(button.dataset.guid!);
}
function renderDetail() {
  if (!selection) { $('detail').textContent='No component selected.'; return; }
  const e=selection, c=e.after??e.before!;
  const keys=[...new Set([...Object.keys(e.before?.dimensions??{}),...Object.keys(e.after?.dimensions??{})])];
  const value=(r: Component|null,key: string)=>{const v=r?.dimensions?.[key];return v==null?'—':number(key==='volume_m3'?v:v/0.0254);};
  $('detail').innerHTML=`<span class="small-cap">${esc(c.assembly)} / ${esc(e.kind)}</span><h3>${esc(c.tag)}</h3><table class="comparison-table"><thead><tr><th>Dimension</th><th>A</th><th>B</th></tr></thead><tbody>${keys.map(k=>`<tr><th>${esc(fieldName(k))}</th><td>${value(e.before,k)}</td><td class="${e.changes.some(v=>v.field===k)?'value-changed':''}">${value(e.after,k)}</td></tr>`).join('')}</tbody></table>${e.issues.length?`<p class="diagnostics">${esc(e.issues.join('; '))}</p>`:''}<details><summary>Source evidence</summary><p>GlobalId: ${esc(c.guid)}</p><p>${esc(c.geometry_source)}</p><p>${esc(c.material)}</p><p>Revision: ${esc(c.source.revision_id)}</p></details><p class="enclosure-note">HSS uses an idealized sharp-corner hollow profile. Alignment assumes concentric supports and direct bearing.</p>`;
}
function renderDrawing() {
  const sheet=$<HTMLSelectElement>('sheet').value;
  const base=`/api/enclosure/packages/${issued.id}/files/`;
  $<HTMLImageElement>('drawing').src=`${base}${sheet}.svg`;
  $<HTMLImageElement>('drawing').alt=`${sheet} issued revision ${issued.issue_revision}`;
  $<HTMLAnchorElement>('svg-link').href=`${base}${sheet}.svg`;
  $<HTMLAnchorElement>('dxf-link').href=`${base}${sheet}.dxf`;
  $<HTMLAnchorElement>('schedule-link').href=`${base}schedule.csv`;
  $<HTMLAnchorElement>('download-package').href=`/api/enclosure/packages/${issued.id}/download`;
  const stale=report.drawing_findings.some(f=>f.document_id===sheet);
  $('drawing-status').textContent=stale?'Stale drawing':'Current detail inputs';
  $('drawing-status').classList.toggle('modified',stale);
  $('drawing-caption').textContent=`Showing issued revision ${issued.issue_revision}, from model ${issued.source_revision.slice(0,12)}. ${stale?'This sheet retains the old inputs; compare them with the revised model above.':'Supported detail inputs agree with the selected model.'} Review draft; print scaling depends on the chosen paper size.`;
  $('schedule').innerHTML=issued.schedule.map(r=>`<tr><td>${esc(r.mark)}</td><td>${esc(r.assembly)}</td><td>${Object.entries(r.dimensions_in).map(([k,v])=>`${esc(k.replaceAll('_',' '))}: ${number(v)}`).join(' · ')}</td><td>${number(r.volume_m3)}</td></tr>`).join('');
}
function queueViewer() {
  viewerQueue=viewerQueue.then(async()=>{
    $('viewer-status').textContent='Loading enclosure IFC…';
    try {
      if (!viewer) { const {ModelViewer}=await import('./viewer'); viewer=new ModelViewer($('model-container'),select); await viewer.init(); }
      const revision=side==='before'?report.baseline_id:report.revised_id;
      await viewer.load(revision,report.entries.filter(e=>e.kind!=='unchanged').map(e=>e.guid),`/api/enclosure/revisions/${revision}/source`);
      const component=selection?.[side];
      const found=await viewer.select(component?.guid??null);
      $('viewer-status').textContent=`${side==='before'?'Baseline':'Revised'} enclosure loaded${component&&!found?' · Selection unavailable':''}`;
      $('model-container').dataset.ready='true';
    } catch(error) { $('viewer-status').textContent=`3D unavailable: ${String(error)}. Drawing evidence remains available.`; }
    for(const value of ['before','after']) { $(`view-${value}`).classList.toggle('selected',side===value); $(`view-${value}`).setAttribute('aria-pressed',String(side===value)); }
  }).catch(error=>message(String(error)));
}
$('compare').onclick=()=>void action(compare);
for (const id of ['baseline','revised','package']) $(id).onchange=()=>void action(compare);
for (const [id,key] of [['diameter','revised_id'],['alignment','misaligned_id'],['control','baseline_id']] as const) $(id).onclick=()=>void action(async()=>{populate(demo.baseline_id,demo[key],demo.package_id);await compare();});
$('sheet').onchange=()=>renderDrawing();
for(const value of ['before','after'] as const) $(`view-${value}`).onclick=()=>{side=value;queueViewer();};
$('fit').onclick=()=>void viewer?.fit().catch(error=>message(String(error)));
$('generate').onclick=()=>void action(async()=>{
  const pkg=await post<Package>('/packages',{revision_id:$<HTMLSelectElement>('revised').value,issue_revision:$<HTMLInputElement>('issue').value});
  packages=await api<Package[]>('/packages');
  populate($<HTMLSelectElement>('baseline').value,$<HTMLSelectElement>('revised').value,pkg.id);
  await compare(); message(`Issue ${pkg.issue_revision} generated as a review draft. Alignment findings, if any, remain open.`);
});
$('upload').onchange=()=>void action(async()=>{
  const input=$<HTMLInputElement>('upload'),file=input.files?.[0];if(!file)return;
  try { const form=new FormData();form.set('file',file);const revision=await api<Revision>('/revisions',{method:'POST',body:form});
    revisions=await api<Revision[]>('/revisions');populate($<HTMLSelectElement>('baseline').value,revision.id,$<HTMLSelectElement>('package').value);await compare();
  } finally {input.value='';}
});
void action(async()=>{demo=await api<Demo>('/demo');[revisions,packages]=await Promise.all([api<Revision[]>('/revisions'),api<Package[]>('/packages')]);populate(demo.baseline_id,demo.revised_id,demo.package_id);await compare();});
