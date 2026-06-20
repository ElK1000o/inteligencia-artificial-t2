import { FileText, Download } from 'lucide-react';
import { Card } from '../components/ui/Card';

const reportTypes = [
  {
    title: 'Reporte de Validación',
    description: 'Métricas de calidad del dataset, filas rechazadas y violaciones de esquema.',
    format: 'PDF / JSON',
    status: 'coming_soon',
  },
  {
    title: 'Reporte de Rendimiento del Modelo',
    description: 'Métricas de entrenamiento/validación/prueba, curvas de aprendizaje e importancia de variables.',
    format: 'PDF / HTML',
    status: 'coming_soon',
  },
  {
    title: 'Reporte de Ranking de Candidatos',
    description: 'Lista priorizada de materiales candidatos con puntajes y resúmenes de razonamiento.',
    format: 'CSV / PDF',
    status: 'coming_soon',
  },
  {
    title: 'Exportación de Registro de Auditoría',
    description: 'Registro completo de actividad de usuarios y eventos de seguridad para cumplimiento.',
    format: 'CSV / JSON',
    status: 'coming_soon',
  },
];

export function ReportsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Reportes</h1>
        <p className="text-gray-400 text-sm mt-1">
          Exporta y descarga reportes de análisis
        </p>
      </div>

      <div className="bg-yellow-500/10 border border-yellow-500/30 text-yellow-400 text-sm px-5 py-4 rounded-xl">
        La funcionalidad de exportación está en desarrollo. Los tipos de reporte a continuación
        estarán disponibles en una próxima versión.
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {reportTypes.map(({ title, description, format }) => (
          <Card key={title}>
            <div className="flex items-start justify-between gap-4">
              <div className="p-3 bg-navy-700 rounded-lg">
                <FileText size={20} className="text-cyan-400" />
              </div>
              <div className="flex-1">
                <h3 className="text-sm font-semibold text-white">{title}</h3>
                <p className="text-xs text-gray-400 mt-1">{description}</p>
                <div className="flex items-center justify-between mt-3">
                  <span className="text-xs text-gray-600">{format}</span>
                  <button
                    disabled
                    className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-500 bg-navy-700 border border-navy-500 rounded-lg cursor-not-allowed opacity-50"
                  >
                    <Download size={11} /> Exportar
                  </button>
                </div>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
