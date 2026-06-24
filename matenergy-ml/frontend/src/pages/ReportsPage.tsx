import { useEffect, useState, FormEvent } from 'react';
import { FileText, Download, AlertCircle, RefreshCw } from 'lucide-react';
import { Card } from '../components/ui/Card';
import { Modal } from '../components/ui/Modal';
import { EmptyState } from '../components/ui/EmptyState';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { generateReport, listReports, downloadReport, ReportFileInfo } from '../api/reports';
import { listDatasets } from '../api/datasets';
import { listModels } from '../api/models';
import { listRankings } from '../api/rankings';
import { Dataset, ModelVersion, CandidateRanking } from '../types';

type ReportKey = 'ranking' | 'model_metrics' | 'dataset_summary' | 'platform_summary';
type ResourceKind = 'ranking' | 'model' | 'dataset' | null;

interface ReportTypeDef {
  key: ReportKey;
  title: string;
  description: string;
  format: string;
  resource: ResourceKind;
}

const REPORT_TYPES: ReportTypeDef[] = [
  {
    key: 'dataset_summary',
    title: 'Reporte de Resumen de Dataset',
    description: 'Estadísticas del dataset, filas válidas/rechazadas y propiedades disponibles.',
    format: 'Markdown',
    resource: 'dataset',
  },
  {
    key: 'model_metrics',
    title: 'Reporte de Rendimiento del Modelo',
    description: 'Métricas de entrenamiento/validación/prueba para una versión de modelo.',
    format: 'Markdown',
    resource: 'model',
  },
  {
    key: 'ranking',
    title: 'Reporte de Ranking de Candidatos',
    description: 'Lista priorizada de materiales candidatos con puntajes y razonamiento.',
    format: 'CSV',
    resource: 'ranking',
  },
  {
    key: 'platform_summary',
    title: 'Resumen de la Plataforma',
    description: 'Conteo agregado de datasets, materiales y versiones de modelo.',
    format: 'Markdown',
    resource: null,
  },
];

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function extractErrorMessage(err: unknown, fallback: string): string {
  if (err && typeof err === 'object' && 'response' in err) {
    const data = (err as { response?: { data?: { message?: string; detail?: string } } }).response
      ?.data;
    return data?.message || data?.detail || fallback;
  }
  return fallback;
}

