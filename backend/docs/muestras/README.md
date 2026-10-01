# Muestras de prueba (versionadas)

Textos sintéticos realistas de Constancia de Situación Fiscal para el lote académico.

| Archivo | Tipo | Propósito |
|---------|------|-----------|
| `01_facil_persona_fisica.txt` | Fácil | Persona física completa |
| `02_facil_persona_moral.txt` | Fácil | Persona moral |
| `03_facil_activo_completo.txt` | Fácil | Todos los bloques |
| `04_dificil_incompleto.txt` | Difícil | Obligatorios faltantes / formatos raros |
| `05_dificil_ambiguo.txt` | Difícil | Ambigüedad + enum inválido |
| `06_facil_suspendido.txt` | Fácil | Estatus categórico SUSPENDIDO |

Ejecutar el lote desde la API (`POST /api/extract/muestras`) o:

```bash
cd backend
python -c "from extraction import procesar_muestras; procesar_muestras()"
```
