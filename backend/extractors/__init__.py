from settings.config import EXTRACTOR
from extractors.base import Arreglo, Campo, ExtractorBase
from extractors.constancia_situacion_fiscal import ConstanciaSituacionFiscal

EXTRACTORES: dict[str, type[ExtractorBase]] = {
    ConstanciaSituacionFiscal.clave: ConstanciaSituacionFiscal,
}


def obtener_extractor(clave: str | None = None) -> ExtractorBase:
    clave = clave or EXTRACTOR
    try:
        clase = EXTRACTORES[clave]
    except KeyError as exc:
        disponibles = ", ".join(sorted(EXTRACTORES))
        raise ValueError(
            f"Extractor '{clave}' no existe. Disponibles: {disponibles}"
        ) from exc
    return clase()
