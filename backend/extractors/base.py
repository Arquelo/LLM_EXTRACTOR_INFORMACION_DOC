from dataclasses import dataclass


@dataclass(frozen=True)
class Campo:
    clave: str
    descripcion: str


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
            f"- {campo.clave}: {campo.descripcion}" for campo in self.campos
        )
        bloques = []
        for arreglo in self.arreglos:
            internos = "\n".join(
                f"    - {campo.clave}: {campo.descripcion}" for campo in arreglo.campos
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
            "- Conserva el texto tal como aparece.\n"
            "- No agregues filas vacías.\n"
            "- No incluyas claves distintas a las indicadas.\n\n"
            "Forma esperada:\n"
            f"{self._ejemplo_json()}"
        )

    def esquema(self) -> dict:
        propiedades = {}
        requeridos = []

        for campo in self.campos:
            propiedades[campo.clave] = {
                "type": "string",
                "description": campo.descripcion,
            }
            requeridos.append(campo.clave)

        for arreglo in self.arreglos:
            item_props = {}
            item_req = []
            for campo in arreglo.campos:
                item_props[campo.clave] = {
                    "type": "string",
                    "description": campo.descripcion,
                }
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
