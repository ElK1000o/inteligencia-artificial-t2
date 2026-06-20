import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Zap,
  Play,
  AlertTriangle,
  CheckCircle,
  XCircle,
  RefreshCw,
  Sparkles,
  ExternalLink,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
} from 'recharts';
import { Card } from '../components/ui/Card';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { Modal } from '../components/ui/Modal';
import { ParetoPlot, ParetoPoint } from '../components/charts/ParetoPlot';
import { ShapWaterfallChart, ShapContribution } from '../components/charts/ShapWaterfallChart';
import { ShapNarrative } from '../components/charts/ShapNarrative';
import { generateShapNarrative } from '../utils/shapNarrative';
import { listModels, explainPrediction } from '../api/models';
import { listDatasets } from '../api/datasets';
import { listMaterials } from '../api/materials';
import { runPredictions, PredictionResult } from '../api/predictions';
import { ModelVersion, Dataset, Material } from '../types';

const TARGET_PROPERTIES = [
  { value: 'energy_above_hull', label: 'Energía sobre el Casco Convexo (eV/átomo)' },
  { value: 'formation_energy_per_atom', label: 'Energía de Formación (eV/átomo)' },
  { value: 'band_gap', label: 'Band Gap (eV)' },
  { value: 'is_stable', label: 'Estabilidad (Clasificación)' },
];

function OODBadge({ ood }: { ood: boolean }) {
  return ood ? (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-amber-500/20 text-amber-400 rounded text-xs font-medium">
      <AlertTriangle size={10} /> OOD
    </span>
  ) : (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-emerald-500/20 text-emerald-400 rounded text-xs font-medium">
      <CheckCircle size={10} /> OK
    </span>
  );
}

