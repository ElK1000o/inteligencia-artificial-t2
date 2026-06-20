import { useEffect, useState, ReactNode } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Atom,
  CheckCircle2,
  XCircle,
  FlaskConical,
  AlertTriangle,
  Info,
  ChevronRight,
  GitFork,
  RefreshCw,
} from 'lucide-react';
import { Card } from '../components/ui/Card';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { EmptyState } from '../components/ui/EmptyState';
import { ElementDiagram } from '../components/charts/ElementDiagram';
import { StructureViewer } from '../components/charts/StructureViewer';
import { getMaterial, getMaterialAnalysis, getMaterialStructure, getMaterialDecomposition } from '../api/materials';
import { MaterialDetail, MaterialAnalysis, CrystalStructure, InstabilityFactor, DecompositionData } from '../types';

type PageTab = 'properties' | 'analysis' | 'structure';

// ---- helpers ----------------------------------------------------------------

const SEVERITY_STYLES: Record<string, string> = {
  high: 'border-red-500/40 bg-red-500/10',
  medium: 'border-amber-500/40 bg-amber-500/10',
  low: 'border-blue-500/40 bg-blue-500/10',
};
const SEVERITY_ICON: Record<string, ReactNode> = {
  high: <AlertTriangle size={15} className="text-red-400 shrink-0 mt-0.5" />,
  medium: <AlertTriangle size={15} className="text-amber-400 shrink-0 mt-0.5" />,
  low: <Info size={15} className="text-blue-400 shrink-0 mt-0.5" />,
};
const VERDICT_STYLES: Record<string, string> = {
  stable: 'border-green-500/50 bg-green-500/10 text-green-400',
  metastable: 'border-amber-500/50 bg-amber-500/10 text-amber-400',
  unstable: 'border-red-500/50 bg-red-500/10 text-red-400',
  unknown: 'border-gray-600 bg-gray-800 text-gray-400',
};

function OxidationBadge({ el, ox }: { el: string; ox: number }) {
  const label = ox > 0 ? `${el}${ox > 1 ? ox : ''}⁺` : `${el}${Math.abs(ox) > 1 ? Math.abs(ox) : ''}⁻`;
  const color = ox > 0 ? 'text-cyan-400 border-cyan-700' : 'text-rose-400 border-rose-700';
  return (
    <span className={`px-2 py-0.5 rounded-full border text-xs font-mono ${color}`}>
      {label} ({ox > 0 ? '+' : ''}{ox})
    </span>
  );
}

function BarGauge({ value, min, max, color }: { value: number; min: number; max: number; color: string }) {
  const pct = Math.max(0, Math.min(100, ((value - min) / (max - min)) * 100));
  return (
    <div className="relative h-2 bg-navy-700 rounded-full overflow-hidden w-full">
      <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, background: color }} />
    </div>
  );
}

function FactorCard({ factor }: { factor: InstabilityFactor }) {
  const [open, setOpen] = useState(false);
  const style = SEVERITY_STYLES[factor.severity] ?? SEVERITY_STYLES.low;
  const icon = SEVERITY_ICON[factor.severity] ?? SEVERITY_ICON.low;

  return (
    <div className={`border rounded-xl p-3 ${style} cursor-pointer select-none`} onClick={() => setOpen(!open)}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-start gap-2 flex-1">
          {icon}
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-gray-200">{factor.factor}</span>
              {factor.value !== null && (
                <span className="text-xs font-mono text-gray-400">
                  {factor.value} {factor.unit ?? ''}
                </span>
              )}
            </div>
          </div>
        </div>
        <ChevronRight
          size={14}
          className={`text-gray-500 shrink-0 transition-transform ${open ? 'rotate-90' : ''}`}
        />
      </div>
      {open && (
        <div className="mt-2 pl-5 space-y-1">
          <p className="text-xs text-gray-300 leading-relaxed">{factor.explanation}</p>
          {factor.threshold_note && (
            <p className="text-xs text-gray-500 italic">{factor.threshold_note}</p>
          )}
        </div>
      )}
    </div>
  );
}

// ---- main component ---------------------------------------------------------

