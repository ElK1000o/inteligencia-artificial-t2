import { useEffect, useState, FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { Database, Upload, RefreshCw, Eye, AlertCircle } from 'lucide-react';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { EmptyState } from '../components/ui/EmptyState';
import { Modal } from '../components/ui/Modal';
import { listDatasets, uploadDataset, getValidationReport } from '../api/datasets';
import { Dataset, ValidationReport } from '../types';

type BadgeVariant = 'valid' | 'invalid' | 'pending' | 'default';

function statusVariant(status: string): BadgeVariant {
  const map: Record<string, BadgeVariant> = {
    valid: 'valid',
    validated: 'valid',
    invalid: 'invalid',
    failed: 'invalid',
    pending: 'pending',
    validating: 'pending',
    imported: 'valid',
  };
  return map[status.toLowerCase()] ?? 'default';
}

function formatDate(iso: string | null) {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('es-ES', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

export function DatasetsPage() {
  const navigate = useNavigate();
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [reportOpen, setReportOpen] = useState(false);
  const [selectedReport, setSelectedReport] = useState<ValidationReport | null>(null);
  const [reportLoading, setReportLoading] = useState(false);

  // Upload form state
  const [file, setFile] = useState<File | null>(null);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');

  const fetchDatasets = () => {
    setLoading(true);
    listDatasets()
      .then((r) => setDatasets(r.data))
      .catch(() => setDatasets([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchDatasets();
  }, []);

  const handleUpload = async (e: FormEvent) => {
    e.preventDefault();
    if (!file || !name.trim()) return;
    setUploadError('');
    setUploading(true);
    try {
      await uploadDataset(file, name, description || undefined);
      setUploadOpen(false);
      setFile(null);
      setName('');
      setDescription('');
      fetchDatasets();
    } catch (err: unknown) {
      const msg =
        err && typeof err === 'object' && 'response' in err
          ? (err as { response?: { data?: { message?: string } } }).response?.data?.message
          : undefined;
      setUploadError(msg || 'Error al subir el archivo. Intente nuevamente.');
    } finally {
      setUploading(false);
    }
  };

  const handleViewReport = async (datasetId: string) => {
    setReportLoading(true);
    setReportOpen(true);
    setSelectedReport(null);
    try {
      const r = await getValidationReport(datasetId);
      setSelectedReport(r.data);
    } catch {
      setSelectedReport(null);
    } finally {
      setReportLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Datasets</h1>
          <p className="text-gray-400 text-sm mt-1">
            Gestione y valide los datasets de propiedades de materiales
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={fetchDatasets}
            className="flex items-center gap-2 px-3 py-2 text-sm text-gray-400 hover:text-white bg-navy-700 hover:bg-navy-600 border border-navy-500 rounded-lg transition-colors"
          >
            <RefreshCw size={14} /> Actualizar
          </button>
          <button
            onClick={() => setUploadOpen(true)}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-navy-900 bg-cyan-500 hover:bg-cyan-400 rounded-lg transition-colors"
          >
            <Upload size={14} /> Subir Dataset
          </button>
        </div>
      </div>

      <Card>
        {loading ? (
          <LoadingSpinner />
        ) : datasets.length === 0 ? (
          <EmptyState
            icon={<Database size={48} />}
            title="Aún no hay datasets"
            description="Suba un archivo CSV o JSON para comenzar el cribado de propiedades de materiales."
            action={
              <button
                onClick={() => setUploadOpen(true)}
                className="px-4 py-2 bg-cyan-500 hover:bg-cyan-400 text-navy-900 text-sm font-medium rounded-lg transition-colors"
              >
                Suba su primer dataset
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
                    Estado
                  </th>
                  <th className="text-right py-3 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    Filas Totales
                  </th>
                  <th className="text-right py-3 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    Válidas
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    Propiedades
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    Importado
                  </th>
                  <th className="text-center py-3 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    Reporte
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-navy-700">
                {datasets.map((ds) => (
                  <tr
                    key={ds.id}
                    className="hover:bg-navy-700/50 transition-colors"
                  >
                    <td className="py-3 px-4">
                      <div className="font-medium text-white">{ds.name}</div>
                      {ds.description && (
                        <div className="text-xs text-gray-500 mt-0.5 truncate max-w-xs">
                          {ds.description}
                        </div>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      <Badge
                        label={ds.status}
                        variant={statusVariant(ds.status)}
                      />
                    </td>
                    <td className="py-3 px-4 text-right text-gray-300">
                      {ds.row_count?.toLocaleString() ?? '—'}
                    </td>
                    <td className="py-3 px-4 text-right">
                      {ds.valid_row_count != null ? (
                        <span className="text-green-400">
                          {ds.valid_row_count.toLocaleString()}
                        </span>
                      ) : (
                        <span className="text-gray-500">—</span>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      {ds.available_properties?.length ? (
                        <div className="flex flex-wrap gap-1 max-w-xs">
                          {ds.available_properties.slice(0, 3).map((p) => (
                            <span
                              key={p}
                              className="px-1.5 py-0.5 bg-navy-600 text-gray-300 rounded text-xs"
                            >
                              {p}
                            </span>
                          ))}
                          {ds.available_properties.length > 3 && (
                            <span className="px-1.5 py-0.5 bg-navy-600 text-gray-500 rounded text-xs">
                              +{ds.available_properties.length - 3}
                            </span>
                          )}
                        </div>
                      ) : (
                        <span className="text-gray-500">—</span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-gray-400 text-xs">
                      {formatDate(ds.imported_at)}
                    </td>
                    <td className="py-3 px-4 text-center">
                      <button
                        onClick={() => navigate(`/datasets/${ds.id}/validation-report`)}
                        className="inline-flex items-center gap-1 px-2 py-1 text-xs text-cyan-400 hover:text-cyan-300 hover:bg-cyan-500/10 rounded transition-colors"
                      >
                        <Eye size={12} /> Ver
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Upload Modal */}
      <Modal
        open={uploadOpen}
        onClose={() => {
          setUploadOpen(false);
          setUploadError('');
        }}
        title="Subir Dataset"
      >
        <form onSubmit={handleUpload} className="space-y-5">
          <div>
            <label className="block text-sm text-gray-400 mb-2">
              Nombre del Dataset <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              placeholder="p. ej. AFLOW Battery Oxides 2024"
              className="w-full bg-navy-700 border border-navy-500 rounded-lg px-4 py-2.5 text-white placeholder-gray-500 focus:outline-none focus:border-cyan-400 transition-colors"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-2">Descripción</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
              placeholder="Descripción opcional..."
              className="w-full bg-navy-700 border border-navy-500 rounded-lg px-4 py-2.5 text-white placeholder-gray-500 focus:outline-none focus:border-cyan-400 transition-colors resize-none"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-2">
              Archivo (CSV / JSON) <span className="text-red-400">*</span>
            </label>
            <div className="border-2 border-dashed border-navy-500 hover:border-cyan-400/50 rounded-lg p-6 text-center transition-colors">
              <input
                type="file"
                accept=".csv,.json"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                className="hidden"
                id="file-upload"
                required
              />
              <label htmlFor="file-upload" className="cursor-pointer">
                {file ? (
                  <div>
                    <div className="text-white font-medium">{file.name}</div>
                    <div className="text-xs text-gray-500 mt-1">
                      {(file.size / 1024 / 1024).toFixed(2)} MB
                    </div>
                  </div>
                ) : (
                  <div>
                    <Upload size={24} className="mx-auto text-gray-500 mb-2" />
                    <div className="text-sm text-gray-400">
                      Haga clic para seleccionar un archivo o arrástrelo aquí
                    </div>
                    <div className="text-xs text-gray-600 mt-1">CSV, JSON de hasta 500 MB</div>
                  </div>
                )}
              </label>
            </div>
          </div>
          {uploadError && (
            <div className="flex items-start gap-2 bg-red-500/10 border border-red-500/30 text-red-400 text-sm px-4 py-3 rounded-lg">
              <AlertCircle size={16} className="mt-0.5 flex-shrink-0" />
              {uploadError}
            </div>
          )}
          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={() => setUploadOpen(false)}
              className="flex-1 py-2.5 text-sm text-gray-400 hover:text-white bg-navy-700 hover:bg-navy-600 border border-navy-500 rounded-lg transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={uploading || !file || !name.trim()}
              className="flex-1 py-2.5 text-sm font-medium text-navy-900 bg-cyan-500 hover:bg-cyan-400 disabled:opacity-50 rounded-lg transition-colors"
            >
              {uploading ? 'Subiendo...' : 'Subir'}
            </button>
          </div>
        </form>
      </Modal>

      {/* Validation Report Modal */}
      <Modal
        open={reportOpen}
        onClose={() => setReportOpen(false)}
        title="Reporte de Validación"
        size="lg"
      >
        {reportLoading ? (
          <LoadingSpinner />
        ) : selectedReport ? (
          <div className="space-y-4 text-sm">
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-navy-700 rounded-lg p-4 text-center">
                <div className="text-2xl font-bold text-white">
                  {selectedReport.total_rows?.toLocaleString() ?? '—'}
                </div>
                <div className="text-xs text-gray-500 mt-1">Filas Totales</div>
              </div>
              <div className="bg-navy-700 rounded-lg p-4 text-center">
                <div className="text-2xl font-bold text-green-400">
                  {selectedReport.valid_rows?.toLocaleString() ?? '—'}
                </div>
                <div className="text-xs text-gray-500 mt-1">Filas Válidas</div>
              </div>
              <div className="bg-navy-700 rounded-lg p-4 text-center">
                <div className="text-2xl font-bold text-red-400">
                  {selectedReport.rejected_rows?.toLocaleString() ?? '—'}
                </div>
                <div className="text-xs text-gray-500 mt-1">Filas Rechazadas</div>
              </div>
            </div>
            {selectedReport.warnings && selectedReport.warnings.length > 0 && (
              <div>
                <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                  Advertencias
                </h4>
                <ul className="space-y-1">
                  {selectedReport.warnings.map((w, i) => (
                    <li
                      key={i}
                      className="flex items-start gap-2 text-yellow-400 text-xs bg-yellow-500/10 border border-yellow-500/20 rounded px-3 py-2"
                    >
                      <AlertCircle size={12} className="mt-0.5 flex-shrink-0" />
                      {w}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {selectedReport.validation_errors &&
              Object.keys(selectedReport.validation_errors).length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                    Errores de Validación
                  </h4>
                  <pre className="bg-navy-700 rounded-lg p-4 text-xs text-red-300 overflow-auto max-h-48">
                    {JSON.stringify(selectedReport.validation_errors, null, 2)}
                  </pre>
                </div>
              )}
            <div className="text-xs text-gray-600">
              Validado el: {formatDate(selectedReport.validated_at)}
            </div>
          </div>
        ) : (
          <EmptyState
            icon={<AlertCircle size={32} />}
            title="Reporte no disponible"
            description="No se encontró un reporte de validación para este dataset."
          />
        )}
      </Modal>
    </div>
  );
}
