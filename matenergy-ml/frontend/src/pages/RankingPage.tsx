import { useEffect, useState, FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { Trophy, Plus, AlertCircle, ChevronDown, ExternalLink } from 'lucide-react';
import { Card } from '../components/ui/Card';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { EmptyState } from '../components/ui/EmptyState';
import { Modal } from '../components/ui/Modal';
import { listRankings, getRankingItems, createRanking } from '../api/rankings';
import { listDatasets } from '../api/datasets';
import { CandidateRanking, RankingItem, Dataset } from '../types';

type PriorityLabel = 'high' | 'moderate' | 'low';

const priorityClasses: Record<string, string> = {
  high: 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30',
  moderate: 'bg-blue-500/20 text-blue-400 border border-blue-500/30',
  low: 'bg-gray-500/20 text-gray-400 border border-gray-500/30',
};

// Display-only Spanish labels for the priority_label enum values (kept in English for lookups)
const PRIORITY_LABELS_ES: Record<string, string> = {
  high: 'Alta',
  moderate: 'Moderada',
  low: 'Baja',
};

function getPriorityClass(label: string): string {
  const key = label.toLowerCase() as PriorityLabel;
  return priorityClasses[key] ?? priorityClasses['low'];
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

function truncate(str: string, max: number) {
  return str.length > max ? str.slice(0, max) + '…' : str;
}

export function RankingPage() {
  const navigate = useNavigate();
  const [rankings, setRankings] = useState<CandidateRanking[]>([]);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedRanking, setSelectedRanking] = useState<CandidateRanking | null>(null);
  const [items, setItems] = useState<RankingItem[]>([]);
  const [itemsLoading, setItemsLoading] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [expandedReason, setExpandedReason] = useState<string | null>(null);

  // Create form
  const [form, setForm] = useState({
    name: '',
    application_target: '',
    dataset_id: '',
  });
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState('');

  const fetchRankings = () => {
    setLoading(true);
    listRankings()
      .then((r) => setRankings(r.data))
      .catch(() => setRankings([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchRankings();
    listDatasets().then((r) => setDatasets(r.data)).catch(() => setDatasets([]));
  }, []);

  const handleSelectRanking = async (ranking: CandidateRanking) => {
    setSelectedRanking(ranking);
    setItemsLoading(true);
    setItems([]);
    try {
      const r = await getRankingItems(ranking.id);
      setItems(r.data.items ?? []);
    } catch {
      setItems([]);
    } finally {
      setItemsLoading(false);
    }
  };

  const handleCreate = async (e: FormEvent) => {
    e.preventDefault();
    setCreateError('');
    setCreating(true);
    try {
      await createRanking({
        name: form.name,
        application_target: form.application_target,
        dataset_id: form.dataset_id,
      });
      setCreateOpen(false);
      setForm({ name: '', application_target: '', dataset_id: '' });
      fetchRankings();
    } catch (err: unknown) {
      const msg =
        err && typeof err === 'object' && 'response' in err
          ? (err as { response?: { data?: { message?: string } } }).response?.data?.message
          : undefined;
      setCreateError(msg || 'No se pudo crear el ranking. Inténtalo de nuevo.');
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Ranking de Candidatos</h1>
          <p className="text-gray-400 text-sm mt-1">
            Prioriza materiales para síntesis y pruebas experimentales
          </p>
        </div>
        <button
          onClick={() => setCreateOpen(true)}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-navy-900 bg-cyan-500 hover:bg-cyan-400 rounded-lg transition-colors"
        >
          <Plus size={14} /> Crear Ranking
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Rankings list */}
        <div className="lg:col-span-1">
          <Card title="Rankings" subtitle={`${rankings.length} disponibles`}>
            {loading ? (
              <LoadingSpinner size="sm" />
            ) : rankings.length === 0 ? (
              <EmptyState
                icon={<Trophy size={32} />}
                title="Aún no hay rankings"
                description="Crea un ranking para priorizar candidatos."
              />
            ) : (
              <div className="space-y-2">
                {rankings.map((r) => (
                  <button
                    key={r.id}
                    onClick={() => handleSelectRanking(r)}
                    className={`w-full text-left p-3 rounded-lg border transition-all ${
                      selectedRanking?.id === r.id
                        ? 'bg-cyan-500/10 border-cyan-500/30 text-white'
                        : 'bg-navy-700 border-navy-500 text-gray-300 hover:border-navy-400 hover:text-white'
                    }`}
                  >
                    <div className="font-medium text-sm">{r.name}</div>
                    <div className="text-xs text-gray-500 mt-0.5">{r.application_target}</div>
                    <div className="flex items-center justify-between mt-2">
                      <span className="text-xs text-gray-600">{formatDate(r.created_at)}</span>
                      {r.n_candidates != null && (
                        <span className="text-xs bg-navy-600 text-gray-400 px-1.5 py-0.5 rounded">
                          {r.n_candidates} candidatos
                        </span>
                      )}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </Card>
        </div>

        {/* Ranking items */}
        <div className="lg:col-span-2">
          {!selectedRanking ? (
            <Card>
              <EmptyState
                icon={<Trophy size={48} />}
                title="Selecciona un ranking"
                description="Haz clic en un ranking de la lista para ver sus candidatos priorizados."
              />
            </Card>
          ) : (
            <Card
              title={selectedRanking.name}
              subtitle={`Objetivo: ${selectedRanking.application_target}`}
              badge={
                selectedRanking.n_candidates != null
                  ? `${selectedRanking.n_candidates} candidatos`
                  : undefined
              }
            >
              {itemsLoading ? (
                <LoadingSpinner />
              ) : items.length === 0 ? (
                <EmptyState
                  title="Sin candidatos"
                  description="Este ranking aún no tiene elementos."
                />
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-navy-600">
                        <th className="text-center py-2 px-3 text-xs font-semibold text-gray-500 uppercase tracking-wider w-12">
                          Rango
                        </th>
                        <th className="text-left py-2 px-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                          ID de Material
                        </th>
                        <th className="text-right py-2 px-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                          Puntaje
                        </th>
                        <th className="text-center py-2 px-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                          Prioridad
                        </th>
                        <th className="text-right py-2 px-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                          Estabilidad
                        </th>
                        <th className="text-left py-2 px-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                          Razonamiento
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-navy-700">
                      {items.map((item) => (
                        <tr
                          key={item.material_id}
                          className="hover:bg-navy-700/30 transition-colors"
                        >
                          <td className="py-2.5 px-3 text-center">
                            <span
                              className={`inline-flex items-center justify-center w-7 h-7 rounded-full text-xs font-bold ${
                                item.rank_position === 1
                                  ? 'bg-yellow-500/20 text-yellow-400'
                                  : item.rank_position === 2
                                  ? 'bg-gray-400/20 text-gray-300'
                                  : item.rank_position === 3
                                  ? 'bg-amber-700/20 text-amber-600'
                                  : 'bg-navy-600 text-gray-400'
                              }`}
                            >
                              {item.rank_position}
                            </span>
                          </td>
                          <td className="py-2.5 px-3 font-mono text-xs text-gray-300">
                            <div className="flex items-center gap-1.5">
                              {truncate(item.material_id, 16)}
                              <button
                                onClick={() => navigate(`/materials/${item.material_id}`)}
                                className="text-gray-600 hover:text-cyan-400 transition-colors"
                                title="Ver detalle del material"
                              >
                                <ExternalLink size={11} />
                              </button>
                            </div>
                          </td>
                          <td className="py-2.5 px-3 text-right font-mono text-cyan-400 font-medium">
                            {item.candidate_score.toFixed(4)}
                          </td>
                          <td className="py-2.5 px-3 text-center">
                            <span
                              className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${getPriorityClass(
                                item.priority_label
                              )}`}
                            >
                              {PRIORITY_LABELS_ES[item.priority_label.toLowerCase()] ?? item.priority_label}
                            </span>
                          </td>
                          <td className="py-2.5 px-3 text-right text-gray-300 font-mono text-xs">
                            {item.stability_score != null
                              ? item.stability_score.toFixed(3)
                              : '—'}
                          </td>
                          <td className="py-2.5 px-3">
                            {item.reasoning_summary ? (
                              <div className="flex items-start gap-1">
                                <span className="text-xs text-gray-400 leading-relaxed">
                                  {expandedReason === item.material_id
                                    ? item.reasoning_summary
                                    : truncate(item.reasoning_summary, 60)}
                                </span>
                                {item.reasoning_summary.length > 60 && (
                                  <button
                                    onClick={() =>
                                      setExpandedReason(
                                        expandedReason === item.material_id
                                          ? null
                                          : item.material_id
                                      )
                                    }
                                    className="flex-shrink-0 mt-0.5 text-cyan-400 hover:text-cyan-300 transition-colors"
                                  >
                                    <ChevronDown
                                      size={12}
                                      className={`transition-transform ${
                                        expandedReason === item.material_id ? 'rotate-180' : ''
                                      }`}
                                    />
                                  </button>
                                )}
                              </div>
                            ) : (
                              <span className="text-gray-600 text-xs">—</span>
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
        </div>
      </div>

      {/* Create Ranking Modal */}
      <Modal
        open={createOpen}
        onClose={() => {
          setCreateOpen(false);
          setCreateError('');
        }}
        title="Crear Ranking de Candidatos"
      >
        <form onSubmit={handleCreate} className="space-y-4">
          <div>
            <label className="block text-sm text-gray-400 mb-2">
              Nombre del Ranking <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              required
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              placeholder="ej. Cribado de cátodos de alta capacidad Q1"
              className="w-full bg-navy-700 border border-navy-500 rounded-lg px-4 py-2.5 text-white placeholder-gray-500 focus:outline-none focus:border-cyan-400 transition-colors"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-2">
              Objetivo de Aplicación <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              required
              value={form.application_target}
              onChange={(e) => setForm((f) => ({ ...f, application_target: e.target.value }))}
              placeholder="ej. cátodo de batería de Li-ion, electrolito sólido"
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
          {createError && (
            <div className="flex items-start gap-2 bg-red-500/10 border border-red-500/30 text-red-400 text-sm px-4 py-3 rounded-lg">
              <AlertCircle size={16} className="mt-0.5 flex-shrink-0" />
              {createError}
            </div>
          )}
          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={() => setCreateOpen(false)}
              className="flex-1 py-2.5 text-sm text-gray-400 hover:text-white bg-navy-700 hover:bg-navy-600 border border-navy-500 rounded-lg transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={creating}
              className="flex-1 py-2.5 text-sm font-medium text-navy-900 bg-cyan-500 hover:bg-cyan-400 disabled:opacity-50 rounded-lg transition-colors"
            >
              {creating ? 'Creando...' : 'Crear Ranking'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
