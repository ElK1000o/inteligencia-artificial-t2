import { useCallback, useEffect, useRef, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  CheckCircle,
  ChevronDown,
  ChevronUp,
  Clock,
  Info,
  Loader,
  LucideIcon,
  Play,
  RefreshCw,
  TerminalSquare,
  Trash2,
  XCircle,
} from 'lucide-react';
import { Card } from '../components/ui/Card';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import {
  cancelDftJob,
  DftJob,
  listDftJobs,
  submitDftJob,
} from '../api/dft';

// ── Status helpers ────────────────────────────────────────────────────────────

const STATUS_STYLES: Record<string, { color: string; Icon: LucideIcon }> = {
  pending:   { color: 'text-gray-400',    Icon: Clock },
  running:   { color: 'text-cyan-400',    Icon: Loader },
  completed: { color: 'text-emerald-400', Icon: CheckCircle },
  failed:    { color: 'text-red-400',     Icon: XCircle },
  cancelled: { color: 'text-gray-500',    Icon: XCircle },
};

// Display-only Spanish labels for the job status enum values (kept in English for lookups/comparisons)
const STATUS_LABELS_ES: Record<string, string> = {
  pending: 'pendiente',
  running: 'en ejecución',
  completed: 'completado',
  failed: 'fallido',
  cancelled: 'cancelado',
};

function StatusBadge({ status }: { status: string }) {
  const s = STATUS_STYLES[status] ?? STATUS_STYLES.pending;
  const { color, Icon } = s;
  return (
    <span className={`inline-flex items-center gap-1 text-xs font-medium ${color}`}>
      <Icon size={11} className={status === 'running' ? 'animate-spin' : ''} />
      {STATUS_LABELS_ES[status] ?? status}
    </span>
  );
}

function fmtDuration(created: string, completed: string | null): string {
  const start = new Date(created).getTime();
  const end = completed ? new Date(completed).getTime() : Date.now();
  const secs = Math.round((end - start) / 1000);
  if (secs < 60) return `${secs}s`;
  return `${Math.floor(secs / 60)}m ${secs % 60}s`;
}

// ── Result panel ─────────────────────────────────────────────────────────────

function ResultPanel({ job }: { job: DftJob }) {
  const r = job.result;
  if (!r) return null;

  const isApprox = r.source === 'deterministic_approximation';

  const rows: { label: string; value: string | null; unit: string }[] = [
    { label: 'Energía total',          value: r.total_energy?.toFixed(4) ?? null,         unit: 'eV'       },
    { label: 'Energía de formación',   value: r.formation_energy?.toFixed(4) ?? null,     unit: 'eV/atom'  },
    { label: 'Energía sobre el casco', value: r.energy_above_hull?.toFixed(4) ?? null,    unit: 'eV/atom'  },
    { label: 'Band gap',               value: r.band_gap?.toFixed(3) ?? null,             unit: 'eV'       },
    { label: 'Magnético',              value: r.is_magnetic === null ? null : r.is_magnetic ? 'Sí' : 'No', unit: '' },
    { label: 'Átomos',                 value: r.n_atoms?.toString() ?? null,              unit: ''         },
  ];

  return (
    <div className="mt-3 space-y-3">
      {isApprox && (
        <div className="flex items-start gap-2 p-2.5 bg-amber-500/10 border border-amber-500/30 rounded-lg text-xs text-amber-400">
          <AlertTriangle size={12} className="mt-0.5 shrink-0" />
          <span>
            <strong>Aproximación determinista</strong> — no es DFT real.
            Conecta VASP + SLURM HPC para obtener resultados de producción.
          </span>
        </div>
      )}
      <div className="grid grid-cols-3 gap-2">
        {rows.filter(r => r.value !== null).map(({ label, value, unit }) => (
          <div key={label} className="bg-navy-700 rounded-lg px-3 py-2">
            <div className="text-xs text-gray-500 mb-0.5">{label}</div>
            <div className="font-mono text-sm text-white">
              {value} <span className="text-gray-500 text-xs">{unit}</span>
            </div>
          </div>
        ))}
      </div>
      <div className="text-xs text-gray-600 font-mono">
        Calculador: {r.calculator ?? r.source ?? '—'}
      </div>
      {r.warning && (
        <div className="flex items-start gap-2 p-2.5 bg-navy-700 border border-navy-600 rounded-lg">
          <Info size={11} className="text-gray-500 mt-0.5 shrink-0" />
          <p className="text-xs text-gray-500 leading-relaxed">{r.warning}</p>
        </div>
      )}
    </div>
  );
}

