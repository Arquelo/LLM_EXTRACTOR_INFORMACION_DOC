"""Extractor de Constancia de Situación Fiscal (SAT, México).

Define el formato de extracción para ese documento: campos escalares
(identificación y domicilio) y arreglos repetibles (actividades,
regímenes y obligaciones).

La validación combina reglas de formato (`Campo`) con el esquema Pydantic
en `extractors.schemas.constancia_situacion_fiscal`.
"""

from extractors.base import (
    FORMATO_CATEGORICO,
    FORMATO_CODIGO_POSTAL,
    FORMATO_CURP,
    FORMATO_FECHA,
    FORMATO_NUMERICO,
    FORMATO_PORCENTAJE,
    FORMATO_RFC,
    Arreglo,
    Campo,
    ExtractorBase,
)
from extractors.schemas.constancia_situacion_fiscal import (
    ESTATUS_OPCIONES,
    validar_con_pydantic,
)


class ConstanciaSituacionFiscal(ExtractorBase):
    """Esquema de extracción de la Constancia de Situación Fiscal del SAT."""

    clave = "constancia_situacion_fiscal"
    tipo_documento = "Constancia de Situación Fiscal del SAT (México)"
    instrucciones = """
Extrae la identificación del contribuyente, su domicilio fiscal y las tablas de
actividades económicas, regímenes y obligaciones.
Si es persona física, llena nombre y apellidos. Si es persona moral, llena
denominacion_razon_social y deja vacíos nombre y apellidos cuando no apliquen.
Cada actividad, régimen y obligación es un elemento de su arreglo.
Omite el sello digital, la cadena original y los avisos legales del final.
Las fechas deben ir en formato dd/mm/aaaa. CURP y RFC en mayúsculas.
estatus_padron debe ser exactamente uno de: ACTIVO, SUSPENDIDO, CANCELADO,
NO LOCALIZADO, OTRO.
Campos obligatorios (mínimos de negocio para iniciar pagos): rfc,
fecha_inicio_operaciones, estatus_padron. El resto es opcional.
""".strip()

    campos = [
        Campo("rfc", "Registro Federal de Contribuyentes", FORMATO_RFC, obligatorio=True),
        Campo("curp", "CURP. Vacío si es persona moral", FORMATO_CURP),
        Campo("id_cif", "Identificador electrónico idCIF", FORMATO_NUMERICO),
        Campo("nombre", "Nombre o nombres de la persona física"),
        Campo("primer_apellido", "Primer apellido"),
        Campo("segundo_apellido", "Segundo apellido"),
        Campo("denominacion_razon_social", "Nombre, denominación o razón social completa"),
        Campo("regimen_capital", "Régimen de capital, por ejemplo S.A. de C.V."),
        Campo("nombre_comercial", "Nombre comercial"),
        Campo(
            "fecha_inicio_operaciones",
            "Fecha de inicio de operaciones",
            FORMATO_FECHA,
            obligatorio=True,
        ),
        Campo(
            "estatus_padron",
            "Estatus en el padrón (categórico)",
            FORMATO_CATEGORICO,
            obligatorio=True,
            opciones=ESTATUS_OPCIONES,
        ),
        Campo(
            "fecha_ultimo_cambio_estado",
            "Fecha de último cambio de estado",
            FORMATO_FECHA,
        ),
        Campo("lugar_fecha_emision", "Lugar y fecha de emisión de la constancia"),
        Campo(
            "codigo_postal",
            "Código postal del domicilio fiscal",
            FORMATO_CODIGO_POSTAL,
        ),
        Campo("tipo_vialidad", "Tipo de vialidad"),
        Campo("nombre_vialidad", "Nombre de la vialidad"),
        Campo("numero_exterior", "Número exterior"),
        Campo("numero_interior", "Número interior"),
        Campo("colonia", "Nombre de la colonia"),
        Campo("localidad", "Nombre de la localidad"),
        Campo("municipio", "Municipio o demarcación territorial"),
        Campo("entidad_federativa", "Entidad federativa"),
        Campo("entre_calle", "Entre calle"),
        Campo("y_calle", "Y calle"),
    ]

    arreglos = [
        Arreglo(
            "actividades_economicas",
            "Actividades económicas registradas",
            [
                Campo("orden", "Número de orden", FORMATO_NUMERICO),
                Campo("actividad", "Descripción de la actividad económica"),
                Campo("porcentaje", "Porcentaje", FORMATO_PORCENTAJE),
                Campo("fecha_inicio", "Fecha de inicio", FORMATO_FECHA),
                Campo("fecha_fin", "Fecha de fin. Vacío si no aparece", FORMATO_FECHA),
            ],
        ),
        Arreglo(
            "regimenes",
            "Regímenes fiscales",
            [
                Campo("regimen", "Nombre del régimen"),
                Campo("fecha_inicio", "Fecha de inicio", FORMATO_FECHA),
                Campo("fecha_fin", "Fecha de fin. Vacío si no aparece", FORMATO_FECHA),
            ],
        ),
        Arreglo(
            "obligaciones",
            "Obligaciones fiscales",
            [
                Campo("descripcion", "Descripción de la obligación"),
                Campo("descripcion_vencimiento", "Descripción del vencimiento"),
                Campo("fecha_inicio", "Fecha de inicio", FORMATO_FECHA),
                Campo("fecha_fin", "Fecha de fin. Vacío si no aparece", FORMATO_FECHA),
            ],
        ),
    ]

    def validar_dominio(self, datos: dict) -> list[dict]:
        return validar_con_pydantic(datos)
