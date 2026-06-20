"""
Report generator for MatEnergy-ML.
Generates CSV and markdown reports for rankings, model metrics, and datasets.
"""
import csv
import io
from datetime import datetime, timezone
from typing import Optional
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class ReportGenerator:
    """Generates exportable reports in CSV and Markdown format."""

    def generate_ranking_csv(
        self,
        ranking_name: str,
        items: list[dict],
        material_formulas: dict,
    ) -> bytes:
        """
        Generate CSV report for a candidate ranking.

        items: list of dicts with rank_position, material_id, candidate_score,
               priority_label, reasoning_summary
        material_formulas: {material_id: formula}
        """
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_ALL)
        writer.writerow([
            "Posición", "Fórmula", "Puntaje del Candidato", "Prioridad",
            "Puntaje de Estabilidad", "Penalización por Incertidumbre", "Fuera de Dominio",
            "Resumen del Razonamiento",
        ])
        for item in sorted(items, key=lambda x: x.get("rank_position", 999)):
            mat_id = str(item.get("material_id", ""))
            stability = item.get("stability_score")
            uncertainty = item.get("uncertainty_penalty")
            writer.writerow([
                item.get("rank_position", ""),
                material_formulas.get(mat_id, mat_id),
                f"{item.get('candidate_score', 0):.4f}",
                item.get("priority_label", ""),
                f"{stability:.4f}" if stability is not None else "",
                f"{uncertainty:.4f}" if uncertainty is not None else "",
                "Sí" if item.get("is_out_of_domain") else "No",
                item.get("reasoning_summary", ""),
            ])
        content = output.getvalue()
        logger.info("ranking_csv_generated", ranking=ranking_name, n_items=len(items))
        return content.encode("utf-8")

    def generate_model_metrics_report(self, model_name: str, metrics: list[dict]) -> str:
        """Generate a markdown report for model performance metrics."""
        now = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        lines = [
            f"# Reporte de Rendimiento del Modelo: {model_name}",
            f"Generado: {now}",
            "",
            "## Métricas",
            "",
            "| Split | Métrica | Valor |",
            "|-------|---------|-------|",
        ]
        for m in sorted(
            metrics,
            key=lambda x: (x.get("split", ""), x.get("metric_name", "")),
        ):
            lines.append(
                f"| {m.get('split', '')} | {m.get('metric_name', '')} "
                f"| {m.get('metric_value', 0):.6f} |"
            )
        lines += ["", "---", "MatEnergy-ML | Cribado de Materiales Energéticos Asistido por IA"]
        return "\n".join(lines)

    def generate_dataset_summary(
        self,
        dataset: dict,
        validation_report: Optional[dict] = None,
    ) -> str:
        """Generate markdown summary for a dataset."""
        now = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        sha256 = dataset.get("sha256_hash", "")
        sha256_preview = f"`{sha256[:16]}...`" if sha256 else "`—`"
        props = dataset.get("available_properties", [])
        props_str = ", ".join(props) if props else "—"
        lines = [
            f"# Resumen del Dataset: {dataset.get('name', 'Desconocido')}",
            f"Generado: {now}",
            "",
            f"- **SHA-256**: {sha256_preview}",
            f"- **Estado**: {dataset.get('status', '')}",
            f"- **Filas Totales**: {dataset.get('row_count', 0)}",
            f"- **Filas Válidas**: {dataset.get('valid_row_count', 0)}",
            f"- **Filas Rechazadas**: {dataset.get('rejected_row_count', 0)}",
            f"- **Propiedades Disponibles**: {props_str}",
        ]
        if validation_report:
            rules = validation_report.get("validation_rules_applied", [])
            lines += [
                "",
                "## Reporte de Validación",
                f"- Validado el: {validation_report.get('validated_at', '')}",
                f"- Reglas de validación: {', '.join(rules)}",
            ]
            warnings = validation_report.get("warnings")
            if warnings:
                lines += ["", "### Advertencias"]
                for w in warnings:
                    lines.append(f"- {w}")
        return "\n".join(lines)
