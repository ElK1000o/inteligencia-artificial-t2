import type { ShapContribution } from '../components/charts/ShapWaterfallChart';

export interface NarrativeFactor {
  label: string;
  featureValue: string;
  shapContribution: string;
}

export interface ShapNarrativeData {
  headline: string;
  verdictLevel: 'positive' | 'warning' | 'negative' | 'neutral';
  /** Section header for features pushing the target value UP */
  pushingUpLabel: string;
  /** Section header for features pushing the target value DOWN */
  pushingDownLabel: string;
  /** Top features with positive SHAP value (push prediction higher) */
  pushingUpFactors: NarrativeFactor[];
  /** Top features with negative SHAP value (push prediction lower) */
  pushingDownFactors: NarrativeFactor[];
  baselineNote: string;
  scientificContext: string;
  /** Whether a lower predicted value is better for this target (e.g. energy_above_hull) */
  lowerIsBetter: boolean;
}

// Human-readable labels for known descriptor names
const FEATURE_LABELS: Record<string, string> = {
  frac_Li: 'Fracción de litio',
  frac_Cu: 'Fracción de cobre',
  frac_O: 'Fracción de oxígeno',
  frac_S: 'Fracción de azufre',
  frac_P: 'Fracción de fósforo',
  frac_Fe: 'Fracción de hierro',
  frac_Mn: 'Fracción de manganeso',
  frac_Co: 'Fracción de cobalto',
  frac_Ni: 'Fracción de níquel',
  frac_transition_metals: 'Fracción de metales de transición',
  n_elements: 'Número de elementos',
  avg_atomic_number: 'Número atómico medio',
  avg_atomic_mass: 'Masa atómica media (u)',
  avg_electronegativity: 'Electronegatividad media',
  electronegativity_range: 'Rango de electronegatividad',
  avg_atomic_radius: 'Radio atómico medio (Å)',
  max_electronegativity: 'Electronegatividad máxima',
  min_electronegativity: 'Electronegatividad mínima',
  std_electronegativity: 'Varianza de electronegatividad',
  max_atomic_mass: 'Masa elemental máxima (u)',
  min_atomic_mass: 'Masa elemental mínima (u)',
  mean_atomic_mass: 'Masa atómica media (u)',
  std_atomic_mass: 'Varianza de masa atómica',
  max_atomic_radius: 'Radio atómico máximo (Å)',
  min_atomic_radius: 'Radio atómico mínimo (Å)',
  std_atomic_radius: 'Varianza de radio atómico',
  max_atomic_number: 'Número atómico máximo',
  min_atomic_number: 'Número atómico mínimo',
  std_atomic_number: 'Varianza de número atómico',
  density: 'Densidad (g/cm³)',
  volume_per_atom: 'Volumen por átomo (ų)',
  space_group: 'Número de grupo espacial',
};

function toLabel(name: string): string {
  return FEATURE_LABELS[name] ?? name.replace(/_/g, ' ');
}

function fmtVal(v: number): string {
  const a = Math.abs(v);
  if (a === 0) return '0';
  if (a < 0.001) return v.toExponential(2);
  if (a < 0.1) return v.toFixed(4);
  if (a < 10) return v.toFixed(3);
  return v.toFixed(1);
}

function fmtShap(v: number, unit: string): string {
  const sign = v >= 0 ? '+' : '';
  const unitSuffix = unit ? ` ${unit}` : '';
  return `${sign}${v.toFixed(4)}${unitSuffix}`;
}

interface TargetConfig {
  unit: string;
  lowerIsBetter: boolean;
  getVerdict(val: number): { text: string; level: 'positive' | 'warning' | 'negative' | 'neutral' };
  pushingUpLabel: string;
  pushingDownLabel: string;
  context: string;
}

