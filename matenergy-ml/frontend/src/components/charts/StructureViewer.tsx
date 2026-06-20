import { useEffect, useRef, useState } from 'react';
import { CrystalStructure } from '../../types';

declare global {
  interface Window {
    $3Dmol: {
      createViewer: (el: HTMLElement, config: Record<string, unknown>) => Viewer3D;
    };
  }
}

interface Viewer3D {
  addModel: (data: string, fmt: string) => void;
  setStyle: (sel: Record<string, unknown>, style: Record<string, unknown>) => void;
  addUnitCell: () => void;
  zoomTo: () => void;
  render: () => void;
  rotate: (deg: number, axis: string) => void;
  zoom: (factor: number) => void;
  setBackgroundColor: (color: string) => void;
  spin: (axis: string, speed: number) => void;
  stopAnimate: () => void;
}

interface Props {
  structure: CrystalStructure;
}

// CPK-ish element color map (hex strings for 3Dmol)
const ELEMENT_COLORS: Record<string, string> = {
  Li: '0x9B59B6', Na: '0x3498DB', K: '0x1ABC9C',
  Mg: '0x27AE60', Ca: '0x16A085', Ba: '0x8E44AD',
  Fe: '0xE67E22', Co: '0x2980B9', Ni: '0x27AE60',
  Mn: '0xAB47BC', Ti: '0x546E7A', V: '0x6D4C41',
  Cr: '0x37474F', Cu: '0xF39C12', Zn: '0xBDC3C7',
  Al: '0x95A5A6', Si: '0xF39C12', Ge: '0x7F8C8D',
  Sn: '0x7F8C8D', Pb: '0x7F8C8D', Bi: '0xC0392B',
  P: '0xE67E22', S: '0xF1C40F', Se: '0xE67E22',
  Cl: '0x27AE60', F: '0x27AE60', Br: '0xA04000',
  O: '0xE74C3C', N: '0x3498DB', C: '0x2C3E50',
  H: '0xECF0F1',
};

function load3Dmol(): Promise<void> {
  return new Promise((resolve, reject) => {
    if (window.$3Dmol) { resolve(); return; }
    const script = document.createElement('script');
    script.src = 'https://3dmol.org/build/3Dmol-min.js';
    script.onload = () => resolve();
    script.onerror = () => reject(new Error('Failed to load 3Dmol.js'));
    document.head.appendChild(script);
  });
}

// Summarize coordination per unique element (average CN)
function summarizeCoordination(coord: CrystalStructure['coordination']) {
  const byEl: Record<string, number[]> = {};
  for (const c of coord) {
    if (c.cn !== null) {
      byEl[c.element] = byEl[c.element] ?? [];
      byEl[c.element].push(c.cn);
    }
  }
  return Object.entries(byEl).map(([el, cns]) => ({
    element: el,
    avg_cn: Math.round((cns.reduce((a, b) => a + b, 0) / cns.length) * 10) / 10,
    n_sites: cns.length,
  }));
}

