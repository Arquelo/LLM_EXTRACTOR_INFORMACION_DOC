"""Base de extractores: campos, formatos, prompt, esquema JSON y validación."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Formato:
    """Regla de formato para un campo (prompt, JSON Schema y validación)."""

    clave: str
    etiqueta: str
    patron: str
    ejemplo: str


# Claves reutilizables al declarar Campo(..., formato=...).
FORMATO_NUMERICO = "numerico"
FORMATO_CODIGO_POSTAL = "codigo_postal"
FORMATO_CURP = "curp"
FORMATO_RFC = "rfc"
FORMATO_FECHA = "fecha"
FORMATO_PORCENTAJE = "porcentaje"

FORMATOS: dict[str, Formato] = {
    FORMATO_NUMERICO: Formato(
        FORMATO_NUMERICO,
        "solo dígitos (0-9)",
        r"^\d+$",
        "123",
    ),
    FORMATO_CODIGO_POSTAL: Formato(
        FORMATO_CODIGO_POSTAL,
        "código postal de 5 dígitos",
        r"^\d{5}$",
        "01000",
    ),
    FORMATO_CURP: Formato(
        FORMATO_CURP,
        "CURP mexicana de 18 caracteres",
        r"^[A-Z][AEIOUX][A-Z]{2}\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])[HM]"
        r"[A-Z]{2}[B-DF-HJ-NP-TV-Z]{3}[A-Z0-9]\d$",
        "GARC850101HDFRRN09",
    ),
    FORMATO_RFC: Formato(
        FORMATO_RFC,
        "RFC mexicano (12 o 13 caracteres)",
        r"^[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}$",
        "XAXX010101000",
    ),
    FORMATO_FECHA: Formato(
        FORMATO_FECHA,
        "fecha dd/mm/aaaa",
        r"^(0[1-9]|[12]\d|3[01])/(0[1-9]|1[0-2])/\d{4}$",
        "15/03/2019",
    ),
    FORMATO_PORCENTAJE: Formato(
        FORMATO_PORCENTAJE,
        "porcentaje numérico (entero o decimal)",
        r"^\d+([.,]\d+)?$",
        "100",
    ),
}


@dataclass(frozen=True)
class Campo:
    clave: str
    descripcion: str
    formato: str | None = None

    def formato_def(self) -> Formato | None:
        if not self.formato:
            return None
        try:
            return FORMATOS[self.formato]
        except KeyError as exc:
            raise ValueError(
                f"Formato '{self.formato}' desconocido en campo '{self.clave}'. "
                f"Disponibles: {', '.join(sorted(FORMATOS))}"
            ) from exc


@dataclass(frozen=True)
class Arreglo:
    clave: str
    descripcion: str
    campos: list[Campo]


class ExtractorBase:
    """Formato de extracción. Los arreglos de campos generan el prompt y la salida."""

    clave = ""
    tipo_documento = ""
    instrucciones = ""
    campos: list[Campo] = []
    arreglos: list[Arreglo] = []

    def prompt(self) -> str:
        lineas_campos = "\n".join(
            f"- {campo.clave}: {self._descripcion_con_formato(campo)}"
            for campo in self.campos
        )
        bloques = []
        for arreglo in self.arreglos:
            internos = "\n".join(
                f"    - {campo.clave}: {self._descripcion_con_formato(campo)}"
                for campo in arreglo.campos
            )
            bloques.append(f"- {arreglo.clave}: {arreglo.descripcion}\n{internos}")

        return (
            "Eres un extractor de datos de documentos. "
            "Responde únicamente con un objeto JSON válido, sin markdown ni texto extra.\n\n"
            f"Tipo de documento: {self.tipo_documento}\n\n"
            f"{self.instrucciones.strip()}\n\n"
            "Campos (cadenas de texto; usa cadena vacía si el dato no aparece):\n"
            f"{lineas_campos}\n\n"
            "Arreglos (listas de objetos; usa [] si no hay filas):\n"
            f"{chr(10).join(bloques)}\n\n"
            "Reglas:\n"
            "- No inventes datos que no estén en el documento.\n"
            "- Conserva el texto tal como aparece, salvo cuando el formato lo exija "
            "(fechas dd/mm/aaaa, CURP/RFC en mayúsculas, etc.).\n"
            "- Si un campo declara formato, el valor debe cumplirlo o ir vacío.\n"
            "- No agregues filas vacías.\n"
            "- No incluyas claves distintas a las indicadas.\n\n"
            "Forma esperada:\n"
            f"{self._ejemplo_json()}"
        )

    def esquema(self) -> dict:
        propiedades = {}
        requeridos = []

        for campo in self.campos:
            propiedades[campo.clave] = self._propiedad_schema(campo)
            requeridos.append(campo.clave)

        for arreglo in self.arreglos:
            item_props = {}
            item_req = []
            for campo in arreglo.campos:
                item_props[campo.clave] = self._propiedad_schema(campo)
                item_req.append(campo.clave)
            propiedades[arreglo.clave] = {
                "type": "array",
                "description": arreglo.descripcion,
                "items": {
                    "type": "object",
                    "properties": item_props,
                    "required": item_req,
                },
            }
            requeridos.append(arreglo.clave)

        return {
            "type": "object",
            "properties": propiedades,
            "required": requeridos,
        }

    def organizar(self, datos: dict) -> dict:
        if not isinstance(datos, dict):
            datos = {}

        resultado = {}
        for campo in self.campos:
            resultado[campo.clave] = _texto(datos.get(campo.clave))

        for arreglo in self.arreglos:
            filas = datos.get(arreglo.clave, [])
            if isinstance(filas, dict):
                filas = [filas]
            if not isinstance(filas, list):
                filas = []

            normalizadas = []
            for fila in filas:
                if not isinstance(fila, dict):
                    continue
                fila_norm = {
                    campo.clave: _texto(fila.get(campo.clave))
                    for campo in arreglo.campos
                }
                if any(fila_norm.values()):
                    normalizadas.append(fila_norm)
            resultado[arreglo.clave] = normalizadas

        return resultado

    def validar(self, datos: dict) -> list[dict]:
        """Verifica formatos tras la respuesta del modelo.

        Devuelve una lista de errores (vacía si todo es válido). Cada error
        incluye `campo`, `valor` y `motivo`. No lanza excepciones.
        """
        if not isinstance(datos, dict):
            return [
                {
                    "campo": "",
                    "valor": "",
                    "motivo": "La respuesta del modelo no es un objeto.",
                }
            ]

        errores: list[dict] = []

        for campo in self.campos:
            valor = _texto(datos.get(campo.clave))
            motivo = _motivo_formato(campo, valor)
            if motivo:
                errores.append(
                    {"campo": campo.clave, "valor": valor, "motivo": motivo}
                )

        for arreglo in self.arreglos:
            filas = datos.get(arreglo.clave, [])
            if not isinstance(filas, list):
                errores.append(
                    {
                        "campo": arreglo.clave,
                        "valor": str(filas),
                        "motivo": "Debe ser una lista de objetos.",
                    }
                )
                continue
            for indice, fila in enumerate(filas):
                if not isinstance(fila, dict):
                    errores.append(
                        {
                            "campo": f"{arreglo.clave}[{indice}]",
                            "valor": str(fila),
                            "motivo": "Cada elemento del arreglo debe ser un objeto.",
                        }
                    )
                    continue
                for campo in arreglo.campos:
                    valor = _texto(fila.get(campo.clave))
                    motivo = _motivo_formato(campo, valor)
                    if motivo:
                        errores.append(
                            {
                                "campo": f"{arreglo.clave}[{indice}].{campo.clave}",
                                "valor": valor,
                                "motivo": motivo,
                            }
                        )

        return errores

    def _descripcion_con_formato(self, campo: Campo) -> str:
        fmt = campo.formato_def()
        if not fmt:
            return campo.descripcion
        return (
            f"{campo.descripcion} "
            f"[formato: {fmt.etiqueta}; ejemplo: {fmt.ejemplo}; vacío si no aplica]"
        )

    def _propiedad_schema(self, campo: Campo) -> dict:
        prop: dict = {
            "type": "string",
            "description": self._descripcion_con_formato(campo),
        }
        fmt = campo.formato_def()
        if fmt:
            # Cadena vacía siempre permitida; si hay valor, debe cumplir el patrón.
            prop["pattern"] = f"^$|{fmt.patron}"
        return prop

    def _ejemplo_json(self) -> str:
        import json

        ejemplo = {campo.clave: "" for campo in self.campos}
        for arreglo in self.arreglos:
            ejemplo[arreglo.clave] = [
                {campo.clave: "" for campo in arreglo.campos}
            ]
        return json.dumps(ejemplo, ensure_ascii=False, indent=2)


def _texto(valor) -> str:
    if valor is None:
        return ""
    return str(valor).strip()


def _motivo_formato(campo: Campo, valor: str) -> str | None:
    """None si el valor es válido (incluye vacío)."""
    if valor == "":
        return None
    fmt = campo.formato_def()
    if not fmt:
        return None
    # CURP/RFC suelen venir en minúsculas; normalizamos solo para chequear.
    candidato = valor.upper() if campo.formato in {FORMATO_CURP, FORMATO_RFC} else valor
    if re.fullmatch(fmt.patron, candidato):
        return None
    return (
        f"El valor no cumple el formato '{fmt.etiqueta}' "
        f"(ejemplo: {fmt.ejemplo})."
    )
