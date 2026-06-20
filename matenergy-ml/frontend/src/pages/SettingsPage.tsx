import { Card } from '../components/ui/Card';
import { useAuth } from '../hooks/useAuth';

export function SettingsPage() {
  const { user } = useAuth();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Configuración</h1>
        <p className="text-gray-400 text-sm mt-1">Información de la cuenta y parámetros de configuración científica</p>
      </div>

      <Card title="Cuenta">
        <div className="space-y-0 text-sm divide-y divide-navy-700">
          {[
            { label: 'Nombre de Usuario', value: user?.username },
            { label: 'Correo Electrónico', value: user?.email },
            { label: 'Roles', value: user?.roles?.join(', ') || '—' },
            { label: 'Estado', value: user?.is_active ? 'Activo' : 'Inactivo' },
          ].map(({ label, value }) => (
            <div key={label} className="flex justify-between items-center py-3">
              <span className="text-gray-400">{label}</span>
              <span className="text-white">{value}</span>
            </div>
          ))}
        </div>
      </Card>

      <Card title="Parámetros Científicos">
        <div className="space-y-0 text-sm divide-y divide-navy-700">
          {[
            { label: 'Umbral de Estabilidad', value: '0.05 eV/atom', desc: 'corte de energy_above_hull para clasificación como estable' },
            { label: 'Tamaño Máximo de Carga', value: '50 MB', desc: 'Tamaño máximo de archivo CSV por carga' },
            { label: 'Máximo de Filas por Dataset', value: '100,000', desc: 'Cantidad máxima de filas procesadas por dataset' },
            { label: 'Semilla Aleatoria Fija', value: '42', desc: 'Garantiza divisiones train/test reproducibles entre ejecuciones' },
            { label: 'Mínimo de Muestras de Entrenamiento', value: '20', desc: 'Cantidad mínima de muestras válidas requeridas para entrenar cualquier modelo' },
            { label: 'TTL del Token de Acceso', value: '15 min', desc: 'Vida útil corta del token de acceso JWT' },
            { label: 'TTL del Token de Actualización', value: '7 días', desc: 'Vida útil del token de actualización (se rota en cada uso)' },
          ].map(({ label, value, desc }) => (
            <div key={label} className="flex justify-between items-start py-3">
              <div>
                <span className="text-gray-300">{label}</span>
                <p className="text-xs text-gray-500 mt-0.5">{desc}</p>
              </div>
              <span className="text-cyan-400 font-mono text-xs ml-4 shrink-0">{value}</span>
            </div>
          ))}
        </div>
      </Card>

      <Card title="Rangos de Propiedades Físicas">
        <div className="space-y-0 text-sm divide-y divide-navy-700">
          {[
            { property: 'energy_above_hull', range: '−0.5 a 10.0 eV/atom', unit: 'eV/atom' },
            { property: 'formation_energy_per_atom', range: '−10.0 a 5.0 eV/atom', unit: 'eV/atom' },
            { property: 'band_gap', range: '0.0 a 20.0 eV', unit: 'eV' },
          ].map(({ property, range }) => (
            <div key={property} className="flex justify-between items-center py-3">
              <span className="text-gray-400 font-mono text-xs">{property}</span>
              <span className="text-gray-300 text-xs">{range}</span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
