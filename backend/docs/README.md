# Documentación del dominio (backend/docs)

- [Decisiones de validación](decisiones_validacion.md) — por qué `rfc`, `fecha_inicio_operaciones` y `estatus_padron` son obligatorios.
- [Muestras académicas](muestras/README.md) — lote fácil / difícil versionado.

## PDFs de muestra (uso local / CLI)

Coloca aquí los PDF que quieras procesar con:

```bash
cd backend
python extract.py
```

Los `*.pdf` **no se versionan** en git (ver `.gitignore`).
Esta carpeta se crea vacía en el clon; añade tus propios archivos.