export function StructureViewer({ structure }: Props) {
  const viewerRef = useRef<HTMLDivElement>(null);
  const viewer3d = useRef<Viewer3D | null>(null);
  const [viewerReady, setViewerReady] = useState(false);
  const [loadError, setLoadError] = useState('');
  const [spinning, setSpinning] = useState(false);
  const [style, setStyle] = useState<'sphere' | 'stick' | 'ballstick'>('ballstick');

  useEffect(() => {
    load3Dmol()
      .then(() => setViewerReady(true))
      .catch(() => setLoadError('No se pudo cargar el visor 3Dmol.js. Verifica tu conexión a internet.'));
  }, []);

  useEffect(() => {
    if (!viewerReady || !viewerRef.current) return;

    try {
      const v = window.$3Dmol.createViewer(viewerRef.current, {
        backgroundColor: '#0a1628',
        antialias: true,
      });

      v.addModel(structure.cif, 'cif');
      applyStyle(v, style);
      v.addUnitCell();
      v.zoomTo();
      v.rotate(20, 'y');
      v.rotate(10, 'x');
      v.render();
      viewer3d.current = v;
    } catch (e) {
      setLoadError('El visor 3D no pudo inicializarse.');
    }
  }, [viewerReady]);

  function applyStyle(v: Viewer3D, s: typeof style) {
    if (s === 'sphere') {
      v.setStyle({}, { sphere: { scale: 0.4 } });
    } else if (s === 'stick') {
      v.setStyle({}, { stick: { radius: 0.15 } });
    } else {
      v.setStyle({}, { sphere: { scale: 0.28 }, stick: { radius: 0.12 } });
    }
    v.render();
  }

  function handleStyle(s: typeof style) {
    setStyle(s);
    if (viewer3d.current) applyStyle(viewer3d.current, s);
  }

  function handleSpin() {
    if (!viewer3d.current) return;
    if (spinning) {
      viewer3d.current.stopAnimate();
    } else {
      viewer3d.current.spin('y', 1);
    }
    setSpinning(!spinning);
  }

  const coordSummary = summarizeCoordination(structure.coordination);

  return (
    <div className="space-y-6">
      {/* Viewer */}
      <div className="relative rounded-2xl overflow-hidden border border-navy-600" style={{ height: 420 }}>
        {loadError ? (
          <div className="absolute inset-0 flex items-center justify-center text-sm text-red-400 bg-navy-900">
            {loadError}
          </div>
        ) : !viewerReady ? (
          <div className="absolute inset-0 flex items-center justify-center text-sm text-gray-500 bg-navy-900">
            Cargando visor 3Dmol…
          </div>
        ) : null}
        <div ref={viewerRef} className="w-full h-full" />

        {/* Controls overlay */}
        {viewerReady && !loadError && (
          <div className="absolute top-3 right-3 flex flex-col gap-2">
            <div className="flex gap-1 bg-navy-900/80 rounded-lg p-1 backdrop-blur">
              {(['sphere', 'stick', 'ballstick'] as const).map((s) => (
                <button
                  key={s}
                  onClick={() => handleStyle(s)}
                  className={`px-2 py-1 text-xs rounded transition-colors ${
                    style === s ? 'bg-cyan-500 text-navy-900 font-semibold' : 'text-gray-400 hover:text-white'
                  }`}
                >
                  {s === 'ballstick' ? 'esferas+barras' : s === 'sphere' ? 'esferas' : 'barras'}
                </button>
              ))}
            </div>
            <button
              onClick={handleSpin}
              className={`text-xs px-3 py-1 rounded-lg transition-colors ${
                spinning ? 'bg-cyan-500/30 text-cyan-300 border border-cyan-500/50' : 'bg-navy-900/80 text-gray-400 hover:text-white backdrop-blur'
              }`}
            >
              {spinning ? '⏹ Detener' : '▶ Girar'}
            </button>
          </div>
        )}

        {/* MP attribution */}
        <div className="absolute bottom-3 left-3 text-xs text-gray-600">
          {structure.mp_material_id} · Materials Project
        </div>
      </div>

      {/* Lattice parameters */}
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
        {[
          { label: 'a', value: `${structure.lattice.a} Å` },
          { label: 'b', value: `${structure.lattice.b} Å` },
          { label: 'c', value: `${structure.lattice.c} Å` },
          { label: 'α', value: `${structure.lattice.alpha}°` },
          { label: 'β', value: `${structure.lattice.beta}°` },
          { label: 'γ', value: `${structure.lattice.gamma}°` },
        ].map(({ label, value }) => (
          <div key={label} className="bg-navy-800 border border-navy-600 rounded-xl p-3 text-center">
            <div className="text-lg font-mono font-bold text-cyan-400">{value}</div>
            <div className="text-xs text-gray-500 mt-0.5">{label}</div>
          </div>
        ))}
      </div>

      {/* Structure info + coordination */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-navy-800 border border-navy-600 rounded-2xl p-4 space-y-3 text-sm">
          <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Información Cristalina</div>
          {[
            { k: 'Grupo espacial', v: `${structure.space_group} (#${structure.space_group_number})` },
            { k: 'Sistema cristalino', v: structure.crystal_system.charAt(0).toUpperCase() + structure.crystal_system.slice(1) },
            { k: 'Sitios en la celda', v: `${structure.n_sites}` },
            { k: 'Especies', v: `${structure.n_species}` },
            { k: 'Volumen', v: `${structure.lattice.volume} Å³` },
            { k: 'Densidad', v: `${structure.density} g/cm³` },
            { k: 'Polimorfos en MP', v: `${structure.n_polymorphs}` },
          ].map(({ k, v }) => (
            <div key={k} className="flex justify-between">
              <span className="text-gray-500">{k}</span>
              <span className="text-gray-200 font-mono text-xs">{v}</span>
            </div>
          ))}
        </div>

        <div className="bg-navy-800 border border-navy-600 rounded-2xl p-4 space-y-2 text-sm">
          <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Números de Coordinación</div>
          {coordSummary.length === 0 ? (
            <span className="text-gray-500 text-xs">Análisis de coordinación no disponible.</span>
          ) : (
            coordSummary.map(({ element, avg_cn, n_sites }) => (
              <div key={element} className="flex items-center gap-3">
                <div
                  className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold text-white shrink-0"
                  style={{ background: (ELEMENT_COLORS[element] ?? '0x64748b').replace('0x', '#') }}
                >
                  {element}
                </div>
                <div className="flex-1">
                  <div className="flex justify-between mb-0.5">
                    <span className="text-gray-300 font-medium">{element}</span>
                    <span className="text-cyan-400 font-mono text-xs">CN = {avg_cn}</span>
                  </div>
                  <div className="h-1.5 bg-navy-600 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-cyan-500 rounded-full"
                      style={{ width: `${Math.min((avg_cn / 12) * 100, 100)}%` }}
                    />
                  </div>
                  <div className="text-xs text-gray-600 mt-0.5">{n_sites} sitio{n_sites > 1 ? 's' : ''}</div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Bond lengths */}
      {structure.bond_analysis.length > 0 && (
        <div className="bg-navy-800 border border-navy-600 rounded-2xl p-4">
          <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Longitudes de Enlace</div>
          <div className="grid grid-cols-2 lg:grid-cols-3 gap-2">
            {structure.bond_analysis.map((b) => (
              <div key={b.pair} className="bg-navy-700 rounded-xl p-3">
                <div className="text-sm font-mono font-bold text-cyan-400 mb-1">{b.pair}</div>
                <div className="text-xs text-gray-300">
                  <span className="font-medium">{b.mean_ang.toFixed(3)} Å</span>
                  <span className="text-gray-500"> ± {b.std_ang.toFixed(3)}</span>
                </div>
                <div className="text-xs text-gray-500 mt-0.5">
                  {b.min_ang.toFixed(3)}–{b.max_ang.toFixed(3)} Å · {b.n_bonds} enlace{b.n_bonds > 1 ? 's' : ''}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Source attribution */}
      <p className="text-xs text-gray-600 leading-relaxed">{structure.structure_source}</p>
    </div>
  );
}
