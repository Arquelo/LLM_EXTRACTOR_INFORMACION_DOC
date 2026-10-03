# Decisiones de validación — Constancia de Situación Fiscal

Este documento justifica qué campos son **obligatorios** en la extracción y por qué el resto permanece opcional.

## Contexto de negocio

La extracción alimenta una plataforma donde el contribuyente inicia **procesos de pago** y avanza en un flujo interno. Para poder comenzar ese flujo, la plataforma exige de forma obligatoria un conjunto mínimo de datos fiscales. El resto de la información (domicilio, actividades, regímenes, obligaciones, etc.) suele complementarse después con otros documentos y registros dentro del mismo sistema.

Por eso el esquema distingue:

1. **Obligatorios de negocio** — sin ellos no se puede arrancar el proceso.
2. **Opcionales de enriquecimiento** — útiles si aparecen, pero su ausencia no bloquea el inicio.

## Campos obligatorios

| Campo | Motivo |
|-------|--------|
| `rfc` | Identificador fiscal del contribuyente. Es el ancla del registro en la plataforma; sin RFC no hay sujeto sobre el cual iniciar pagos ni avanzar en el flujo. |
| `fecha_inicio_operaciones` | Fecha a partir de la cual el contribuyente opera ante el SAT. La plataforma la usa como dato mínimo de vigencia/contexto del registro al abrir el proceso. |
| `estatus_padron` | Estado categórico en el padrón (`ACTIVO`, `SUSPENDIDO`, `CANCELADO`, `NO LOCALIZADO`, `OTRO`). Determina si el contribuyente puede avanzar en el flujo de pagos o requiere tratamiento especial. |

Estos tres campos se validan en dos capas:

- Declaración `obligatorio=True` en el extractor (`Campo`).
- Validadores Pydantic en `extractors/schemas/constancia_situacion_fiscal.py` (vacío rechazado; `estatus_padron` acotado al enum).

Si faltan o tienen formato inválido, el resultado se clasifica como `parcial` o `fallido` según haya o no otros datos útiles.

## Campos opcionales (se extraen, no bloquean)

Dirección fiscal (`codigo_postal`, vialidad, colonia, municipio, etc.), identificación complementaria (`curp`, `id_cif`, nombre / razón social), y tablas de `actividades_economicas`, `regimenes` y `obligaciones`:

- **Sí ayudan** cuando la constancia los trae: enriquecen el perfil y reducen carga manual.
- **No son obligatorios** para iniciar el proceso de pagos: en muchos casos se completan con otros documentos o registros de la plataforma.
- Además, **no todas las constancias** incluyen esos bloques de forma completa; con el tiempo el padrón se actualiza y el registro se complementa después.

Si un opcional viene mal formado (p. ej. CURP inválida o CP de 4 dígitos), se reporta en `errores_validacion`, pero **no** se exige que esté presente.

## Relación con estados del lote

| Estado | Criterio |
|--------|----------|
| `exito` | Los tres obligatorios válidos y sin errores de formato en campos presentes. |
| `parcial` | Hay datos útiles, pero falta un obligatorio o hay formato inválido. |
| `fallido` | Error duro (lectura, Ollama, JSON) o salida sin datos útiles. |

## Referencias en código

- Esquema Pydantic: `extractors/schemas/constancia_situacion_fiscal.py` (`CAMPOS_OBLIGATORIOS`)
- Extractor / prompt / JSON Schema: `extractors/constancia_situacion_fiscal.py`
- Clasificación de estado: `extractors/base.py` → `clasificar_estado`
