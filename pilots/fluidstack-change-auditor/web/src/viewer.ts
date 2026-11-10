import * as OBC from '@thatopen/components';
import * as THREE from 'three';
import type { FragmentsModel } from '@thatopen/fragments';

export class ModelViewer {
  private components = new OBC.Components();
  private world = this.components.get(OBC.Worlds).create<OBC.SimpleScene, OBC.SimpleCamera, OBC.SimpleRenderer>();
  private fragments = this.components.get(OBC.FragmentsManager);
  private loader = this.components.get(OBC.IfcLoader);
  private model: FragmentsModel | null = null;
  private revision = '';
  private changed: string[] = [];
  private down = { x: 0, y: 0 };
  private container: HTMLElement;
  private onPick: (guid: string) => void;
  constructor(container: HTMLElement, onPick: (guid: string) => void) {
    this.container = container;
    this.onPick = onPick;
  }

  async init() {
    this.world.scene = new OBC.SimpleScene(this.components);
    this.world.scene.setup();
    this.world.scene.three.background = new THREE.Color('#edf1f0');
    this.world.renderer = new OBC.SimpleRenderer(this.components, this.container, { antialias: true });
    this.world.renderer.three.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
    this.world.camera = new OBC.SimpleCamera(this.components);
    await this.world.camera.controls.setLookAt(11, 9, 12, 2, 1.5, -3);
    this.components.init();
    this.components.get(OBC.Grids).create(this.world);
    this.fragments.init('/vendor/fragments-worker.mjs');
    this.world.camera.controls.addEventListener('update', () => { void this.fragments.core.update(); });
    await this.loader.setup({ autoSetWasm: false, wasm: { path: `${location.origin}/vendor/`, absolute: true } });
    const canvas = this.world.renderer.three.domElement;
    canvas.setAttribute('aria-label', 'Interactive IFC model. Drag to orbit; use the component table for keyboard selection.');
    canvas.addEventListener('pointerdown', e => { this.down = { x: e.clientX, y: e.clientY }; });
    canvas.addEventListener('pointerup', e => {
      if (Math.hypot(e.clientX - this.down.x, e.clientY - this.down.y) > 5) return;
      void this.pick(e).catch(error => this.container.dispatchEvent(new CustomEvent('viewer-error', { detail: error })));
    });
  }

  private async pick(event: PointerEvent) {
    const canvas = this.world.renderer!.three.domElement;
    const box = canvas.getBoundingClientRect();
    const hit = await this.fragments.raycast({ camera: this.world.camera.three, dom: canvas,
      mouse: new THREE.Vector2((event.clientX - box.left) / box.width * 2 - 1, -(event.clientY - box.top) / box.height * 2 + 1) });
    if (hit) { const [guid] = await hit.fragments.getGuidsByLocalIds([hit.localId]); if (guid) this.onPick(guid); }
  }

  async load(revision: string, changed: string[]) {
    this.changed = changed;
    if (this.revision === revision && this.model) return;
    if (this.model) {
      this.world.scene.three.remove(this.model.object);
      await this.fragments.core.disposeModel(this.model.modelId);
      this.model = null;
    }
    this.revision = '';
    const response = await fetch(`/api/revisions/${revision}/source`);
    if (!response.ok) throw new Error('Unable to load source IFC');
    this.model = await this.loader.load(new Uint8Array(await response.arrayBuffer()), false, revision);
    this.model.useCamera(this.world.camera.three);
    this.world.scene.three.add(this.model.object);
    this.revision = revision;
    await this.fragments.core.update(true);
    await this.world.camera.fitToItems();
    await this.fragments.core.update(true);
    this.container.dataset.revision = revision;
  }

  async select(guid: string | null) {
    if (!this.model) return 0;
    await this.model.resetHighlight();
    const color = async (guids: string[], hex: string) => {
      const ids = (await this.model!.getLocalIdsByGuids(guids)).filter((id): id is number => id !== null);
      if (ids.length) await this.model!.highlight(ids, { color: new THREE.Color(hex), renderedFaces: 1, opacity: 1, transparent: false });
      return ids.length;
    };
    await color(this.changed, '#e68b35');
    const found = guid ? await color([guid], '#107c72') : 0;
    this.container.dataset.selectedGuid = found ? guid! : '';
    await this.fragments.core.update(true);
    return found;
  }
  async fit() { await this.world.camera.fitToItems(); }
}
