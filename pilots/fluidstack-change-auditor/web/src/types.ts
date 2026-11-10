export interface Source { revision_id: string; step_id: number; global_id: string | null; entity: string; file: string }
export interface Component {
  key: string; guid: string | null; tag: string | null; name: string | null; class: string;
  source: Source; issues: string[]; specification: string | null;
  geometry: { length_m: number; width_m: number; height_m: number; volume_m3: number; source_path: string } | null;
  material_source: { step_id: number; name: string }[];
}
export interface Entry {
  id: string; kind: string; confidence: string; match_method: string; before: Component | null; after: Component | null;
  changes: { field: string; before: unknown; after: unknown; delta?: number; unit: string | null }[];
  issues: string[]; review_state: string; bom_line_ids: string[];
}
export interface Impact {
  id: string; change_id: string; tag: string; rule: string; state: string; message: string;
  bom_line_id: string | null; po_line_id: string | null;
  ordered: { specification: string; length_m: number; count: number; status: string } | null;
}
export interface Revision { id: string; filename: string; schema: string; length_unit_to_m: number; component_count?: number }
export interface Report {
  diagnostics: string[]; review_state: string;
  id: string; engine_version: string; baseline: Revision; revised: Revision; procurement_sha256: string;
  summary: Record<string, number>; entries: Entry[]; impacts: Impact[]; scope: string;
  tolerances: { length_m: number; volume_m3: number };
}
export interface AuditRequest { baseline_id: string; revised_id: string; procurement_id: string }
