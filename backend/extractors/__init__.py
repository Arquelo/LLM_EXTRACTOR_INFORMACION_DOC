from settings.config import EXTRACTOR
from extractors.base import Arreglo, Campo, ExtractorBase
from extractors.constancia_situacion_fiscal import ConstanciaSituacionFiscal

# Para otro documento (por ejemplo calificaciones): crea la clase, regístrala aquí
# y cambia EXTRACTOR en .env. El prompt y el orden de los datos viajan con la clase.
EXTRACTORES: dict[str, type[ExtractorBase]] = {
    ConstanciaSituacionFiscal.clave: ConstanciaSituacionFiscal,
}


def obtener_extractor(clave: str | None = None) -> ExtractorBase:
    clave = clave or EXTRACTOR
    try:
        clase = EXTRACTORES[clave]
    except KeyError as exc:
        disponibles = ", ".join(sorted(EXTRACTORES))
        raise SystemExit(
            f"Extractor '{clave}' no existe. Disponibles: {disponibles}"
        ) from exc
    return clase()