export function PredictionsPage() {
  const navigate = useNavigate();
  const [models, setModels] = useState<ModelVersion[]>([]);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [materials, setMaterials] = useState<Material[]>([]);

  const [selectedModel, setSelectedModel] = useState('');
  const [selectedDataset, setSelectedDataset] = useState('');
  const [targetProperty, setTargetProperty] = useState('energy_above_hull');

  const [loading, setLoading] = useState(false);
  const [loadingMaterials, setLoadingMaterials] = useState(false);
  const [results, setResults] = useState<PredictionResult[] | null>(null);
  const [batchMeta, setBatchMeta] = useState<{ batch_id: string; n_ood: number } | null>(null);
  const [error, setError] = useState<string | null>(null);

  // SHAP modal state
  const [shapOpen, setShapOpen] = useState(false);
  const [shapLoading, setShapLoading] = useState(false);
  const [shapData, setShapData] = useState<{
    formula: string;
    base_value: number;
    predicted_value: number;
    target_property: string;
    feature_contributions: ShapContribution[];
  } | null>(null);
  const [shapError, setShapError] = useState('');

  useEffect(() => {
    listModels()
      .then((r) => setModels(r.data))
      .catch(() => setModels([]));
    listDatasets()
      .then((r) => setDatasets(r.data))
      .catch(() => setDatasets([]));
  }, []);

  useEffect(() => {
    if (!selectedDataset) {
      setMaterials([]);
      return;
    }
    setLoadingMaterials(true);
    listMaterials({ dataset_id: selectedDataset, limit: 200 })
      .then((r) => setMaterials(r.data))
      .catch(() => setMaterials([]))
      .finally(() => setLoadingMaterials(false));
  }, [selectedDataset]);

  const activeModels = models.filter((m) => m.is_active);

  const handleRun = async () => {
    if (!selectedDataset || !targetProperty) return;
    if (materials.length === 0) {
      setError('No hay materiales cargados para el dataset seleccionado.');
      return;
    }

    setLoading(true);
    setError(null);
    setResults(null);
    setBatchMeta(null);

    try {
      const payload: {
        target_property: string;
        material_ids: string[];
        dataset_id: string;
        model_version_id?: string;
      } = {
        target_property: targetProperty,
        material_ids: materials.map((m) => m.id),
        dataset_id: selectedDataset,
      };
      if (selectedModel) payload.model_version_id = selectedModel;

      const resp = await runPredictions(payload);
      setResults(resp.data.predictions);
      setBatchMeta({ batch_id: resp.data.batch_id, n_ood: resp.data.n_ood });
    } catch (e: unknown) {
      const msg =
        e && typeof e === 'object' && 'message' in e
          ? String((e as { message: unknown }).message)
          : 'La predicción falló';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  // Distribution chart: bin predicted values
  const histogramData = (() => {
    if (!results) return [];
    const values = results
      .map((r) => r.predicted_value)
      .filter((v): v is number => v !== null && !Number.isNaN(v));
    if (values.length === 0) return [];
    const min = Math.min(...values);
    const max = Math.max(...values);
    if (min === max) return [{ bin: min.toFixed(3), count: values.length }];
    const N_BINS = 10;
    const step = (max - min) / N_BINS;
    const bins = Array.from({ length: N_BINS }, (_, i) => ({
      bin: (min + i * step).toFixed(3),
      count: 0,
      isOod: false,
    }));
    values.forEach((v) => {
      const idx = Math.min(Math.floor((v - min) / step), N_BINS - 1);
      bins[idx].count += 1;
    });
    return bins.filter((b) => b.count > 0);
  })();

  const nOod = results?.filter((r) => r.is_out_of_domain).length ?? 0;
  const nErrors = results?.filter((r) => r.error).length ?? 0;
  const nOk = results ? results.length - nErrors : 0;

  const formulaMap = Object.fromEntries(materials.map((m) => [m.id, m.formula]));

  const handleExplain = async (result: PredictionResult) => {
    const modelId = selectedModel || activeModels.find((m) => m.target_property === targetProperty)?.id;
    if (!modelId || !selectedDataset) return;
    setShapOpen(true);
    setShapLoading(true);
    setShapData(null);
    setShapError('');
    try {
      const r = await explainPrediction(modelId, {
        material_id: result.material_id,
        dataset_id: selectedDataset,
      });
      setShapData({
        formula: r.data.formula || formulaMap[result.material_id] || result.material_id.slice(0, 8),
        base_value: r.data.base_value,
        predicted_value: r.data.predicted_value,
        target_property: r.data.target_property,
        feature_contributions: r.data.feature_contributions,
      });
    } catch {
      setShapError('No se pudieron calcular los valores SHAP. El modelo puede no admitir explicabilidad.');
    } finally {
      setShapLoading(false);
    }
  };

  // Build Pareto points if results contain energy_above_hull predictions
  const paretoPoints: ParetoPoint[] = results
    ? results
        .filter((r) => !r.error && r.predicted_value !== null && targetProperty === 'energy_above_hull')
        .map((r) => ({
          material_id: r.material_id,
          formula: formulaMap[r.material_id] ?? r.material_id.slice(0, 8),
          energy_above_hull: r.predicted_value ?? 0,
          formation_energy_per_atom: 0, // placeholder — filled below if available
        }))
    : [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Predicciones</h1>
        <p className="text-gray-400 text-sm mt-1">
          Ejecuta inferencia por lotes sobre datasets de materiales usando modelos entrenados
        </p>
      </div>

      {/* Configuration panel */}
      <Card title="Configuración de Predicción">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-400 mb-1.5">
              Propiedad Objetivo
            </label>
            <select
              value={targetProperty}
              onChange={(e) => setTargetProperty(e.target.value)}
              className="w-full bg-navy-700 border border-navy-500 rounded-lg px-3 py-2.5 text-sm text-gray-200 focus:outline-none focus:border-cyan-400 transition-colors"
            >
              {TARGET_PROPERTIES.map((p) => (
                <option key={p.value} value={p.value}>
                  {p.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-400 mb-1.5">
              Dataset
            </label>
            <select
              value={selectedDataset}
              onChange={(e) => setSelectedDataset(e.target.value)}
              className="w-full bg-navy-700 border border-navy-500 rounded-lg px-3 py-2.5 text-sm text-gray-200 focus:outline-none focus:border-cyan-400 transition-colors"
            >
              <option value="">Selecciona un dataset…</option>
              {datasets.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-400 mb-1.5">
              Modelo Alternativo{' '}
              <span className="text-gray-600 font-normal">(opcional — usa el modelo activo)</span>
            </label>
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="w-full bg-navy-700 border border-navy-500 rounded-lg px-3 py-2.5 text-sm text-gray-200 focus:outline-none focus:border-cyan-400 transition-colors"
            >
              <option value="">Automático (modelo activo)</option>
              {activeModels.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.name} — {m.model_type} ({m.target_property})
                </option>
              ))}
            </select>
          </div>
        </div>

        {selectedDataset && (
          <div className="mt-3 text-xs text-gray-500">
            {loadingMaterials ? (
              <span className="flex items-center gap-1.5">
                <RefreshCw size={12} className="animate-spin" /> Cargando materiales…
              </span>
            ) : (
              <span>
                {materials.length} material{materials.length !== 1 ? 'es' : ''} listo{materials.length !== 1 ? 's' : ''} para predicción
              </span>
            )}
          </div>
        )}

        <div className="mt-5">
          <button
            onClick={handleRun}
            disabled={loading || !selectedDataset || loadingMaterials || materials.length === 0}
            className="flex items-center gap-2 px-5 py-2.5 text-sm font-semibold text-navy-900 bg-cyan-500 hover:bg-cyan-400 disabled:opacity-40 disabled:cursor-not-allowed rounded-lg transition-colors"
          >
            {loading ? (
              <>
                <RefreshCw size={15} className="animate-spin" /> Ejecutando…
              </>
            ) : (
              <>
                <Play size={15} /> Ejecutar Predicciones
              </>
            )}
          </button>
        </div>
      </Card>

      {/* Error state */}
      {error && (
        <div className="flex items-start gap-3 p-4 bg-red-500/10 border border-red-500/30 rounded-xl">
          <XCircle size={18} className="text-red-400 mt-0.5 shrink-0" />
          <div>
            <p className="text-sm font-medium text-red-300">La predicción falló</p>
            <p className="text-xs text-red-400 mt-0.5">{error}</p>
          </div>
        </div>
      )}

      {/* Results */}
      {results && (
        <>
          {/* Summary cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {[
              { label: 'Predicciones', value: nOk, color: 'text-cyan-400' },
              { label: 'Fuera de Dominio', value: nOod, color: 'text-amber-400' },
              { label: 'Errores', value: nErrors, color: 'text-red-400' },
              {
                label: 'ID de Lote',
                value: batchMeta?.batch_id.slice(0, 8) + '…',
                color: 'text-gray-400',
              },
            ].map(({ label, value, color }) => (
              <Card key={label}>
                <div className="text-xs text-gray-500 mb-1">{label}</div>
                <div className={`text-xl font-bold font-mono ${color}`}>{value}</div>
              </Card>
            ))}
          </div>

          {/* Distribution chart */}
          {histogramData.length > 1 && (
            <Card title="Distribución de Valores Predichos">
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={histogramData} margin={{ top: 4, right: 8, left: -8, bottom: 4 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e3a5f" />
                  <XAxis dataKey="bin" tick={{ fill: '#9ca3af', fontSize: 10 }} />
                  <YAxis tick={{ fill: '#9ca3af', fontSize: 11 }} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{
                      background: '#0f2744',
                      border: '1px solid #1e3a5f',
                      borderRadius: 8,
                    }}
                    labelStyle={{ color: '#e2e8f0' }}
                    itemStyle={{ color: '#06b6d4' }}
                    formatter={(v: number) => [v, 'Materiales']}
                    labelFormatter={(l) => `≈ ${l}`}
                  />
                  {targetProperty === 'energy_above_hull' && (
                    <ReferenceLine
                      x="0.050"
                      stroke="#f59e0b"
                      strokeDasharray="4 2"
                      label={{ value: 'Umbral de estabilidad', fill: '#f59e0b', fontSize: 10 }}
                    />
                  )}
                  <Bar dataKey="count" radius={[3, 3, 0, 0]}>
                    {histogramData.map((_, i) => (
                      <Cell key={i} fill="#06b6d4" fillOpacity={0.85} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
              {targetProperty === 'energy_above_hull' && (
                <p className="text-xs text-amber-400/80 mt-2">
                  Línea punteada en 0.05 eV/átomo — los materiales por debajo de este umbral se
                  consideran termodinámicamente estables. Este es un criterio de cribado, no una
                  prueba de sintetizabilidad.
                </p>
              )}
            </Card>
          )}

          {/* Results table */}
          <Card title={`Resultados — ${results.length} materiales`}>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-navy-600">
                    <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Fórmula</th>
                    <th className="text-right py-3 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Valor Predicho</th>
                    <th className="text-right py-3 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Confianza</th>
                    <th className="text-center py-3 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Dominio</th>
                    <th className="text-center py-3 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Explicar</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-navy-700">
                  {results.map((r) => (
                    <tr
                      key={r.material_id}
                      className={`hover:bg-navy-700/40 transition-colors ${r.error ? 'opacity-50' : ''}`}
                    >
                      <td className="py-2.5 px-4 font-mono text-cyan-400">
                        <div className="flex items-center gap-1.5">
                          {formulaMap[r.material_id] ?? r.material_id.slice(0, 8)}
                          <button
                            onClick={() => navigate(`/materials/${r.material_id}`)}
                            className="text-gray-500 hover:text-cyan-400 transition-colors"
                            title="Ver detalle del material"
                          >
                            <ExternalLink size={11} />
                          </button>
                        </div>
                      </td>
                      <td className="py-2.5 px-4 text-right font-mono text-gray-200">
                        {r.error ? (
                          <span className="text-red-400 text-xs">{r.error}</span>
                        ) : r.predicted_class !== null ? (
                          <span className={`px-2 py-0.5 rounded text-xs font-medium ${r.predicted_class === '1' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'}`}>
                            {r.predicted_class === '1' ? 'Estable' : 'Inestable'}
                          </span>
                        ) : r.predicted_value !== null ? (
                          r.predicted_value.toFixed(4)
                        ) : '—'}
                      </td>
                      <td className="py-2.5 px-4 text-right text-gray-400 text-xs font-mono">
                        {r.confidence_score !== null
                          ? `${(r.confidence_score * 100).toFixed(1)}%`
                          : <span className="text-gray-600">—</span>}
                      </td>
                      <td className="py-2.5 px-4 text-center">
                        {!r.error && <OODBadge ood={r.is_out_of_domain} />}
                      </td>
                      <td className="py-2.5 px-4 text-center">
                        {!r.error && (
                          <button
                            onClick={() => handleExplain(r)}
                            className="inline-flex items-center gap-1 px-2 py-1 text-xs text-purple-400 hover:text-purple-300 hover:bg-purple-500/10 rounded transition-colors"
                            title="Explicar esta predicción con SHAP"
                          >
                            <Sparkles size={10} /> ¿Por qué?
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {nOod > 0 && (
              <div className="mt-4 p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg text-xs text-amber-400">
                <strong>{nOod}</strong> material
                {nOod !== 1 ? 'es están' : ' está'} fuera del dominio de entrenamiento del modelo. Las predicciones tienen mayor incertidumbre.
              </div>
            )}
          </Card>

          {/* Pareto Analysis */}
          {paretoPoints.length > 1 && (
            <Card title="Frontera de Pareto — Materiales Candidatos Principales">
              <ParetoPlot points={paretoPoints} />
            </Card>
          )}

          {/* SHAP explanation modal */}
          <Modal open={shapOpen} onClose={() => setShapOpen(false)} title="Explicación de la Predicción (SHAP)" size="lg">
            {shapLoading ? (
              <LoadingSpinner />
            ) : shapError ? (
              <div className="text-red-400 text-sm text-center py-8">{shapError}</div>
            ) : shapData ? (
              <>
                <ShapWaterfallChart
                  formula={shapData.formula}
                  targetProperty={shapData.target_property}
                  baseValue={shapData.base_value}
                  predictedValue={shapData.predicted_value}
                  contributions={shapData.feature_contributions}
                />
                <ShapNarrative
                  data={generateShapNarrative(
                    shapData.formula,
                    shapData.target_property,
                    shapData.predicted_value,
                    shapData.base_value,
                    shapData.feature_contributions,
                  )}
                />
              </>
            ) : null}
          </Modal>
        </>
      )}

      {/* Empty state — no results yet */}
      {!results && !loading && !error && (
        <Card>
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <div className="p-4 bg-cyan-500/10 rounded-2xl mb-5">
              <Zap size={36} className="text-cyan-400" />
            </div>
            <h3 className="text-base font-semibold text-white mb-2">
              Configura y ejecuta predicciones arriba
            </h3>
            <p className="text-sm text-gray-500 max-w-md">
              Selecciona un dataset y una propiedad objetivo, opcionalmente elige un modelo alternativo,
              luego haz clic en Ejecutar Predicciones. La detección de fuera de dominio y las
              estimaciones de incertidumbre se reportan para cada material.
            </p>
          </div>
        </Card>
      )}
    </div>
  );
}
