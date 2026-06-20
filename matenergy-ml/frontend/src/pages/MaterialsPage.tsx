import { useEffect, useState, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Atom, Search, ChevronLeft, ChevronRight, Table2, Waypoints } from 'lucide-react';
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
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { EmptyState } from '../components/ui/EmptyState';
import { ConvexHullPlot, HullPoint } from '../components/charts/ConvexHullPlot';
import { StabilityGauge } from '../components/charts/StabilityGauge';
import { listMaterials, getHullData } from '../api/materials';
import { listDatasets } from '../api/datasets';
import { Material, Dataset } from '../types';

type ViewMode = 'table' | 'hull' | 'cards';

const PAGE_SIZE = 20;

export function MaterialsPage() {
  const [materials, setMaterials] = useState<Material[]>([]);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [selectedDataset, setSelectedDataset] = useState('');
  const [page, setPage] = useState(0);
  const [viewMode, setViewMode] = useState<ViewMode>('table');
  const [hullPoints, setHullPoints] = useState<HullPoint[]>([]);
  const [hullLoading, setHullLoading] = useState(false);
  const navigate = useNavigate();

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(search), 350);
    return () => clearTimeout(timer);
  }, [search]);

  useEffect(() => {
    listDatasets()
      .then((r) => setDatasets(r.data))
      .catch(() => setDatasets([]));
  }, []);

  const fetchMaterials = useCallback(() => {
    setLoading(true);
    listMaterials({
      dataset_id: selectedDataset || undefined,
      skip: page * PAGE_SIZE,
      limit: PAGE_SIZE,
    })
      .then((r) => setMaterials(r.data))
      .catch(() => setMaterials([]))
      .finally(() => setLoading(false));
  }, [selectedDataset, page]);

  useEffect(() => {
    setPage(0);
  }, [selectedDataset, debouncedSearch]);

  useEffect(() => {
    fetchMaterials();
  }, [fetchMaterials]);

  const filtered = debouncedSearch
    ? materials.filter(
        (m) =>
          m.formula.toLowerCase().includes(debouncedSearch.toLowerCase()) ||
          (m.reduced_formula &&
            m.reduced_formula.toLowerCase().includes(debouncedSearch.toLowerCase())) ||
          (m.chemsys && m.chemsys.toLowerCase().includes(debouncedSearch.toLowerCase()))
      )
    : materials;

  // Chemical system distribution from current page
  const chemsysData = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const m of materials) {
      const key = m.chemsys ?? 'Unknown';
      counts[key] = (counts[key] ?? 0) + 1;
    }
    return Object.entries(counts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 12)
      .map(([name, count]) => ({ name, count }));
  }, [materials]);

  const CHART_COLORS = [
    '#06b6d4', '#3b82f6', '#8b5cf6', '#10b981',
    '#f59e0b', '#ef4444', '#ec4899', '#14b8a6',
    '#f97316', '#84cc16', '#6366f1', '#a78bfa',
  ];

  const hullMap = useMemo(
    () => Object.fromEntries(hullPoints.map((p) => [p.material_id, p])),
    [hullPoints]
  );

  const handleViewMode = (mode: ViewMode) => {
    setViewMode(mode);
    if ((mode === 'hull' || mode === 'cards') && hullPoints.length === 0 && selectedDataset) {
      setHullLoading(true);
      getHullData(selectedDataset)
        .then((r) => setHullPoints(r.data.points))
        .catch(() => setHullPoints([]))
        .finally(() => setHullLoading(false));
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Materiales</h1>
        <p className="text-gray-400 text-sm mt-1">
          Explore las composiciones de materiales en sus datasets
        </p>
      </div>

      {chemsysData.length > 0 && (
        <Card title="Distribución de Sistemas Químicos">
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={chemsysData} margin={{ top: 4, right: 8, left: -16, bottom: 40 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e3a5f" />
              <XAxis
                dataKey="name"
                tick={{ fill: '#9ca3af', fontSize: 11 }}
                angle={-35}
                textAnchor="end"
                interval={0}
              />
              <YAxis tick={{ fill: '#9ca3af', fontSize: 11 }} allowDecimals={false} />
              <Tooltip
                contentStyle={{ background: '#0f2744', border: '1px solid #1e3a5f', borderRadius: 8 }}
                labelStyle={{ color: '#e2e8f0' }}
                itemStyle={{ color: '#06b6d4' }}
              />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {chemsysData.map((_, i) => (
                  <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>
      )}

      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-64">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar por fórmula, fórmula reducida o sistema químico..."
            className="w-full bg-navy-700 border border-navy-500 rounded-lg pl-9 pr-4 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-cyan-400 transition-colors"
          />
        </div>
        <select
          value={selectedDataset}
          onChange={(e) => { setSelectedDataset(e.target.value); setHullPoints([]); }}
          className="bg-navy-700 border border-navy-500 rounded-lg px-4 py-2.5 text-sm text-gray-300 focus:outline-none focus:border-cyan-400 transition-colors"
        >
          <option value="">Todos los Datasets</option>
          {datasets.map((ds) => (
            <option key={ds.id} value={ds.id}>{ds.name}</option>
          ))}
        </select>

        {/* View mode toggle */}
        <div className="flex gap-1 bg-navy-700 rounded-lg p-1">
          {([
            { id: 'table' as ViewMode, icon: <Table2 size={14} />, label: 'Tabla' },
            { id: 'hull' as ViewMode, icon: <Waypoints size={14} />, label: 'Casco Convexo' },
            { id: 'cards' as ViewMode, icon: <Atom size={14} />, label: 'Tarjetas' },
          ]).map((v) => (
            <button
              key={v.id}
              onClick={() => handleViewMode(v.id)}
              disabled={v.id !== 'table' && !selectedDataset}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors disabled:opacity-30 ${
                viewMode === v.id ? 'bg-cyan-500 text-navy-900' : 'text-gray-400 hover:text-white'
              }`}
              title={v.id !== 'table' && !selectedDataset ? 'Seleccione primero un dataset' : undefined}
            >
              {v.icon} {v.label}
            </button>
          ))}
        </div>
      </div>

      {/* Convex Hull View */}
      {viewMode === 'hull' && (
        <Card title="Casco Convexo — Panorama de Estabilidad Termodinámica">
          {hullLoading ? (
            <LoadingSpinner />
          ) : hullPoints.length === 0 ? (
            <EmptyState
              title="Sin datos de casco convexo"
              description="Seleccione un dataset y asegúrese de que se hayan importado las propiedades energy_above_hull y formation_energy_per_atom."
            />
          ) : (
            <ConvexHullPlot points={hullPoints} />
          )}
        </Card>
      )}

      {/* Cards View */}
      {viewMode === 'cards' && (
        <div>
          {loading || hullLoading ? (
            <LoadingSpinner />
          ) : filtered.length === 0 ? (
            <EmptyState icon={<Atom size={48} />} title="No se encontraron materiales" description="" />
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
              {filtered.map((m, idx) => {
                const hull = hullMap[m.id];
                const eah = hull?.energy_above_hull ?? null;
                const stabilityColor =
                  eah === null ? 'text-gray-500'
                    : eah <= 0.05 ? 'text-emerald-400'
                    : eah <= 0.10 ? 'text-amber-400'
                    : 'text-red-400';
                const stabilityLabel =
                  eah === null ? 'desconocido'
                    : eah <= 0.05 ? 'estable'
                    : eah <= 0.10 ? 'metaestable'
                    : 'inestable';
                return (
                  <div
                    key={m.id}
                    onClick={() => navigate(`/materials/${m.id}`)}
                    className="bg-navy-800 border border-navy-600 rounded-xl p-4 cursor-pointer hover:border-cyan-500/50 transition-all hover:shadow-lg hover:shadow-cyan-500/5"
                    style={{
                      opacity: 0,
                      animation: `fadeInUp 0.4s ease-out ${idx * 30}ms forwards`,
                    }}
                  >
                    <div className="font-mono text-cyan-400 font-bold truncate">{m.formula}</div>
                    <div className="text-xs text-gray-500 mt-0.5">{m.chemsys ?? '—'}</div>
                    {eah !== null && (
                      <div className="mt-2">
                        <StabilityGauge energyAboveHull={eah} size={40} />
                        <div className={`text-xs font-medium mt-1 ${stabilityColor}`}>
                          {stabilityLabel} · {eah.toFixed(3)} eV/at
                        </div>
                      </div>
                    )}
                    <div className="flex flex-wrap gap-1 mt-2">
                      {m.elements?.slice(0, 4).map((el) => (
                        <span key={el} className="px-1.5 py-0.5 bg-navy-600 text-gray-400 rounded text-xs font-mono">{el}</span>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Table View */}
      {viewMode === 'table' && (
        <Card>
          {loading ? (
            <LoadingSpinner />
          ) : filtered.length === 0 ? (
            <EmptyState
              icon={<Atom size={48} />}
              title="No se encontraron materiales"
              description={
                debouncedSearch
                  ? `Ningún material coincide con "${debouncedSearch}". Intente con otra fórmula.`
                  : 'Suba un dataset para comenzar a explorar materiales.'
              }
            />
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-navy-600">
                      <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Fórmula</th>
                      <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Fórmula Reducida</th>
                      <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Sistema Químico</th>
                      <th className="text-center py-3 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider"># Elementos</th>
                      <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Elementos</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-navy-700">
                    {filtered.map((m) => (
                      <tr
                        key={m.id}
                        onClick={() => navigate(`/materials/${m.id}`)}
                        className="hover:bg-navy-700/50 cursor-pointer transition-colors"
                      >
                        <td className="py-3 px-4">
                          <span className="font-mono font-medium text-cyan-400">{m.formula}</span>
                        </td>
                        <td className="py-3 px-4 font-mono text-gray-300">{m.reduced_formula ?? '—'}</td>
                        <td className="py-3 px-4 text-gray-400">{m.chemsys ?? '—'}</td>
                        <td className="py-3 px-4 text-center text-gray-300">{m.nelements ?? '—'}</td>
                        <td className="py-3 px-4">
                          <div className="flex flex-wrap gap-1">
                            {m.elements?.map((el) => (
                              <span key={el} className="px-1.5 py-0.5 bg-navy-600 text-gray-300 rounded text-xs font-mono">{el}</span>
                            )) ?? <span className="text-gray-500">—</span>}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="flex items-center justify-between pt-4 border-t border-navy-700 mt-4">
                <span className="text-xs text-gray-500">
                  Página {page + 1} — mostrando {filtered.length} materiales
                </span>
                <div className="flex items-center gap-2">
                  <button
                    disabled={page === 0}
                    onClick={() => setPage((p) => p - 1)}
                    className="p-1.5 rounded text-gray-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed hover:bg-navy-600 transition-colors"
                  >
                    <ChevronLeft size={16} />
                  </button>
                  <button
                    disabled={materials.length < PAGE_SIZE}
                    onClick={() => setPage((p) => p + 1)}
                    className="p-1.5 rounded text-gray-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed hover:bg-navy-600 transition-colors"
                  >
                    <ChevronRight size={16} />
                  </button>
                </div>
              </div>
            </>
          )}
        </Card>
      )}
    </div>
  );
}