export function MaterialDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [material, setMaterial] = useState<MaterialDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const [tab, setTab] = useState<PageTab>('properties');
  const [analysis, setAnalysis] = useState<MaterialAnalysis | null>(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);

  const [structure, setStructure] = useState<CrystalStructure | null>(null);
  const [structureLoading, setStructureLoading] = useState(false);
  const [structureError, setStructureError] = useState<string | null>(null);

  const [decomposition, setDecomposition] = useState<DecompositionData | null>(null);
  const [decompositionLoading, setDecompositionLoading] = useState(false);
  const [decompositionError, setDecompositionError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    getMaterial(id)
      .then((r) => setMaterial(r.data))
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, [id]);

  function handleTabSwitch(t: PageTab) {
    setTab(t);
    if (t === 'analysis' && !analysis && !analysisLoading && id) {
      setAnalysisLoading(true);
      setAnalysisError(null);
      getMaterialAnalysis(id)
        .then((r) => setAnalysis(r.data))
        .catch(() => setAnalysisError('No se pudo cargar el análisis. Intente nuevamente.'))
        .finally(() => setAnalysisLoading(false));
    }
    if (t === 'structure' && !structure && !structureLoading && id) {
      setStructureLoading(true);
      setStructureError(null);
      getMaterialStructure(id)
        .then((r) => setStructure(r.data))
        .catch((e) => {
          const detail = e?.response?.data?.detail;
          setStructureError(detail ?? 'No se encontró estructura en Materials Project para esta fórmula.');
        })
        .finally(() => setStructureLoading(false));
    }
  }

  function handleLoadDecomposition() {
    if (decompositionLoading || decomposition || !id) return;
    setDecompositionLoading(true);
    setDecompositionError(null);
    getMaterialDecomposition(id)
      .then((r) => setDecomposition(r.data))
      .catch((e) => {
        const detail = e?.response?.data?.detail;
        setDecompositionError(detail ?? 'No se pudo calcular la vía de descomposición.');
      })
      .finally(() => setDecompositionLoading(false));
  }

  if (loading) return <LoadingSpinner />;

  if (error || !material) {
    return (
      <EmptyState
        icon={<Atom size={48} />}
        title="Material no encontrado"
        description="No se pudo cargar el material solicitado."
        action={
          <button
            onClick={() => navigate('/materials')}
            className="px-4 py-2 bg-cyan-500 hover:bg-cyan-400 text-navy-900 text-sm font-medium rounded-lg"
          >
            Volver a Materiales
          </button>
        }
      />
    );
  }

  const tabs: { key: PageTab; label: string }[] = [
    { key: 'properties', label: 'Propiedades' },
    { key: 'analysis', label: 'Análisis Químico' },
    { key: 'structure', label: 'Estructura 3D' },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start gap-4">
        <button
          onClick={() => navigate('/materials')}
          className="mt-1 p-2 text-gray-400 hover:text-white hover:bg-navy-700 rounded-lg transition-colors"
        >
          <ArrowLeft size={18} />
        </button>
        <div className="flex-1">
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-2xl font-bold font-mono text-cyan-400">{material.formula}</h1>
            {material.reduced_formula && material.reduced_formula !== material.formula && (
              <span className="text-gray-500 font-mono text-lg">({material.reduced_formula})</span>
            )}
          </div>
          <div className="flex items-center gap-2 mt-2 flex-wrap">
            {material.chemsys && (
              <span className="px-2 py-0.5 bg-navy-600 text-gray-300 rounded text-xs">{material.chemsys}</span>
            )}
            {material.nelements != null && (
              <span className="px-2 py-0.5 bg-navy-600 text-gray-400 rounded text-xs">
                {material.nelements} elemento{material.nelements !== 1 ? 's' : ''}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Composition pills */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card title="Composición">
          {material.elements && material.elements.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {material.elements.map((el) => (
                <div
                  key={el}
                  className="px-4 py-3 bg-navy-700 border border-navy-500 rounded-xl text-center min-w-[3rem]"
                >
                  <div className="text-lg font-bold font-mono text-cyan-400">{el}</div>
                </div>
              ))}
            </div>
          ) : (
            <span className="text-gray-500 text-sm">No hay datos de elementos disponibles.</span>
          )}
        </Card>

        <Card title="Metadatos" className="lg:col-span-2">
          <div className="grid grid-cols-2 gap-y-3 text-sm">
            <span className="text-gray-500">ID del Material</span>
            <span className="text-gray-300 font-mono text-xs truncate">{material.id}</span>
            <span className="text-gray-500">ID del Dataset</span>
            <span className="text-gray-300 font-mono text-xs truncate">{material.dataset_id}</span>
            <span className="text-gray-500">Creado el</span>
            <span className="text-gray-300 text-xs">
              {material.created_at ? new Date(material.created_at).toLocaleString() : '—'}
            </span>
          </div>
        </Card>
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 border-b border-navy-600">
        {tabs.map(({ key, label }) => (
          <button
            key={key}
            onClick={() => handleTabSwitch(key)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              tab === key
                ? 'border-cyan-400 text-cyan-400'
                : 'border-transparent text-gray-500 hover:text-gray-300'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* ---- PROPERTIES TAB ---- */}
      {tab === 'properties' && (
        <Card
          title="Propiedades DFT"
          subtitle={`${material.properties.length} propiedades disponibles`}
        >
          {material.properties.length === 0 ? (
            <EmptyState title="Sin propiedades" description="No hay propiedades calculadas disponibles para este material." />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-navy-600">
                    <th className="text-left py-2 px-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Propiedad</th>
                    <th className="text-right py-2 px-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Valor</th>
                    <th className="text-left py-2 px-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Unidad</th>
                    <th className="text-center py-2 px-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">DFT</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-navy-700">
                  {material.properties.map((prop, idx) => (
                    <tr key={idx} className="hover:bg-navy-700/30 transition-colors">
                      <td className="py-2.5 px-3 font-medium text-gray-200">{prop.property_name}</td>
                      <td className="py-2.5 px-3 text-right font-mono text-cyan-400">
                        {prop.value_float != null
                          ? Number.isInteger(prop.value_float)
                            ? prop.value_float
                            : prop.value_float.toFixed(6)
                          : prop.value_str ?? '—'}
                      </td>
                      <td className="py-2.5 px-3 text-gray-500 text-xs">{prop.unit ?? ''}</td>
                      <td className="py-2.5 px-3 text-center">
                        {prop.is_dft_computed ? (
                          <CheckCircle2 size={14} className="mx-auto text-green-400" />
                        ) : (
                          <XCircle size={14} className="mx-auto text-gray-600" />
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}

      {/* ---- ANALYSIS TAB ---- */}
      {tab === 'analysis' && (
        <div className="space-y-6">
          {analysisLoading && (
            <div className="flex justify-center py-16">
              <LoadingSpinner />
            </div>
          )}

          {analysisError && (
            <div className="p-4 rounded-xl border border-red-500/40 bg-red-500/10 text-red-300 text-sm">
              {analysisError}
            </div>
          )}

          {analysis && (
            <>
              {/* Stability verdict */}
              <div className={`rounded-2xl border p-5 ${VERDICT_STYLES[analysis.stability_verdict]}`}>
                <div className="flex items-center gap-3">
                  <div className="text-3xl font-bold">{analysis.verdict_text}</div>
                  {analysis.dft_properties.energy_above_hull !== null && (
                    <span className="px-2 py-0.5 text-xs font-mono rounded-full bg-black/20 border border-current">
                      EAH = {analysis.dft_properties.energy_above_hull.toFixed(4)} eV/átomo
                    </span>
                  )}
                </div>
                <p className="mt-1 text-sm opacity-80">{analysis.verdict_detail}</p>
              </div>

              {/* DFT property quick-stats */}
              {(analysis.dft_properties.energy_above_hull !== null ||
                analysis.dft_properties.formation_energy_per_atom !== null ||
                analysis.dft_properties.band_gap !== null) && (
                <div className="grid grid-cols-3 gap-3">
                  {analysis.dft_properties.energy_above_hull !== null && (
                    <div className="bg-navy-800 border border-navy-600 rounded-xl p-3 text-center">
                      <div className="text-xs text-gray-500 mb-1">Energía sobre el Casco Convexo</div>
                      <div className="text-lg font-mono font-bold text-cyan-400">
                        {analysis.dft_properties.energy_above_hull.toFixed(4)}
                      </div>
                      <div className="text-xs text-gray-500">eV/átomo</div>
                      <BarGauge
                        value={Math.max(0, analysis.dft_properties.energy_above_hull)}
                        min={0}
                        max={0.5}
                        color={
                          analysis.dft_properties.energy_above_hull <= 0.05
                            ? '#22c55e'
                            : analysis.dft_properties.energy_above_hull <= 0.1
                            ? '#f59e0b'
                            : '#ef4444'
                        }
                      />
                    </div>
                  )}
                  {analysis.dft_properties.formation_energy_per_atom !== null && (
                    <div className="bg-navy-800 border border-navy-600 rounded-xl p-3 text-center">
                      <div className="text-xs text-gray-500 mb-1">Energía de Formación</div>
                      <div className="text-lg font-mono font-bold text-violet-400">
                        {analysis.dft_properties.formation_energy_per_atom.toFixed(4)}
                      </div>
                      <div className="text-xs text-gray-500">eV/átomo</div>
                    </div>
                  )}
                  {analysis.dft_properties.band_gap !== null && (
                    <div className="bg-navy-800 border border-navy-600 rounded-xl p-3 text-center">
                      <div className="text-xs text-gray-500 mb-1">Band Gap</div>
                      <div className="text-lg font-mono font-bold text-emerald-400">
                        {analysis.dft_properties.band_gap.toFixed(3)}
                      </div>
                      <div className="text-xs text-gray-500">eV</div>
                    </div>
                  )}
                </div>
              )}

              {/* Element diagram */}
              <Card title="Perfil Atómico" subtitle="Electronegatividad (χ) y radio atómico por elemento">
                <ElementDiagram elements={analysis.element_data} />
              </Card>

              {/* Composition stats */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <Card title="Estadísticas de Composición">
                  <div className="space-y-3 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-500">Elementos</span>
                      <span className="font-mono text-gray-200">{analysis.composition_stats.n_elements}</span>
                    </div>
                    <div>
                      <div className="flex justify-between mb-1">
                        <span className="text-gray-500">Dispersión de electronegatividad</span>
                        <span className="font-mono text-gray-200">
                          {analysis.composition_stats.electronegativity_spread.toFixed(2)} Pauling
                        </span>
                      </div>
                      <BarGauge
                        value={analysis.composition_stats.electronegativity_spread}
                        min={0}
                        max={3.5}
                        color={
                          analysis.composition_stats.electronegativity_spread > 2.4
                            ? '#ef4444'
                            : analysis.composition_stats.electronegativity_spread > 1.8
                            ? '#f59e0b'
                            : '#22c55e'
                        }
                      />
                    </div>
                    <div>
                      <div className="flex justify-between mb-1">
                        <span className="text-gray-500">Mismatch de tamaño</span>
                        <span className="font-mono text-gray-200">
                          {(analysis.composition_stats.size_mismatch_ratio * 100).toFixed(1)}%
                        </span>
                      </div>
                      <BarGauge
                        value={analysis.composition_stats.size_mismatch_ratio * 100}
                        min={0}
                        max={100}
                        color={
                          analysis.composition_stats.size_mismatch_ratio > 0.7
                            ? '#ef4444'
                            : analysis.composition_stats.size_mismatch_ratio > 0.4
                            ? '#f59e0b'
                            : '#22c55e'
                        }
                      />
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">Balance de carga</span>
                      {analysis.composition_stats.charge_balanced === true ? (
                        <span className="flex items-center gap-1 text-green-400 text-xs">
                          <CheckCircle2 size={13} /> Válido
                        </span>
                      ) : analysis.composition_stats.charge_balanced === false ? (
                        <span className="flex items-center gap-1 text-red-400 text-xs">
                          <XCircle size={13} /> Sin asignación válida
                        </span>
                      ) : (
                        <span className="text-gray-500 text-xs">Desconocido</span>
                      )}
                    </div>
                  </div>
                </Card>

                <Card title="Estados de Oxidación" subtitle="Asignación más probable">
                  {Object.keys(analysis.composition_stats.dominant_oxidation_states).length > 0 ? (
                    <div className="flex flex-wrap gap-2">
                      {Object.entries(analysis.composition_stats.dominant_oxidation_states).map(([el, ox]) => (
                        <OxidationBadge key={el} el={el} ox={ox} />
                      ))}
                    </div>
                  ) : (
                    <span className="text-gray-500 text-sm">No se encontró una asignación válida de estados de oxidación.</span>
                  )}
                  {Object.keys(analysis.composition_stats.dominant_oxidation_states).length > 0 && (
                    <p className="mt-3 text-xs text-gray-500 leading-relaxed">
                      Balance de carga: positivos + negativos = 0 por unidad de fórmula. Derivado por pymatgen a partir de valencias
                      iónicas comunes, sin requerir datos de estructura.
                    </p>
                  )}
                </Card>
              </div>

              {/* Instability factors */}
              <Card
                title="Factores de Inestabilidad"
                subtitle={
                  analysis.instability_factors.length === 0
                    ? 'No se detectaron factores de inestabilidad significativos'
                    : `${analysis.instability_factors.length} factor${analysis.instability_factors.length > 1 ? 'es' : ''} identificado${analysis.instability_factors.length > 1 ? 's' : ''} — clic para expandir`
                }
              >
                {analysis.instability_factors.length === 0 ? (
                  <div className="flex items-center gap-2 p-3 rounded-xl border border-green-500/30 bg-green-500/10">
                    <CheckCircle2 size={16} className="text-green-400" />
                    <span className="text-sm text-green-300">
                      No se detectaron factores de inestabilidad química significativos para esta composición.
                    </span>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {analysis.instability_factors.map((f, i) => (
                      <FactorCard key={i} factor={f} />
                    ))}
                  </div>
                )}
              </Card>

              {/* Decomposition Pathway */}
              <Card
                title="Vía de Descomposición"
                subtitle="Fases competidoras estables según el diagrama de fases de Materials Project"
              >
                {!decomposition && !decompositionLoading && !decompositionError && (
                  <div className="flex flex-col items-center gap-3 py-4">
                    <p className="text-sm text-gray-400 text-center max-w-sm">
                      {analysis.stability_verdict === 'stable'
                        ? 'Este material parece termodinámicamente estable — la vía de descomposición aún puede calcularse para verificación.'
                        : 'Cargue el diagrama de fases de Materials Project para ver en qué fases estables se descompondría este material.'}
                    </p>
                    <button
                      onClick={handleLoadDecomposition}
                      className="inline-flex items-center gap-2 px-4 py-2 bg-cyan-500/20 hover:bg-cyan-500/30 border border-cyan-500/40 text-cyan-400 text-sm rounded-lg transition-colors"
                    >
                      <GitFork size={14} /> Cargar Vía de Descomposición
                    </button>
                  </div>
                )}

                {decompositionLoading && (
                  <div className="flex flex-col items-center gap-2 py-6">
                    <RefreshCw size={20} className="text-cyan-400 animate-spin" />
                    <p className="text-sm text-gray-500">
                      Construyendo el diagrama de fases desde Materials Project… (puede tardar ~10 s)
                    </p>
                  </div>
                )}

                {decompositionError && (
                  <div className="p-3 rounded-xl border border-amber-500/40 bg-amber-500/10 text-amber-300 text-sm">
                    {decompositionError}
                  </div>
                )}

                {decomposition && !decomposition.not_in_mp && (
                  <div className="space-y-4">
                    {/* Reaction equation */}
                    <div className="bg-navy-700 rounded-xl p-4 font-mono text-sm text-center leading-relaxed">
                      <span className="text-cyan-400 font-bold">{decomposition.reduced_formula}</span>
                      <span className="text-gray-400 mx-2">→</span>
                      {decomposition.decomposition_products
                        .filter((p) => p.fraction > 1e-6)
                        .map((p, i, arr) => (
                          <span key={p.formula}>
                            <span className="text-gray-300">{p.fraction.toFixed(3)} </span>
                            <span className="text-emerald-400">{p.formula}</span>
                            {i < arr.length - 1 && <span className="text-gray-500 mx-2">+</span>}
                          </span>
                        ))}
                    </div>

                    {/* Energy above hull from MP */}
                    <div className="flex items-center gap-4 text-sm">
                      <div className="flex items-center gap-2">
                        <span className="text-gray-500">EAH (MP):</span>
                        <span className={`font-mono font-bold ${
                          decomposition.energy_above_hull <= 0.025
                            ? 'text-green-400'
                            : decomposition.energy_above_hull <= 0.10
                            ? 'text-amber-400'
                            : 'text-red-400'
                        }`}>
                          {decomposition.energy_above_hull.toFixed(4)} eV/átomo
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-gray-500">Entradas del diagrama de fases:</span>
                        <span className="font-mono text-gray-300">{decomposition.n_pd_entries}</span>
                      </div>
                    </div>

                    {/* Fraction bars */}
                    <div className="space-y-2">
                      <div className="text-xs text-gray-500 uppercase tracking-wider">Fracciones de los productos</div>
                      {decomposition.decomposition_products
                        .filter((p) => p.fraction > 1e-6)
                        .map((p) => (
                          <div key={p.formula} className="flex items-center gap-3">
                            <div className="w-28 text-xs font-mono text-emerald-400 truncate shrink-0">{p.formula}</div>
                            <div className="flex-1 h-3 bg-navy-700 rounded-full overflow-hidden">
                              <div
                                className="h-full rounded-full bg-gradient-to-r from-cyan-600 to-emerald-500 transition-all"
                                style={{ width: `${Math.min(p.fraction * 100, 100)}%` }}
                              />
                            </div>
                            <div className="text-xs font-mono text-gray-300 w-14 text-right shrink-0">
                              {(p.fraction * 100).toFixed(1)}%
                            </div>
                            {p.mp_id && (
                              <div className="text-xs text-gray-600 w-20 truncate shrink-0">{p.mp_id}</div>
                            )}
                          </div>
                        ))}
                    </div>

                    <p className="text-xs text-gray-600 leading-relaxed">{decomposition.source}</p>
                  </div>
                )}

                {decomposition?.not_in_mp && (
                  <div className="p-3 rounded-xl border border-gray-600 bg-navy-700 text-gray-400 text-sm">
                    La fórmula <span className="font-mono text-gray-300">{decomposition.formula}</span> no se encontró
                    en la base de datos de Materials Project. No se puede calcular la descomposición.
                  </div>
                )}
              </Card>

              {/* Structure note */}
              <div className="flex items-start gap-2 p-3 rounded-xl border border-navy-600 bg-navy-800/60">
                <FlaskConical size={15} className="text-cyan-500 shrink-0 mt-0.5" />
                <p className="text-xs text-gray-400 leading-relaxed">{analysis.structure_note}</p>
              </div>
            </>
          )}
        </div>
      )}

      {/* ---- STRUCTURE 3D TAB ---- */}
      {tab === 'structure' && (
        <div className="space-y-4">
          {structureLoading && (
            <div className="flex flex-col items-center justify-center py-20 gap-3">
              <LoadingSpinner />
              <p className="text-sm text-gray-500">Obteniendo la estructura cristalina desde Materials Project…</p>
            </div>
          )}

          {structureError && (
            <div className="p-4 rounded-xl border border-amber-500/40 bg-amber-500/10 text-amber-300 text-sm space-y-1">
              <div className="font-medium">Estructura no disponible</div>
              <div className="text-xs opacity-80">{structureError}</div>
            </div>
          )}

          {structure && (
            <Card
              title={`Estructura Cristalina — ${structure.formula}`}
              subtitle={`${structure.space_group} · ${structure.crystal_system} · ${structure.n_sites} sitios`}
            >
              <StructureViewer structure={structure} />
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