export function ReportsPage() {
  const [reports, setReports] = useState<ReportFileInfo[]>([]);
  const [reportsLoading, setReportsLoading] = useState(true);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [models, setModels] = useState<ModelVersion[]>([]);
  const [rankings, setRankings] = useState<CandidateRanking[]>([]);

  const [activeType, setActiveType] = useState<ReportTypeDef | null>(null);
  const [resourceId, setResourceId] = useState('');
  const [generating, setGenerating] = useState(false);
  const [generateError, setGenerateError] = useState('');
  const [downloadingFile, setDownloadingFile] = useState<string | null>(null);

  const fetchReports = () => {
    setReportsLoading(true);
    listReports()
      .then((r) => setReports(r.data))
      .catch(() => setReports([]))
      .finally(() => setReportsLoading(false));
  };

  useEffect(() => {
    fetchReports();
    listDatasets().then((r) => setDatasets(r.data)).catch(() => setDatasets([]));
    listModels().then((r) => setModels(r.data)).catch(() => setModels([]));
    listRankings().then((r) => setRankings(r.data)).catch(() => setRankings([]));
  }, []);

  const openGenerate = (type: ReportTypeDef) => {
    setActiveType(type);
    setResourceId('');
    setGenerateError('');
  };

  const handleGenerate = async (e: FormEvent) => {
    e.preventDefault();
    if (!activeType) return;
    setGenerateError('');
    setGenerating(true);
    try {
      await generateReport(activeType.key, activeType.resource ? resourceId : undefined);
      setActiveType(null);
      fetchReports();
    } catch (err: unknown) {
      setGenerateError(
        extractErrorMessage(err, 'No se pudo generar el reporte. Inténtalo de nuevo.')
      );
    } finally {
      setGenerating(false);
    }
  };

  const handleDownload = async (filename: string) => {
    setDownloadingFile(filename);
    try {
      const res = await downloadReport(filename);
      const blob = new Blob([res.data], {
        type: (res.headers['content-type'] as string) || 'application/octet-stream',
      });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      // File may have been removed on disk — list stays stale until manual refresh.
    } finally {
      setDownloadingFile(null);
    }
  };

  const resourceLabel = (resource: ResourceKind): string => {
    if (resource === 'dataset') return 'Dataset';
    if (resource === 'model') return 'Versión de Modelo';
    if (resource === 'ranking') return 'Ranking';
    return '';
  };

  const renderResourceSelect = () => {
    if (!activeType?.resource) return null;
    const baseClass =
      'w-full bg-navy-700 border border-navy-500 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-cyan-400 transition-colors';

    if (activeType.resource === 'dataset') {
      return (
        <select required value={resourceId} onChange={(e) => setResourceId(e.target.value)} className={baseClass}>
          <option value="">Selecciona un dataset...</option>
          {datasets.map((d) => (
            <option key={d.id} value={d.id}>
              {d.name}
            </option>
          ))}
        </select>
      );
    }
    if (activeType.resource === 'model') {
      return (
        <select required value={resourceId} onChange={(e) => setResourceId(e.target.value)} className={baseClass}>
          <option value="">Selecciona una versión de modelo...</option>
          {models.map((m) => (
            <option key={m.id} value={m.id}>
              {m.name} ({m.target_property})
            </option>
          ))}
        </select>
      );
    }
    return (
      <select required value={resourceId} onChange={(e) => setResourceId(e.target.value)} className={baseClass}>
        <option value="">Selecciona un ranking...</option>
        {rankings.map((r) => (
          <option key={r.id} value={r.id}>
            {r.name}
          </option>
        ))}
      </select>
    );
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Reportes</h1>
        <p className="text-gray-400 text-sm mt-1">Genera y descarga reportes de análisis</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {REPORT_TYPES.map((type) => (
          <Card key={type.key}>
            <div className="flex items-start justify-between gap-4">
              <div className="p-3 bg-navy-700 rounded-lg">
                <FileText size={20} className="text-cyan-400" />
              </div>
              <div className="flex-1">
                <h3 className="text-sm font-semibold text-white">{type.title}</h3>
                <p className="text-xs text-gray-400 mt-1">{type.description}</p>
                <div className="flex items-center justify-between mt-3">
                  <span className="text-xs text-gray-600">{type.format}</span>
                  <button
                    onClick={() => openGenerate(type)}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-navy-900 bg-cyan-500 hover:bg-cyan-400 rounded-lg transition-colors"
                  >
                    <FileText size={11} /> Generar
                  </button>
                </div>
              </div>
            </div>
          </Card>
        ))}
      </div>

      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">
          Reportes Generados
        </h2>
        <button
          onClick={fetchReports}
          className="flex items-center gap-2 px-3 py-1.5 text-xs text-gray-400 hover:text-white bg-navy-700 hover:bg-navy-600 border border-navy-500 rounded-lg transition-colors"
        >
          <RefreshCw size={12} /> Actualizar
        </button>
      </div>

      <Card>
        {reportsLoading ? (
          <LoadingSpinner size="sm" />
        ) : reports.length === 0 ? (
          <EmptyState
            icon={<FileText size={32} />}
            title="Aún no hay reportes generados"
            description="Usa los botones 'Generar' arriba para crear tu primer reporte."
          />
        ) : (
          <div className="space-y-2">
            {reports.map((r) => (
              <div
                key={r.filename}
                className="flex items-center justify-between p-3 bg-navy-700 border border-navy-500 rounded-lg"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <FileText size={16} className="text-cyan-400 flex-shrink-0" />
                  <div className="min-w-0">
                    <div className="text-sm text-white truncate">{r.filename}</div>
                    <div className="text-xs text-gray-500">{formatSize(r.size_bytes)}</div>
                  </div>
                </div>
                <button
                  onClick={() => handleDownload(r.filename)}
                  disabled={downloadingFile === r.filename}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-300 hover:text-white bg-navy-600 hover:bg-navy-500 border border-navy-500 rounded-lg transition-colors disabled:opacity-50 flex-shrink-0"
                >
                  <Download size={11} />{' '}
                  {downloadingFile === r.filename ? 'Descargando...' : 'Descargar'}
                </button>
              </div>
            ))}
          </div>
        )}
      </Card>

      <Modal open={!!activeType} onClose={() => setActiveType(null)} title={activeType?.title ?? ''}>
        <form onSubmit={handleGenerate} className="space-y-4">
          {activeType?.resource ? (
            <div>
              <label className="block text-sm text-gray-400 mb-2">
                {resourceLabel(activeType.resource)} <span className="text-red-400">*</span>
              </label>
              {renderResourceSelect()}
            </div>
          ) : (
            <p className="text-sm text-gray-400">
              Este reporte no requiere seleccionar un recurso — se genera con los datos agregados
              actuales de la plataforma.
            </p>
          )}
          {generateError && (
            <div className="flex items-start gap-2 bg-red-500/10 border border-red-500/30 text-red-400 text-sm px-4 py-3 rounded-lg">
              <AlertCircle size={16} className="mt-0.5 flex-shrink-0" />
              {generateError}
            </div>
          )}
          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={() => setActiveType(null)}
              className="flex-1 py-2.5 text-sm text-gray-400 hover:text-white bg-navy-700 hover:bg-navy-600 border border-navy-500 rounded-lg transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={generating}
              className="flex-1 py-2.5 text-sm font-medium text-navy-900 bg-cyan-500 hover:bg-cyan-400 disabled:opacity-50 rounded-lg transition-colors"
            >
              {generating ? 'Generando...' : 'Generar Reporte'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
