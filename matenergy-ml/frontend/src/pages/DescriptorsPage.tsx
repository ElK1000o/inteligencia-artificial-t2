import { useEffect, useState } from 'react';
import { FlaskConical, Plus, RefreshCw, Map } from 'lucide-react';
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
import { ChemicalSpaceMap, SpaceMapPoint } from '../components/charts/ChemicalSpaceMap';
import { listDescriptorSets, getSpaceMap } from '../api/descriptors';
import { DescriptorSet } from '../types';

type PageTab = 'sets' | 'space-map';

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('es-ES', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

export function DescriptorsPage() {
  const [descriptors, setDescriptors] = useState<DescriptorSet[]>([]);
  const [loading, setLoading] = useState(true);
  const [pageTab, setPageTab] = useState<PageTab>('sets');
  const [selectedSetForMap, setSelectedSetForMap] = useState('');
  const [colorProperty, setColorProperty] = useState('formation_energy_per_atom');
  const [spaceMapPoints, setSpaceMapPoints] = useState<SpaceMapPoint[]>([]);
  const [colorMin, setColorMin] = useState(0);
  const [colorMax, setColorMax] = useState(1);
  const [mapColorProp, setMapColorProp] = useState('');
  const [mapLoading, setMapLoading] = useState(false);
  const [mapError, setMapError] = useState('');

  const fetchDescriptors = () => {
    setLoading(true);
    listDescriptorSets()
      .then((r) => setDescriptors(r.data))
      .catch(() => setDescriptors([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchDescriptors();
  }, []);

  const handleLoadMap = () => {
    if (!selectedSetForMap) return;
    setMapLoading(true);
    setMapError('');
    setSpaceMapPoints([]);
    getSpaceMap(selectedSetForMap, { color_property: colorProperty })
      .then((r) => {
        setSpaceMapPoints(r.data.points);
        setColorMin(r.data.color_min);
        setColorMax(r.data.color_max);
        setMapColorProp(r.data.color_property);
      })
      .catch(() => setMapError('No se pudo calcular el mapa del espacio químico. Asegúrese de que existan vectores de descriptores.'))
      .finally(() => setMapLoading(false));
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Descriptores</h1>
          <p className="text-gray-400 text-sm mt-1">
            Conjuntos de características derivadas de composiciones de materiales para entrenamiento de ML
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={fetchDescriptors}
            className="flex items-center gap-2 px-3 py-2 text-sm text-gray-400 hover:text-white bg-navy-700 hover:bg-navy-600 border border-navy-500 rounded-lg transition-colors"
          >
            <RefreshCw size={14} /> Actualizar
          </button>
          <button
            disabled
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-navy-900 bg-cyan-500 opacity-60 cursor-not-allowed rounded-lg"
            title="Próximamente — use la API para generar descriptores"
          >
            <Plus size={14} /> Generar Descriptores
          </button>
        </div>
      </div>

      {/* Page tab switcher */}
      <div className="flex gap-1 bg-navy-800 border border-navy-600 rounded-xl p-1 w-fit">
        {([
          { id: 'sets' as PageTab, label: 'Conjuntos de Descriptores', icon: <FlaskConical size={13} /> },
          { id: 'space-map' as PageTab, label: 'Mapa del Espacio Químico', icon: <Map size={13} /> },
        ]).map((t) => (
          <button
            key={t.id}
            onClick={() => setPageTab(t.id)}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              pageTab === t.id ? 'bg-cyan-500 text-navy-900' : 'text-gray-400 hover:text-white'
            }`}
          >
            {t.icon} {t.label}
          </button>
        ))}
      </div>

      {/* Chemical Space Map tab */}
      {pageTab === 'space-map' && (
        <Card title="Mapa del Espacio Químico (t-SNE)">
          <div className="flex flex-wrap gap-3 mb-5">
            <div>
              <label className="block text-xs text-gray-400 mb-1">Conjunto de Descriptores</label>
              <select
                value={selectedSetForMap}
                onChange={(e) => setSelectedSetForMap(e.target.value)}
                className="bg-navy-700 border border-navy-500 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-cyan-400 transition-colors"
              >
                <option value="">Seleccione un conjunto…</option>
                {descriptors.map((d) => (
                  <option key={d.id} value={d.id}>{d.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Propiedad de color</label>
              <select
                value={colorProperty}
                onChange={(e) => setColorProperty(e.target.value)}
                className="bg-navy-700 border border-navy-500 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-cyan-400 transition-colors"
              >
                <option value="formation_energy_per_atom">Energía de Formación</option>
                <option value="energy_above_hull">Energía sobre el Casco Convexo</option>
                <option value="band_gap">Band Gap</option>
              </select>
            </div>
            <div className="self-end">
              <button
                onClick={handleLoadMap}
                disabled={!selectedSetForMap || mapLoading}
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-navy-900 bg-cyan-500 hover:bg-cyan-400 disabled:opacity-50 rounded-lg transition-colors"
              >
                {mapLoading ? <><RefreshCw size={13} className="animate-spin" /> Calculando…</> : <><Map size={13} /> Generar Mapa</>}
              </button>
            </div>
          </div>
          {mapLoading && <LoadingSpinner />}
          {mapError && <div className="text-red-400 text-sm">{mapError}</div>}
          {!mapLoading && !mapError && spaceMapPoints.length > 0 && (
            <ChemicalSpaceMap
              points={spaceMapPoints}
              colorMin={colorMin}
              colorMax={colorMax}
              colorProperty={mapColorProp}
            />
          )}
          {!mapLoading && !mapError && spaceMapPoints.length === 0 && !mapColorProp && (
            <div className="text-center py-12 text-gray-500 text-sm">
              Seleccione un conjunto de descriptores y haga clic en Generar Mapa para visualizar cómo se agrupan los materiales en el espacio químico.
            </div>
          )}
        </Card>
      )}

      {pageTab === 'sets' && descriptors.length > 0 && (
        <Card title="Cantidad de Características por Conjunto de Descriptores">
          <ResponsiveContainer width="100%" height={180}>
            <BarChart
              data={descriptors.map((d) => ({ name: d.name, features: d.n_features ?? 0 }))}
              margin={{ top: 4, right: 8, left: -8, bottom: 4 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#1e3a5f" />
              <XAxis dataKey="name" tick={{ fill: '#9ca3af', fontSize: 11 }} />
              <YAxis tick={{ fill: '#9ca3af', fontSize: 11 }} allowDecimals={false} />
              <Tooltip
                contentStyle={{ background: '#0f2744', border: '1px solid #1e3a5f', borderRadius: 8 }}
                labelStyle={{ color: '#e2e8f0' }}
                itemStyle={{ color: '#8b5cf6' }}
                formatter={(v: number) => [v.toLocaleString(), 'Características']}
              />
              <Bar dataKey="features" radius={[4, 4, 0, 0]}>
                {descriptors.map((_, i) => (
                  <Cell key={i} fill={i % 2 === 0 ? '#8b5cf6' : '#06b6d4'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>
      )}

      {pageTab === 'sets' && (
        <>
          <Card>
            {loading ? (
              <LoadingSpinner />
            ) : descriptors.length === 0 ? (
              <EmptyState
                icon={<FlaskConical size={48} />}
                title="No se encontraron conjuntos de descriptores"
                description="Los conjuntos de descriptores se generan automáticamente al iniciar un entrenamiento."
              />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-navy-600">
                      <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Nombre</th>
                      <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Tipo</th>
                      <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Versión</th>
                      <th className="text-right py-3 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Características</th>
                      <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Creado</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-navy-700">
                    {descriptors.map((d) => (
                      <tr key={d.id} className="hover:bg-navy-700/50 transition-colors">
                        <td className="py-3 px-4 font-medium text-white">{d.name}</td>
                        <td className="py-3 px-4">
                          <span className="px-2 py-0.5 bg-navy-600 text-gray-300 rounded text-xs font-mono">{d.descriptor_type}</span>
                        </td>
                        <td className="py-3 px-4 text-gray-400 text-xs font-mono">{d.version}</td>
                        <td className="py-3 px-4 text-right text-cyan-400 font-mono">{d.n_features?.toLocaleString() ?? '—'}</td>
                        <td className="py-3 px-4 text-gray-500 text-xs">{formatDate(d.created_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>

          <Card title="Acerca de los Descriptores">
            <div className="text-sm text-gray-400 space-y-2">
              <p>
                Los descriptores codifican información química y estructural de los materiales en
                vectores de características numéricas adecuados para el aprendizaje automático.
              </p>
              <p>
                MatEnergy-ML usa descriptores basados en composición (Magpie, Deml, Meredig) derivados
                de estadísticas elementales. Cada material se representa con ~130 características que capturan
                electronegatividad, radio atómico, energías de formación y más.
              </p>
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
