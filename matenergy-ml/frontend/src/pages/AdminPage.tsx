import { Shield } from 'lucide-react';
import { Card } from '../components/ui/Card';
import { useAuth } from '../hooks/useAuth';

export function AdminPage() {
  const { user } = useAuth();
  const isAdmin = user?.roles?.includes('admin');

  if (!isAdmin) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <Shield size={40} className="text-gray-600 mx-auto mb-4" />
          <h2 className="text-white font-semibold">Acceso Restringido</h2>
          <p className="text-gray-400 text-sm mt-2">Se requiere rol de administrador para ver esta página</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Panel de Administración</h1>
        <p className="text-gray-400 text-sm mt-1">Eventos de seguridad, registros de auditoría y gestión del sistema</p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card title="Eventos de Seguridad" badge="Monitor" badgeColor="red">
          <p className="text-gray-400 text-sm">Monitoreo de eventos de seguridad mediante el registro de auditoría de la base de datos. Revisa el dashboard para ver el conteo de eventos activos e incidentes sin resolver.</p>
        </Card>
        <Card title="Registro de Auditoría" badge="Trace">
          <p className="text-gray-400 text-sm">Cada acción de usuario se registra con ID de usuario, marca de tiempo, dirección IP y recurso afectado. Los registros de auditoría son de solo anexado y a prueba de manipulación.</p>
        </Card>
        <Card title="Gestión de Usuarios">
          <p className="text-gray-400 text-sm">
            Registra nuevos usuarios mediante <code className="text-cyan-400 text-xs bg-navy-700 px-1 py-0.5 rounded">POST /api/v1/auth/register</code> con credenciales de administrador.
            Roles: admin, researcher, viewer.
          </p>
        </Card>
        <Card title="Configuración del Sistema">
          <p className="text-gray-400 text-sm">
            Los parámetros principales (umbral de estabilidad, límites de tasa, límites de carga) se configuran mediante variables de entorno.
            Consulta <code className="text-cyan-400 text-xs bg-navy-700 px-1 py-0.5 rounded">.env.example</code> para ver todas las opciones.
          </p>
        </Card>
      </div>
    </div>
  );
}
