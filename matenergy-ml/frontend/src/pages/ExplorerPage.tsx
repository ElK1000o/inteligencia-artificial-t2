import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FlaskConical, Play, RefreshCw, AlertCircle, CheckCircle, BookOpen, ExternalLink } from 'lucide-react';
import { Card } from '../components/ui/Card';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { explorePredict, ExploreResult } from '../api/explore';
import { listDescriptorSets } from '../api/descriptors';
import { DescriptorSet } from '../types';

const TARGET_PROPERTIES = [
  'energy_above_hull',
  'formation_energy_per_atom',
  'band_gap',
  'is_stable',
];

const STABILITY_COLORS: Record<string, string> = {
  stable: 'text-emerald-400 bg-emerald-500/20 border-emerald-500/30',
  metastable: 'text-amber-400 bg-amber-500/20 border-amber-500/30',
  unstable: 'text-red-400 bg-red-500/20 border-red-500/30',
  unknown: 'text-gray-400 bg-gray-500/20 border-gray-500/30',
};

const STABILITY_DESCRIPTIONS: Record<string, string> = {
  stable: 'Energía sobre el casco convexo ≤ 0.05 eV/átomo. Probablemente estable termodinámicamente.',
  metastable: 'Energía sobre el casco convexo 0.05–0.10 eV/átomo. Puede ser sintéticamente accesible.',
  unstable: 'Energía sobre el casco convexo > 0.10 eV/átomo. Termodinámicamente desfavorable.',
  unknown: 'No hay modelo activo para energy_above_hull.',
};

// Display-only Spanish labels for the stability_label enum values (kept in English for lookups)
const STABILITY_LABELS_ES: Record<string, string> = {
  stable: 'Estable',
  metastable: 'Metaestable',
  unstable: 'Inestable',
  unknown: 'Desconocido',
};

interface HistoryEntry {
  formula: string;
  result: ExploreResult;
}