const CONFIGS: Record<string, TargetConfig> = {
  energy_above_hull: {
    unit: 'eV/atom',
    lowerIsBetter: true,
    getVerdict(v) {
      if (v <= 0.025) return { text: 'altamente estable — EAH ≤ 0.025 eV/atom', level: 'positive' };
      if (v <= 0.05)  return { text: 'candidato termodinámicamente estable — EAH ≤ 0.05 eV/atom', level: 'positive' };
      if (v <= 0.1)   return { text: 'marginalmente inestable — puede existir como fase metaestable', level: 'warning' };
      if (v <= 0.3)   return { text: 'moderadamente inestable — propenso a descomposición bajo condiciones de operación', level: 'negative' };
      return { text: 'termodinámicamente inestable — alto riesgo de descomposición', level: 'negative' };
    },
    pushingUpLabel: 'Factores que aumentan la inestabilidad (elevan la EAH)',
    pushingDownLabel: 'Factores que favorecen la estabilidad (reducen la EAH)',
    context:
      'La energía sobre el hull convexo (EAH) mide la estabilidad termodinámica respecto a todas las fases competidoras en el mismo sistema químico. Valores más bajos indican mayor estabilidad. El umbral de 0.05 eV/atom es el criterio estándar de screening computacional para sintetizabilidad — los materiales por encima de él tienden a descomponerse en fases más estables. Esta predicción se deriva de descriptores composicionales y datos de entrenamiento calibrados con DFT, no de un cálculo termodinámico directo.',
  },
  formation_energy_per_atom: {
    unit: 'eV/atom',
    lowerIsBetter: true,
    getVerdict(v) {
      if (v < -2.0) return { text: 'formación fuertemente exotérmica — energética altamente favorable', level: 'positive' };
      if (v < -0.5) return { text: 'energía de formación moderadamente exotérmica', level: 'positive' };
      if (v < 0)    return { text: 'débilmente exotérmica — formación marginalmente favorable', level: 'warning' };
      return { text: 'formación endotérmica — el compuesto puede no formarse espontáneamente a partir de los elementos', level: 'negative' };
    },
    pushingUpLabel: 'Factores que reducen la favorabilidad de formación (elevan la ΔHf)',
    pushingDownLabel: 'Factores que mejoran la favorabilidad de formación (reducen la ΔHf)',
    context:
      'La energía de formación por átomo (ΔHf) cuantifica la energía liberada cuando el compuesto se forma a partir de sus elementos constituyentes en condiciones estándar. Valores más negativos reflejan una vía de síntesis termodinámicamente más favorable. Cabe señalar que la energía de formación por sí sola no determina la sintetizabilidad — también deben considerarse las barreras cinéticas y las fases competidoras.',
  },
  band_gap: {
    unit: 'eV',
    lowerIsBetter: false,
    getVerdict(v) {
      if (v < 0.05) return { text: 'metálico o semimetálico — band gap electrónico despreciable', level: 'neutral' };
      if (v < 0.5)  return { text: 'semiconductor de band gap estrecho — potencial electrodo o conductor mixto', level: 'positive' };
      if (v < 3.0)  return { text: 'semiconductor — relevante para aplicaciones fotoelectroquímicas y optoelectrónicas', level: 'positive' };
      if (v < 5.0)  return { text: 'semiconductor de band gap ancho — candidato a electrolito sólido (suprime la conductividad electrónica)', level: 'positive' };
      return { text: 'aislante de band gap ancho', level: 'neutral' };
    },
    pushingUpLabel: 'Factores que aumentan el band gap',
    pushingDownLabel: 'Factores que reducen el band gap',
    context:
      'El band gap rige la conductividad electrónica. Los electrodos de batería típicamente requieren materiales metálicos o de band gap estrecho para conducir electrones junto con los iones Li⁺. Los electrolitos en estado sólido necesitan un band gap amplio (> 3 eV) para bloquear la corriente electrónica mientras mantienen la conductividad iónica. Los band gaps de DFT calculados con el funcional GGA están sistemáticamente subestimados en 30–50% respecto a los valores experimentales — trata las predicciones como cotas inferiores.',
  },
  is_stable: {
    unit: '',
    lowerIsBetter: false,
    getVerdict(v) {
      // predicted_value may be class label (0/1) or raw model score
      const isStable = v >= 0.5;
      if (isStable)  return { text: 'clasificado como termodinámicamente estable', level: 'positive' };
      return { text: 'clasificado como termodinámicamente inestable', level: 'negative' };
    },
    pushingUpLabel: 'Factores que respaldan la clasificación estable',
    pushingDownLabel: 'Factores que respaldan la clasificación inestable',
    context:
      'La estabilidad se predice como una clasificación binaria derivada del umbral de energía sobre el hull (EAH ≤ 0.05 eV/atom). Los valores SHAP positivos empujan hacia la clase "estable"; los negativos empujan hacia "inestable". Este clasificador fue entrenado con el mismo dataset derivado de DFT y hereda sus sesgos composicionales y limitaciones de dominio.',
  },
};

const FALLBACK_CONFIG = CONFIGS.energy_above_hull;
const TOP_N = 5;

export function generateShapNarrative(
  formula: string,
  targetProperty: string,
  predictedValue: number,
  baseValue: number,
  contributions: ShapContribution[],
): ShapNarrativeData {
  const cfg = CONFIGS[targetProperty] ?? FALLBACK_CONFIG;
  const { unit, lowerIsBetter } = cfg;

  const { text: verdictText, level: verdictLevel } = cfg.getVerdict(predictedValue);
  const propLabel = targetProperty.replace(/_/g, ' ');
  const valStr = `${fmtVal(predictedValue)}${unit ? ' ' + unit : ''}`;
  const headline = `${formula} — ${propLabel} predicho: ${valStr}. ${verdictText.charAt(0).toUpperCase() + verdictText.slice(1)}.`;

  const sorted = [...contributions].sort((a, b) => Math.abs(b.shap_value) - Math.abs(a.shap_value));

  const makeFactor = (c: ShapContribution): NarrativeFactor => ({
    label: toLabel(c.feature),
    featureValue: fmtVal(c.feature_value),
    shapContribution: fmtShap(c.shap_value, unit),
  });

  const pushingUpFactors = sorted.filter((c) => c.shap_value > 0).slice(0, TOP_N).map(makeFactor);
  const pushingDownFactors = sorted.filter((c) => c.shap_value < 0).slice(0, TOP_N).map(makeFactor);

  const baselineNote = `Línea base del modelo: ${fmtVal(baseValue)}${unit ? ' ' + unit : ''} (predicción promedio sobre el conjunto de entrenamiento). La suma de todas las contribuciones SHAP desde esta línea base produce el valor predicho mostrado arriba.`;

  return {
    headline,
    verdictLevel,
    pushingUpLabel: cfg.pushingUpLabel,
    pushingDownLabel: cfg.pushingDownLabel,
    pushingUpFactors,
    pushingDownFactors,
    baselineNote,
    scientificContext: cfg.context,
    lowerIsBetter,
  };
}