// ── Job row ───────────────────────────────────────────────────────────────────

function JobRow({
  job,
  onCancel,
  onRefresh,
}: {
  job: DftJob;
  onCancel: (id: string) => void;
  onRefresh: () => void;
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border border-navy-600 rounded-xl overflow-hidden">
      <div
        className="flex items-center gap-3 p-3 cursor-pointer hover:bg-navy-700/40 transition-colors"
        onClick={() => setExpanded(v => !v)}
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-mono text-cyan-400 text-sm font-bold truncate">
              {job.job_name ?? job.formula ?? job.id.slice(0, 8)}
            </span>
            {job.formula && job.job_name && (
              <span className="text-xs text-gray-500 font-mono">{job.formula}</span>
            )}
            <span className="text-xs bg-navy-600 text-gray-400 rounded px-1.5 py-0.5">
              {job.calculation_type ?? '—'}
            </span>
            <span className="text-xs text-gray-600 bg-navy-700 rounded px-1.5 py-0.5">
              {job.adapter ?? 'local'}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-4 shrink-0">
          <StatusBadge status={job.status} />
          <span className="text-xs text-gray-600 font-mono">
            {fmtDuration(job.created_at, job.completed_at)}
          </span>
          {(job.status === 'pending' || job.status === 'running') && (
            <button
              onClick={e => { e.stopPropagation(); onCancel(job.id); }}
              className="text-xs text-red-400 hover:text-red-300 flex items-center gap-1 transition-colors"
              title="Cancelar trabajo"
            >
              <Trash2 size={11} /> Cancelar
            </button>
          )}
          {expanded ? <ChevronUp size={14} className="text-gray-500" /> : <ChevronDown size={14} className="text-gray-500" />}
        </div>
      </div>

      {expanded && (
        <div className="px-3 pb-3 border-t border-navy-600 bg-navy-800/40">
          {job.status === 'running' && (
            <div className="flex items-center gap-2 py-3 text-xs text-cyan-400">
              <Loader size={12} className="animate-spin" />
              Cálculo en progreso — se actualiza automáticamente cada 5 s
            </div>
          )}
          {job.status === 'failed' && (
            <div className="py-3 text-xs text-red-400">
              <strong>Error:</strong> {job.error_message ?? 'Error desconocido'}
            </div>
          )}
          {job.status === 'completed' && <ResultPanel job={job} />}
          {job.status === 'cancelled' && (
            <div className="py-3 text-xs text-gray-500">El trabajo fue cancelado.</div>
          )}
          {job.status === 'pending' && (
            <div className="flex items-center gap-2 py-3 text-xs text-gray-500">
              <Clock size={12} /> En cola — esperando hilo de trabajo
            </div>
          )}
          <div className="mt-2 text-xs text-gray-700 font-mono">ID: {job.id}</div>
        </div>
      )}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

const CALC_TYPES = ['static', 'relax', 'band_structure', 'dos'];
const FUNCTIONALS = ['PBE', 'PBE+U', 'HSE06'];
const ADAPTERS = [
  { value: 'local', label: 'Local (ASE/EMT + aproximación)' },
  { value: 'slurm', label: 'SLURM + VASP (stub de HPC)' },
];

export function DftJobsPage() {
  const [jobs, setJobs] = useState<DftJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitLoading, setSubmitLoading] = useState(false);
  const [submitError, setSubmitError] = useState('');
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Form state
  const [formula, setFormula] = useState('LiFePO4');
  const [calcType, setCalcType] = useState('static');
  const [functional, setFunctional] = useState('PBE');
  const [encut, setEncut] = useState(520);
  const [kpointsDensity, setKpointsDensity] = useState(1000);
  const [adapter, setAdapter] = useState('local');
  const [jobName, setJobName] = useState('');

  const fetchJobs = useCallback(async () => {
    try {
      const r = await listDftJobs({ limit: 50 });
      setJobs(r.data);
    } catch {
      /* silent — stale list is acceptable */
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);

  // Auto-poll while any job is pending or running
  useEffect(() => {
    const hasActive = jobs.some(j => j.status === 'pending' || j.status === 'running');
    if (hasActive && !pollRef.current) {
      pollRef.current = setInterval(fetchJobs, 5000);
    } else if (!hasActive && pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [jobs, fetchJobs]);

  const handleSubmit = async () => {
    if (!formula.trim()) return;
    setSubmitLoading(true);
    setSubmitError('');
    try {
      await submitDftJob({
        formula: formula.trim(),
        calculation_type: calcType,
        functional,
        encut,
        kpoints_density: kpointsDensity,
        hubbard_u: {},
        adapter,
        job_name: jobName.trim() || null,
      });
      await fetchJobs();
    } catch (e: unknown) {
      const msg =
        e && typeof e === 'object' && 'response' in e
          ? (e as { response?: { data?: { detail?: string } } }).response?.data?.detail ?? 'Error al enviar el trabajo'
          : 'Error al enviar el trabajo';
      setSubmitError(String(msg));
    } finally {
      setSubmitLoading(false);
    }
  };

  const handleCancel = async (id: string) => {
    try {
      await cancelDftJob(id);
      await fetchJobs();
    } catch {/* ignore */}
  };

  const nRunning = jobs.filter(j => j.status === 'running').length;
  const nCompleted = jobs.filter(j => j.status === 'completed').length;
  const nFailed = jobs.filter(j => j.status === 'failed').length;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <TerminalSquare size={22} className="text-cyan-400" />
          Trabajos de Simulación DFT
        </h1>
        <p className="text-gray-400 text-sm mt-1">
          Interfaz de simulación atomística — Etapa 13
        </p>
      </div>

      {/* Architecture note */}
      <div className="flex items-start gap-3 p-4 bg-cyan-500/5 border border-cyan-500/20 rounded-xl text-xs text-cyan-300/70">
        <Info size={14} className="mt-0.5 shrink-0 text-cyan-500" />
        <div>
          <strong className="text-cyan-400">Adaptador local:</strong> usa ASE/EMT para sistemas metálicos
          (Al, Cu, Ag, Au, Ni, Pd, Pt, Zn, Cd, Hg) o una aproximación determinista basada en la composición
          para todos los demás materiales. <strong className="text-cyan-400">Adaptador SLURM:</strong> genera
          archivos de entrada reales de VASP (POSCAR/INCAR/KPOINTS) y un script de SLURM — se conecta a tu cluster
          HPC cuando SLURM_HOST/SLURM_USER están configurados. Todos los trabajos se rastrean en la base de datos.
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: 'En ejecución', value: nRunning, color: 'text-cyan-400' },
          { label: 'Completados', value: nCompleted, color: 'text-emerald-400' },
          { label: 'Fallidos', value: nFailed, color: 'text-red-400' },
        ].map(({ label, value, color }) => (
          <Card key={label}>
            <div className="text-xs text-gray-500 mb-1">{label}</div>
            <div className={`text-2xl font-bold font-mono ${color}`}>{value}</div>
          </Card>
        ))}
      </div>

      {/* Submission form */}
      <Card title="Enviar Cálculo">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-400 mb-1.5">Fórmula</label>
            <input
              value={formula}
              onChange={e => setFormula(e.target.value)}
              placeholder="ej. LiFePO4"
              className="w-full bg-navy-700 border border-navy-500 rounded-lg px-3 py-2.5 text-sm text-gray-200 font-mono focus:outline-none focus:border-cyan-400 transition-colors"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-400 mb-1.5">Nombre del Trabajo (opcional)</label>
            <input
              value={jobName}
              onChange={e => setJobName(e.target.value)}
              placeholder="ej. cathode-screening-01"
              className="w-full bg-navy-700 border border-navy-500 rounded-lg px-3 py-2.5 text-sm text-gray-200 focus:outline-none focus:border-cyan-400 transition-colors"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-400 mb-1.5">Tipo de Cálculo</label>
            <select
              value={calcType}
              onChange={e => setCalcType(e.target.value)}
              className="w-full bg-navy-700 border border-navy-500 rounded-lg px-3 py-2.5 text-sm text-gray-200 focus:outline-none focus:border-cyan-400 transition-colors"
            >
              {CALC_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-400 mb-1.5">Funcional XC</label>
            <select
              value={functional}
              onChange={e => setFunctional(e.target.value)}
              className="w-full bg-navy-700 border border-navy-500 rounded-lg px-3 py-2.5 text-sm text-gray-200 focus:outline-none focus:border-cyan-400 transition-colors"
            >
              {FUNCTIONALS.map(f => <option key={f} value={f}>{f}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-400 mb-1.5">
              ENCUT <span className="text-gray-600">(eV)</span>
            </label>
            <input
              type="number"
              value={encut}
              onChange={e => setEncut(Number(e.target.value))}
              min={200}
              max={900}
              step={10}
              className="w-full bg-navy-700 border border-navy-500 rounded-lg px-3 py-2.5 text-sm text-gray-200 font-mono focus:outline-none focus:border-cyan-400 transition-colors"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-400 mb-1.5">Adaptador</label>
            <select
              value={adapter}
              onChange={e => setAdapter(e.target.value)}
              className="w-full bg-navy-700 border border-navy-500 rounded-lg px-3 py-2.5 text-sm text-gray-200 focus:outline-none focus:border-cyan-400 transition-colors"
            >
              {ADAPTERS.map(a => <option key={a.value} value={a.value}>{a.label}</option>)}
            </select>
          </div>
        </div>

        {submitError && (
          <div className="mt-4 flex items-start gap-2 p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-xs text-red-400">
            <AlertTriangle size={12} className="mt-0.5 shrink-0" />
            {submitError}
          </div>
        )}

        <div className="mt-5 flex items-center gap-3">
          <button
            onClick={handleSubmit}
            disabled={submitLoading || !formula.trim()}
            className="flex items-center gap-2 px-5 py-2.5 text-sm font-semibold text-navy-900 bg-cyan-500 hover:bg-cyan-400 disabled:opacity-40 disabled:cursor-not-allowed rounded-lg transition-colors"
          >
            {submitLoading ? (
              <><RefreshCw size={14} className="animate-spin" /> Enviando…</>
            ) : (
              <><Play size={14} /> Enviar Trabajo</>
            )}
          </button>
          {nRunning > 0 && (
            <span className="text-xs text-cyan-400 flex items-center gap-1">
              <Activity size={12} className="animate-pulse" />
              {nRunning} trabajo{nRunning !== 1 ? 's' : ''} en ejecución — actualización automática cada 5 s
            </span>
          )}
        </div>
      </Card>

      {/* Job queue */}
      <Card title={`Cola de Trabajos${jobs.length > 0 ? ` — ${jobs.length}` : ''}`}>
        <div className="flex justify-end mb-3">
          <button
            onClick={fetchJobs}
            className="flex items-center gap-1 text-xs text-gray-400 hover:text-cyan-400 transition-colors"
          >
            <RefreshCw size={12} /> Actualizar
          </button>
        </div>
        {loading ? (
          <LoadingSpinner />
        ) : jobs.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-10 text-center">
            <TerminalSquare size={32} className="text-gray-600 mb-3" />
            <p className="text-sm text-gray-500">Aún no hay trabajos DFT. Envía uno arriba.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {jobs.map(job => (
              <JobRow
                key={job.id}
                job={job}
                onCancel={handleCancel}
                onRefresh={fetchJobs}
              />
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