export function ExplorerPage() {
  const navigate = useNavigate();
  const [descriptors, setDescriptors] = useState<DescriptorSet[]>([]);
  const [formula, setFormula] = useState('');
  const [descriptorSetId, setDescriptorSetId] = useState('');
  const [targetProperties, setTargetProperties] = useState<string[]>(['energy_above_hull', 'formation_energy_per_atom']);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ExploreResult | null>(null);
  const [error, setError] = useState('');
  const [history, setHistory] = useState<HistoryEntry[]>([]);

  useEffect(() => {
    listDescriptorSets()
      .then((r) => {
        setDescriptors(r.data);
        if (r.data.length > 0) setDescriptorSetId(r.data[0].id);
      })
      .catch(() => setDescriptors([]));
  }, []);

  const handlePredict = async () => {
    if (!formula.trim() || !descriptorSetId) return;
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const r = await explorePredict({
        formula: formula.trim(),
        descriptor_set_id: descriptorSetId,
        target_properties: targetProperties,
      });
      setResult(r.data);
      setHistory((prev) => [{ formula: formula.trim(), result: r.data }, ...prev.slice(0, 9)]);
    } catch (e: unknown) {
      const detail =
        e && typeof e === 'object' && 'response' in e
          ? (e as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : undefined;
      setError(detail || 'No se pudo predecir. Verifica la fórmula e inténtalo de nuevo.');
    } finally {
      setLoading(false);
    }
  };

  const toggleProperty = (prop: string) => {
    setTargetProperties((prev) =>
      prev.includes(prop) ? prev.filter((p) => p !== prop) : [...prev, prop]
    );
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <FlaskConical className="text-cyan-400" size={24} />
          Explorador de Composiciones
        </h1>
        <p className="text-gray-400 text-sm mt-1">
          Predice propiedades de materiales para cualquier fórmula química — sin ejecutar DFT.
          Usa los modelos de ML activos para evaluar compuestos hipotéticos al instante.
        </p>
      </div>

      {/* Input panel */}
      <Card title="Predecir una Fórmula">
        <div className="space-y-4">
          <div className="flex flex-wrap gap-3">
            <div className="flex-1 min-w-52">
              <label className="block text-xs text-gray-400 mb-1.5">Fórmula Química</label>
              <input
                type="text"
                value={formula}
                onChange={(e) => setFormula(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handlePredict()}
                placeholder="ej. LiCoO2, LiFePO4, Na2TiO3"
                className="w-full bg-navy-700 border border-navy-500 rounded-lg px-4 py-2.5 text-white font-mono placeholder-gray-500 focus:outline-none focus:border-cyan-400 transition-colors"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1.5">Conjunto de Descriptores</label>
              <select
                value={descriptorSetId}
                onChange={(e) => setDescriptorSetId(e.target.value)}
                className="bg-navy-700 border border-navy-500 rounded-lg px-3 py-2.5 text-sm text-gray-200 focus:outline-none focus:border-cyan-400 transition-colors"
              >
                {descriptors.length === 0 ? (
                  <option value="">— sin conjuntos de descriptores —</option>
                ) : (
                  descriptors.map((d) => (
                    <option key={d.id} value={d.id}>{d.name}</option>
                  ))
                )}
              </select>
              {descriptors.length === 0 && (
                <p className="text-xs text-amber-400 mt-1">Genera primero un conjunto de descriptores en la página de Descriptores.</p>
              )}
            </div>
          </div>

          <div>
            <label className="block text-xs text-gray-400 mb-2">Propiedades a Predecir</label>
            <div className="flex flex-wrap gap-2">
              {TARGET_PROPERTIES.map((p) => (
                <button
                  key={p}
                  onClick={() => toggleProperty(p)}
                  className={`px-3 py-1 rounded-lg text-xs font-mono font-medium border transition-colors ${
                    targetProperties.includes(p)
                      ? 'bg-cyan-500/20 border-cyan-500/50 text-cyan-400'
                      : 'bg-navy-700 border-navy-500 text-gray-500 hover:text-gray-300'
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>

          <button
            onClick={handlePredict}
            disabled={loading || !formula.trim() || !descriptorSetId || targetProperties.length === 0}
            className="flex items-center gap-2 px-5 py-2.5 text-sm font-semibold text-navy-900 bg-cyan-500 hover:bg-cyan-400 disabled:opacity-40 disabled:cursor-not-allowed rounded-lg transition-colors"
          >
            {loading ? (
              <><RefreshCw size={15} className="animate-spin" /> Prediciendo…</>
            ) : (
              <><Play size={15} /> Predecir Propiedades</>
            )}
          </button>

          {error && (
            <div className="flex items-start gap-2 bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3 text-sm text-red-400">
              <AlertCircle size={15} className="mt-0.5 shrink-0" />
              {error}
            </div>
          )}
        </div>
      </Card>

      {/* Results */}
      {result && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Left: summary */}
          <div className="lg:col-span-1 space-y-4">
            <Card>
              <div className="text-center py-2">
                <div className="text-3xl font-mono font-bold text-cyan-400 mb-1">{result.formula}</div>
                {result.is_known_material && (
                  <div className="flex items-center justify-center gap-2 text-xs text-emerald-400">
                    <BookOpen size={11} /> Conocido en el dataset
                    {result.material_id && (
                      <button
                        onClick={() => navigate(`/materials/${result.material_id}`)}
                        className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-emerald-500/20 hover:bg-emerald-500/40 border border-emerald-500/30 text-emerald-400 transition-colors"
                        title="Ver detalle del material"
                      >
                        <ExternalLink size={10} /> Ver
                      </button>
                    )}
                  </div>
                )}
                <div className={`inline-flex items-center gap-1.5 mt-3 px-4 py-2 rounded-xl border text-sm font-semibold ${STABILITY_COLORS[result.stability_label]}`}>
                  {result.stability_label === 'stable' ? <CheckCircle size={14} /> : <AlertCircle size={14} />}
                  {STABILITY_LABELS_ES[result.stability_label] ?? result.stability_label}
                </div>
                <p className="text-xs text-gray-500 mt-2 max-w-[220px] mx-auto">
                  {STABILITY_DESCRIPTIONS[result.stability_label]}
                </p>
              </div>
            </Card>
          </div>

          {/* Right: predictions + descriptors preview */}
          <div className="lg:col-span-2 space-y-4">
            <Card title="Propiedades Predichas">
              <div className="grid grid-cols-2 gap-3">
                {Object.entries(result.predictions).map(([prop, val]) => (
                  <div key={prop} className="bg-navy-700 rounded-xl p-4">
                    <div className="text-xs text-gray-500 mb-1 font-mono">{prop}</div>
                    <div className="text-lg font-bold font-mono text-cyan-400">
                      {val !== null ? val.toFixed(4) : <span className="text-gray-600">—</span>}
                    </div>
                    {prop.includes('energy') && (
                      <div className="text-xs text-gray-600 mt-0.5">eV/átomo</div>
                    )}
                    {prop === 'band_gap' && (
                      <div className="text-xs text-gray-600 mt-0.5">eV</div>
                    )}
                  </div>
                ))}
              </div>
            </Card>

            <Card title="Variables de Descriptores Clave">
              <div className="space-y-2">
                {Object.entries(result.descriptors_preview).map(([name, val]) => (
                  <div key={name} className="flex items-center gap-3">
                    <div className="text-xs text-gray-500 font-mono w-52 truncate shrink-0" title={name}>{name}</div>
                    <div className="flex-1 h-1.5 bg-navy-600 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-cyan-500 rounded-full"
                        style={{
                          width: `${Math.min(Math.abs(val) * 20, 100)}%`,
                          transition: 'width 0.6s ease-out',
                        }}
                      />
                    </div>
                    <div className="text-xs font-mono text-gray-300 w-16 text-right">{val.toFixed(3)}</div>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        </div>
      )}

      {/* Comparison history */}
      {history.length > 1 && (
        <Card title={`Comparación — Últimas ${history.length} Fórmulas`}>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-navy-600">
                  <th className="text-left py-2 px-3 text-xs text-gray-500 uppercase">Fórmula</th>
                  <th className="text-left py-2 px-3 text-xs text-gray-500 uppercase">Estabilidad</th>
                  {TARGET_PROPERTIES.filter((p) => history[0].result.predictions[p] !== undefined).map((p) => (
                    <th key={p} className="text-right py-2 px-3 text-xs text-gray-500 uppercase font-mono">{p}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-navy-700">
                {history.map((h, i) => (
                  <tr
                    key={i}
                    onClick={() => setResult(h.result)}
                    className="hover:bg-navy-700/50 cursor-pointer transition-colors"
                  >
                    <td className="py-2.5 px-3 font-mono text-cyan-400">{h.formula}</td>
                    <td className="py-2.5 px-3">
                      <span className={`px-2 py-0.5 rounded text-xs font-medium border ${STABILITY_COLORS[h.result.stability_label]}`}>
                        {STABILITY_LABELS_ES[h.result.stability_label] ?? h.result.stability_label}
                      </span>
                    </td>
                    {TARGET_PROPERTIES.filter((p) => h.result.predictions[p] !== undefined).map((p) => (
                      <td key={p} className="py-2.5 px-3 text-right font-mono text-gray-300">
                        {h.result.predictions[p] !== null ? (h.result.predictions[p] as number).toFixed(4) : '—'}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Scientific guide */}
      {!result && !loading && (
        <Card title="Cómo usar esta herramienta">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5 text-sm">
            {[
              {
                step: '1',
                title: 'Escribe una fórmula',
                desc: 'Ingresa cualquier fórmula estequiométrica — real o hipotética. Ejemplos: LiCoO2, Li2MnO3, Na3V2(PO4)3, K0.5Co0.5FeO2.',
                color: 'text-cyan-400',
              },
              {
                step: '2',
                title: 'El ML predice al instante',
                desc: 'El sistema calcula ~130 descriptores composicionales y los pasa por el modelo scikit-learn activo. No requiere DFT — resultados en milisegundos.',
                color: 'text-purple-400',
              },
              {
                step: '3',
                title: 'Evalúa candidatos',
                desc: 'Compara múltiples fórmulas en la tabla de historial. Los materiales con energía sobre el casco convexo < 0.05 eV/átomo son candidatos estables para síntesis de cátodos de batería.',
                color: 'text-emerald-400',
              },
            ].map((s) => (
              <div key={s.step} className="flex gap-3">
                <div className={`text-2xl font-bold ${s.color} shrink-0 w-7`}>{s.step}</div>
                <div>
                  <div className="font-medium text-white mb-1">{s.title}</div>
                  <div className="text-gray-500 text-xs leading-relaxed">{s.desc}</div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
