import { useEffect, useState, FormEvent } from 'react';
import { Brain, Plus, Play, AlertCircle, CheckCircle2, BarChart2, ScatterChart } from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { EmptyState } from '../components/ui/EmptyState';
import { Modal } from '../components/ui/Modal';
import { FeatureImportanceChart } from '../components/charts/FeatureImportanceChart';
import { ParityPlot } from '../components/charts/ParityPlot';
import { listModels, getModelMetrics, getFeatureImportance, getParityData, trainModel, activateModel } from '../api/models';
import { listDatasets } from '../api/datasets';
import { listDescriptorSets } from '../api/descriptors';
import { ModelVersion, ModelMetric, Dataset, DescriptorSet } from '../types';

type MetricsTab = 'metrics' | 'importance' | 'parity';

const MODEL_TYPES = ['random_forest', 'gradient_boosting', 'neural_network', 'xgboost', 'svr'];
const TASK_TYPES = ['regression', 'classification'];

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

export function ModelsPage() {
  const [models, setModels] = useState<ModelVersion[]>([]);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [descriptors, setDescriptors] = useState<DescriptorSet[]>([]);
  const [loading, setLoading] = useState(true);
  const [trainOpen, setTrainOpen] = useState(false);
  const [metricsOpen, setMetricsOpen] = useState(false);
  const [selectedMetrics, setSelectedMetrics] = useState<ModelMetric[]>([]);
  const [metricsLoading, setMetricsLoading] = useState(false);
  const [selectedModelName, setSelectedModelName] = useState('');
  const [selectedModelId, setSelectedModelId] = useState('');
  const [metricsTab, setMetricsTab] = useState<MetricsTab>('metrics');
  const [featureImportance, setFeatureImportance] = useState<{ feature: string; importance: number }[]>([]);
  const [fiLoading, setFiLoading] = useState(false);
  const [parityData, setParityData] = useState<{ y_test: number[]; y_pred: number[]; mae: number; r2: number; target_property: string } | null>(null);
  const [parityLoading, setParityLoading] = useState(false);
  const [parityError, setParityError] = useState('');

  // Train form
  const [form, setForm] = useState({
    name: '',
    model_type: 'random_forest',
    task_type: 'regression',
    target_property: '',
    dataset_id: '',
    descriptor_set_id: '',
  });
  const [training, setTraining] = useState(false);
  const [trainError, setTrainError] = useState('');
  const [trainSuccess, setTrainSuccess] = useState(false);

  const fetchModels = () => {
    setLoading(true);
    listModels()
      .then((r) => setModels(r.data))
      .catch(() => setModels([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchModels();
    listDatasets().then((r) => setDatasets(r.data)).catch(() => setDatasets([]));
    listDescriptorSets().then((r) => setDescriptors(r.data)).catch(() => setDescriptors([]));
  }, []);

  const handleTrain = async (e: FormEvent) => {
    e.preventDefault();
    setTrainError('');
    setTrainSuccess(false);
    setTraining(true);
    try {
      await trainModel({
        model_type: form.model_type,
        task_type: form.task_type,
        target_property: form.target_property,
        dataset_id: form.dataset_id,
        descriptor_set_id: form.descriptor_set_id,
        name: form.name || undefined,
      });
      setTrainSuccess(true);
      fetchModels();
      setTimeout(() => {
        setTrainOpen(false);
        setTrainSuccess(false);
        setForm({
          name: '',
          model_type: 'random_forest',
          task_type: 'regression',
          target_property: '',
          dataset_id: '',
          descriptor_set_id: '',
        });
      }, 1500);
    } catch (err: unknown) {
      const msg =
        err && typeof err === 'object' && 'response' in err
          ? (err as { response?: { data?: { message?: string } } }).response?.data?.message
          : undefined;
      setTrainError(msg || 'La solicitud de entrenamiento falló. Inténtalo de nuevo.');
    } finally {
      setTraining(false);
    }
  };

  const handleViewMetrics = async (model: ModelVersion) => {
    setSelectedModelName(model.name);
    setSelectedModelId(model.id);
    setMetricsLoading(true);
    setMetricsOpen(true);
    setSelectedMetrics([]);
    setFeatureImportance([]);
    setParityData(null);
    setParityError('');
    setMetricsTab('metrics');
    try {
      const r = await getModelMetrics(model.id);
      setSelectedMetrics(r.data);
    } catch {
      setSelectedMetrics([]);
    } finally {
      setMetricsLoading(false);
    }
  };

  const loadFeatureImportance = async () => {
    if (!selectedModelId || featureImportance.length > 0) return;
    setFiLoading(true);
    try {
      const r = await getFeatureImportance(selectedModelId, 20);
      setFeatureImportance(r.data);
    } catch {
      setFeatureImportance([]);
    } finally {
      setFiLoading(false);
    }
  };

  const loadParityData = async () => {
    if (!selectedModelId || parityData) return;
    setParityLoading(true);
    setParityError('');
    try {
      const r = await getParityData(selectedModelId);
      setParityData(r.data);
    } catch {
      setParityError('Datos de paridad no disponibles. Reentrena el modelo para generarlos.');
    } finally {
      setParityLoading(false);
    }
  };

  const handleMetricsTab = (tab: MetricsTab) => {
    setMetricsTab(tab);
    if (tab === 'importance') loadFeatureImportance();
    if (tab === 'parity') loadParityData();
  };

  const handleActivate = async (modelId: string) => {
    try {
      await activateModel(modelId);
      fetchModels();
    } catch {
      // silent — ideally show a toast
    }
  };

  // Group metrics by split
  const metricsBySplit = selectedMetrics.reduce<Record<string, ModelMetric[]>>((acc, m) => {
    if (!acc[m.split]) acc[m.split] = [];
    acc[m.split].push(m);
    return acc;
  }, {});

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Modelos</h1>
          <p className="text-gray-400 text-sm mt-1">
            Entrena y gestiona modelos de aprendizaje automático para predicción de propiedades
          </p>
        </div>
        <button
          onClick={() => setTrainOpen(true)}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-navy-900 bg-cyan-500 hover:bg-cyan-400 rounded-lg transition-colors"
        >
          <Plus size={14} /> Entrenar Modelo Nuevo
        </button>
      </div>

      <Card>
        {loading ? (
          <LoadingSpinner />
        ) : models.length === 0 ? (
          <EmptyState
            icon={<Brain size={48} />}
            title="Aún no hay modelos entrenados"
            description="Entrena tu primer modelo seleccionando un dataset, un conjunto de descriptores y una propiedad objetivo."
            action={
              <button
                onClick={() => setTrainOpen(true)}
                className="px-4 py-2 bg-cyan-500 hover:bg-cyan-400 text-navy-900 text-sm font-medium rounded-lg"
              >
                Entrenar un modelo
              </button>
            }
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-navy-600">
                  <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    Nombre
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    Tipo
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    Tarea
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    Propiedad Objetivo
                  </th>
                  <th className="text-center py-3 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    Estado
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    Creado
                  </th>
                  <th className="text-center py-3 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    Acciones
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-navy-700">
                {models.map((m) => (
                  <tr key={m.id} className="hover:bg-navy-700/50 transition-colors">
                    <td className="py-3 px-4">
                      <div className="font-medium text-white">{m.name}</div>
                      {m.version_tag && (
                        <div className="text-xs text-gray-500 mt-0.5">{m.version_tag}</div>
                      )}
                    </td>
                    <td className="py-3 px-4 text-gray-300 font-mono text-xs">
                      {m.model_type}
                    </td>
                    <td className="py-3 px-4">
                      <Badge
                        label={m.task_type}
                        variant={m.task_type === 'regression' ? 'moderate' : 'high'}
                      />
                    </td>
                    <td className="py-3 px-4 text-gray-300">{m.target_property}</td>
                    <td className="py-3 px-4 text-center">
                      {m.is_active ? (
                        <Badge label="Activo" variant="valid" />
                      ) : (
                        <Badge label="Inactivo" variant="default" />
                      )}
                    </td>
                    <td className="py-3 px-4 text-gray-500 text-xs">
                      {formatDate(m.created_at)}
                    </td>
                    <td className="py-3 px-4 text-center">
                      <div className="flex items-center justify-center gap-2">
                        <button
                          onClick={() => handleViewMetrics(m)}
                          className="px-2 py-1 text-xs text-cyan-400 hover:text-cyan-300 hover:bg-cyan-500/10 rounded transition-colors"
                        >
                          Métricas
                        </button>
                        {!m.is_active && (
                          <button
                            onClick={() => handleActivate(m.id)}
                            className="px-2 py-1 text-xs text-green-400 hover:text-green-300 hover:bg-green-500/10 rounded transition-colors flex items-center gap-1"
                          >
                            <Play size={10} /> Activar
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Train Model Modal */}
      <Modal
        open={trainOpen}
        onClose={() => {
          setTrainOpen(false);
          setTrainError('');
          setTrainSuccess(false);
        }}
        title="Entrenar Modelo Nuevo"
        size="lg"
      >
        {trainSuccess ? (
          <div className="flex flex-col items-center py-8 gap-3">
            <CheckCircle2 size={48} className="text-green-400" />
            <p className="text-white font-medium">¡Trabajo de entrenamiento enviado con éxito!</p>
            <p className="text-gray-400 text-sm">El modelo aparecerá en la lista una vez que finalice el entrenamiento.</p>
          </div>
        ) : (
          <form onSubmit={handleTrain} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <label className="block text-sm text-gray-400 mb-2">Nombre del Modelo (opcional)</label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                  placeholder="ej. RF Bandgap v1"
                  className="w-full bg-navy-700 border border-navy-500 rounded-lg px-4 py-2.5 text-white placeholder-gray-500 focus:outline-none focus:border-cyan-400 transition-colors"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-2">
                  Tipo de Modelo <span className="text-red-400">*</span>
                </label>
                <select
                  required
                  value={form.model_type}
                  onChange={(e) => setForm((f) => ({ ...f, model_type: e.target.value }))}
                  className="w-full bg-navy-700 border border-navy-500 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-cyan-400 transition-colors"
                >
                  {MODEL_TYPES.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-2">
                  Tipo de Tarea <span className="text-red-400">*</span>
                </label>
                <select
                  required
                  value={form.task_type}
                  onChange={(e) => setForm((f) => ({ ...f, task_type: e.target.value }))}
                  className="w-full bg-navy-700 border border-navy-500 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-cyan-400 transition-colors"
                >
                  {TASK_TYPES.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
              </div>
              <div className="col-span-2">
                <label className="block text-sm text-gray-400 mb-2">
                  Propiedad Objetivo <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={form.target_property}
                  onChange={(e) => setForm((f) => ({ ...f, target_property: e.target.value }))}
                  placeholder="ej. band_gap, formation_energy, stability"
                  className="w-full bg-navy-700 border border-navy-500 rounded-lg px-4 py-2.5 text-white placeholder-gray-500 focus:outline-none focus:border-cyan-400 transition-colors"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-2">
                  Dataset <span className="text-red-400">*</span>
                </label>
                <select
                  required
                  value={form.dataset_id}
                  onChange={(e) => setForm((f) => ({ ...f, dataset_id: e.target.value }))}
                  className="w-full bg-navy-700 border border-navy-500 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-cyan-400 transition-colors"
                >
                  <option value="">Selecciona un dataset...</option>
                  {datasets.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-2">
                  Conjunto de Descriptores <span className="text-red-400">*</span>
                </label>
                <select
                  required
                  value={form.descriptor_set_id}
                  onChange={(e) => setForm((f) => ({ ...f, descriptor_set_id: e.target.value }))}
                  className="w-full bg-navy-700 border border-navy-500 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-cyan-400 transition-colors"
                >
                  <option value="">Selecciona un conjunto de descriptores...</option>
                  {descriptors.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name} ({d.descriptor_type})
                    </option>
                  ))}
                </select>
              </div>
            </div>
            {trainError && (
              <div className="flex items-start gap-2 bg-red-500/10 border border-red-500/30 text-red-400 text-sm px-4 py-3 rounded-lg">
                <AlertCircle size={16} className="mt-0.5 flex-shrink-0" />
                {trainError}
              </div>
            )}
            <div className="flex gap-3 pt-2">
              <button
                type="button"
                onClick={() => setTrainOpen(false)}
                className="flex-1 py-2.5 text-sm text-gray-400 hover:text-white bg-navy-700 hover:bg-navy-600 border border-navy-500 rounded-lg transition-colors"
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={training}
                className="flex-1 py-2.5 text-sm font-medium text-navy-900 bg-cyan-500 hover:bg-cyan-400 disabled:opacity-50 rounded-lg transition-colors"
              >
                {training ? 'Enviando...' : 'Iniciar Entrenamiento'}
              </button>
            </div>
          </form>
        )}
      </Modal>

      {/* Metrics Modal */}
      <Modal
        open={metricsOpen}
        onClose={() => setMetricsOpen(false)}
        title={`Análisis — ${selectedModelName}`}
        size="lg"
      >
        {/* Tab bar */}
        <div className="flex gap-1 mb-5 bg-navy-700 rounded-lg p-1">
          {([
            { id: 'metrics' as MetricsTab, label: 'Métricas', icon: <BarChart2 size={13} /> },
            { id: 'importance' as MetricsTab, label: 'Importancia de Variables', icon: <BarChart2 size={13} /> },
            { id: 'parity' as MetricsTab, label: 'Gráfico de Paridad', icon: <ScatterChart size={13} /> },
          ] as const).map((tab) => (
            <button
              key={tab.id}
              onClick={() => handleMetricsTab(tab.id)}
              className={`flex items-center gap-1.5 flex-1 justify-center py-1.5 px-3 rounded-md text-xs font-medium transition-colors ${
                metricsTab === tab.id
                  ? 'bg-cyan-500 text-navy-900'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              {tab.icon} {tab.label}
            </button>
          ))}
        </div>

        {metricsTab === 'metrics' && (
          metricsLoading ? (
            <LoadingSpinner />
          ) : selectedMetrics.length === 0 ? (
            <EmptyState
              title="No hay métricas disponibles"
              description="Las métricas estarán disponibles una vez que el modelo termine de entrenarse."
            />
          ) : (
            <div className="space-y-6">
              {Object.entries(metricsBySplit).map(([split, metrics]) => (
                <div key={split}>
                  <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
                    División {split}
                  </h4>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                    {metrics.map((m) => (
                      <div key={m.metric_name} className="bg-navy-700 rounded-lg p-4 text-center">
                        <div className="text-xl font-bold font-mono text-cyan-400">
                          {m.metric_value.toFixed(4)}
                        </div>
                        <div className="text-xs text-gray-500 mt-1 uppercase">{m.metric_name}</div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
              {selectedMetrics.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
                    Comparación de Métricas por División
                  </h4>
                  <ResponsiveContainer width="100%" height={200}>
                    <BarChart
                      data={selectedMetrics.filter(m =>
                        ['mae', 'rmse', 'r2', 'accuracy', 'f1'].includes(m.metric_name)
                      )}
                      margin={{ top: 5, right: 10, left: 0, bottom: 20 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e3a5f" />
                      <XAxis dataKey="metric_name" tick={{ fill: '#94a3b8', fontSize: 11 }} angle={-30} textAnchor="end" />
                      <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} domain={[0, 'auto']} />
                      <Tooltip
                        contentStyle={{ background: '#1e3a5f', border: '1px solid #334155', borderRadius: '8px' }}
                        formatter={(val: number) => val.toFixed(4)}
                      />
                      <Bar dataKey="metric_value" radius={[4, 4, 0, 0]}>
                        {selectedMetrics.map((_, idx) => (
                          <Cell key={idx} fill={['#06b6d4', '#3b82f6', '#8b5cf6', '#10b981'][idx % 4]} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>
          )
        )}

        {metricsTab === 'importance' && (
          fiLoading ? (
            <LoadingSpinner />
          ) : featureImportance.length === 0 ? (
            <EmptyState
              title="No hay datos de importancia de variables"
              description="La importancia de variables está disponible para modelos Random Forest y Gradient Boosting. Reentrena el modelo para generarla."
            />
          ) : (
            <FeatureImportanceChart data={featureImportance} topN={15} />
          )
        )}

        {metricsTab === 'parity' && (
          parityLoading ? (
            <LoadingSpinner />
          ) : parityError ? (
            <EmptyState title="Datos de paridad no disponibles" description={parityError} />
          ) : parityData ? (
            <ParityPlot
              yTest={parityData.y_test}
              yPred={parityData.y_pred}
              mae={parityData.mae}
              r2={parityData.r2}
              targetProperty={parityData.target_property}
            />
          ) : (
            <EmptyState title="Selecciona la pestaña Gráfico de Paridad para cargar los datos" description="" />
          )
        )}
      </Modal>
    </div>
  );
}
