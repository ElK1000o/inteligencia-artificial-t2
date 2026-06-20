import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, CheckCircle2, XCircle, AlertTriangle, Download } from 'lucide-react';
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
import { Badge } from '../components/ui/Badge';
import { getValidationReport } from '../api/datasets';
import { ValidationReport } from '../types';

function formatDate(iso: string | null) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('es-ES', {
    year: 'numeric', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

type RejectedRow = {
  row_number: number;
  raw_data: Record<string, unknown> | null;
  rejection_reasons: string[] | null;
};

export function ValidationReportPage() {
  const { id } = useParams<{ id: string }>();
  const [report, setReport] = useState<ValidationReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!id) return;
    getValidationReport(id)
      .then((r) => setReport(r.data))
      .catch(() => setError('No se pudo cargar el reporte de validación.'))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="p-8"><LoadingSpinner /></div>;

  if (error || !report) {
    return (
      <div className="p-8">
        <EmptyState
          icon={<XCircle size={48} />}
          title="Reporte no encontrado"
          description={error || 'No existe un reporte de validación para este dataset.'}
          action={<Link to="/datasets" className="px-4 py-2 bg-cyan-500 text-navy-900 rounded-lg text-sm font-medium">Volver a Datasets</Link>}
        />
      </div>
    );
  }

  const validPct = report.total_rows
    ? ((report.valid_rows ?? 0) / report.total_rows * 100).toFixed(1)
    : '0';

  const chartData = [
    { name: 'Válidas', value: report.valid_rows ?? 0, fill: '#10b981' },
    { name: 'Rechazadas', value: report.rejected_rows ?? 0, fill: '#ef4444' },
  ];

  const errorEntries = report.validation_errors
    ? Object.entries(report.validation_errors as Record<string, unknown>)
    : [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link
          to="/datasets"
          className="p-2 rounded-lg bg-navy-700 hover:bg-navy-600 text-gray-400 hover:text-white transition-colors"
        >
          <ArrowLeft size={16} />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-white">Reporte de Validación</h1>
          <p className="text-gray-400 text-sm mt-1">
            ID del Dataset: <span className="font-mono text-xs text-gray-500">{id}</span>
          </p>
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="bg-navy-800 border border-navy-600 rounded-xl p-4">
          <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">Filas Totales</div>
          <div className="text-2xl font-bold text-white">{report.total_rows ?? '—'}</div>
        </div>
        <div className="bg-navy-800 border border-green-500/30 rounded-xl p-4">
          <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">Filas Válidas</div>
          <div className="text-2xl font-bold text-green-400">{report.valid_rows ?? '—'}</div>
          <div className="text-xs text-gray-500 mt-1">{validPct}% de aprobación</div>
        </div>
        <div className="bg-navy-800 border border-red-500/30 rounded-xl p-4">
          <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">Filas Rechazadas</div>
          <div className="text-2xl font-bold text-red-400">{report.rejected_rows ?? '—'}</div>
        </div>
        <div className="bg-navy-800 border border-navy-600 rounded-xl p-4">
          <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">Validado el</div>
          <div className="text-sm font-medium text-gray-300">{formatDate(report.validated_at)}</div>
        </div>
      </div>

      {/* Chart + Errors grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title="Distribución de Filas">
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e3a5f" />
              <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 13 }} />
              <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} />
              <Tooltip
                contentStyle={{ background: '#1e3a5f', border: '1px solid #334155', borderRadius: '8px' }}
              />
              <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                {chartData.map((entry, idx) => (
                  <Cell key={idx} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>

        <Card title="Errores de Validación">
          {errorEntries.length === 0 ? (
            <div className="flex items-center gap-2 py-6 text-green-400">
              <CheckCircle2 size={18} />
              <span className="text-sm">No se detectaron errores de validación</span>
            </div>
          ) : (
            <div className="space-y-2 max-h-52 overflow-y-auto">
              {errorEntries.map(([key, val]) => (
                <div key={key} className="bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2 text-xs">
                  <span className="font-medium text-red-400">{key}:</span>
                  <span className="text-gray-300 ml-2">{String(val)}</span>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      {/* Warnings */}
      {report.warnings && report.warnings.length > 0 && (
        <Card title="Advertencias">
          <div className="space-y-2">
            {report.warnings.map((w, i) => (
              <div key={i} className="flex items-start gap-2 bg-yellow-500/10 border border-yellow-500/20 rounded-lg px-3 py-2 text-xs">
                <AlertTriangle size={14} className="text-yellow-400 flex-shrink-0 mt-0.5" />
                <span className="text-gray-300">{w}</span>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Back button */}
      <div className="flex gap-3">
        <Link
          to="/datasets"
          className="px-4 py-2 text-sm text-gray-400 hover:text-white bg-navy-700 hover:bg-navy-600 border border-navy-500 rounded-lg transition-colors"
        >
          ← Volver a Datasets
        </Link>
      </div>
    </div>
  );
}
