# Instrucción para próxima sesión con Claude

Copia y pega esto al inicio de la próxima conversación:

---

Continuamos el proyecto MatEnergy-ML. Lee la memoria del proyecto antes de responder nada:
`C:\Users\camri\.claude\projects\C--Users-camri-OneDrive-Documentos-GitHub-inteligencia-artificial-t2\memory\project_matenergy_ml.md`

## Estado al cierre de la sesión 8 (2026-06-09) — post-documentación

Todo está funcionando y desplegado. Los contenedores están corriendo con `docker compose up -d`.
La plataforma está accesible en http://localhost:3000 (frontend) y http://localhost:8000 (backend API).

### Lo que se completó en sesión 8

**Etapa 13 — DFT Job Queue Interface (completa)**

Backend:
- `BackgroundJob` ORM model + repository → mapea a tabla `background_jobs` existente
- `LocalSimulationAdapter`: ASE/EMT para metales, aproximación determinista para el resto; corre en daemon thread
- `SlurmAdapter` stub: genera POSCAR/INCAR/KPOINTS (pymatgen) + script SLURM reales
- `DFTResultIngester`: almacena resultados DFT como `MaterialProperty` en DB
- 6 endpoints: `POST /dft-jobs`, `GET /dft-jobs`, `GET /dft-jobs/{id}`, `DELETE /dft-jobs/{id}`, `POST /dft-jobs/{id}/ingest`, `GET /dft-jobs/{id}/inputs`
- `ase>=3.23.0` añadido a `requirements.txt`

Frontend:
- `DftJobsPage.tsx`: formulario de submit + cola con auto-polling (5s) + panel de resultados expandible
- Ítem "DFT Jobs" añadido al sidebar

**Sesión 7 (mismo día):**
- Narrativa SHAP automática (rule-based, sin IA generativa) en modal "Why?" de PredictionsPage

**Documentación completada en la misma sesión 8 (post-implementación):**
- `docs/api_documentation.md`: sección "DFT Jobs" completa con los 6 endpoints, esquemas de request/response, anotaciones de comportamiento
- `docs/technical_architecture.md`: `infrastructure/simulation/` añadida a sección 2.4; grupo 8 "Background Jobs" añadido al schema overview; diagrama ASCII actualizado con rama de daemon thread
- `docs/database_design.md`: sección 2.8 "Background Jobs Group" con tabla completa de columnas, esquema JSONB de payload/result, modelo de hilos
- `docs/guia_completa_plataforma.md`: sección 4.10 "DFT Jobs" con tutorial completo; ciclo de workflow actualizado; glosario ampliado (ASE, EMT, VASP, SLURM, POSCAR, HPC)
- `memory/project_matenergy_ml.md`: limpiada nota stale "Etapa 13 (stubs only)"; próximos pasos actualizados en orden

### Regla crítica de Docker

`docker compose restart` NO recarga código. Siempre reconstruir:
```bash
docker compose build backend && docker compose up -d backend
docker compose build frontend && docker compose up -d frontend
```

### Próximos pasos (en orden de prioridad)

1. **Comparador de materiales** ← SIGUIENTE
   - Ruta: `/materials/compare`
   - Seleccionar 2–3 materiales del ranking o tabla de materiales
   - Mostrar propiedades, scores ML, análisis composicional y contribuciones SHAP lado a lado
   - Útil para presentaciones académicas y decisiones de síntesis
2. **Export PDF del ranking** — PDF descargable de candidatos priorizados para presentaciones académicas
3. **Predicción de voltaje de cátodo** — requiere datos de estado litiado/delitiado o cálculo desde MP
4. **Descriptores CGCNN** — usar estructura 3D de MP para superar limitación composicional
5. **QE/GPAW workflow** — adapters adicionales para Etapa 13 (Quantum ESPRESSO, GPAW)

---

*Generado al cierre de sesión 8 (post-doc pass) — 2026-06-09*
