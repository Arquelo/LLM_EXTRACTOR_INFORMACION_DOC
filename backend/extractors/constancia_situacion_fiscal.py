"""Extractor de Constancia de Situación Fiscal (SAT, México).

Define el formato de extracción para ese documento: campos escalares
(identificación y domicilio) y arreglos repetibles (actividades,
regímenes y obligaciones).

`ExtractorBase` usa `instrucciones`, `campos` y `arreglos` para armar el
prompt del LLM y el JSON Schema de salida. Regístralo en
`extractors.EXTRACTORES` bajo la clave `constancia_situacion_fiscal`.
"""

from extractors.base import (
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


class ConstanciaSituacionFiscal(ExtractorBase):
    """Esquema de extracción de la Constancia de Situación Fiscal del SAT.

    - `campos`: datos únicos del contribuyente y su domicilio fiscal.
    - `arreglos`: tablas que se repiten (actividades, regímenes, obligaciones).

    Las instrucciones distinguen persona física (nombre/apellidos) de
    persona moral (`denominacion_razon_social`) y piden omitir sello,
    cadena original y avisos legales del final del PDF.
    """

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
""".strip()

    # Identificación del contribuyente y datos generales del padrón.
    campos = [
        Campo("rfc", "Registro Federal de Contribuyentes", FORMATO_RFC),
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
        ),
        Campo("estatus_padron", "Estatus en el padrón"),
        Campo(
            "fecha_ultimo_cambio_estado",
            "Fecha de último cambio de estado",
            FORMATO_FECHA,
        ),
        Campo("lugar_fecha_emision", "Lugar y fecha de emisión de la constancia"),
        # Domicilio fiscal.
        Campo(
            "codigo_postal",
            "Código postal del domicilio fiscal",
            FORMATO_CODIGO_POSTAL,
        ),
        Campo("tipo_vialidad", "Tipo de vialidad"),
        Campo("nombre_vialidad", "Nombre de la vialidad"),
        Campo("numero_exterior", "Número exterior"),
        Campo("numero_interior", "Número interior"),
        Campo("colonia", "Nombre o clave numérica de la colonia", FORMATO_NUMERICO),
        Campo("localidad", "Nombre de la localidad"),
        Campo("municipio", "Municipio o demarcación territorial"),
        Campo("entidad_federativa", "Entidad federativa"),
        Campo("entre_calle", "Entre calle"),
        Campo("y_calle", "Y calle"),
    ]

    # Tablas del documento: cada fila es un elemento del arreglo.
    arreglos = [
        Arreglo(
            "actividades_economicas",
            "Actividades económicas registradas",
            [
                Campo("orden", "Número de orden", FORMATO_NUMERICO),
                Campo("actividad", "Descripción de la actividad económica"),
                Campo("porcentaje", "Porcentaje", FORMATO_PORCENTAJE),
                Campo("fecha_inicio", "Fecha de inicio", FORMATO_FECHA),
                Campo(
                    "fecha_fin",
                    "Fecha de fin. Vacío si no aparece",
                    FORMATO_FECHA,
                ),
            ],
        ),
        Arreglo(
            "regimenes",
            "Regímenes fiscales",
            [
                Campo("regimen", "Nombre del régimen"),
                Campo("fecha_inicio", "Fecha de inicio", FORMATO_FECHA),
                Campo(
                    "fecha_fin",
                    "Fecha de fin. Vacío si no aparece",
                    FORMATO_FECHA,
                ),
            ],
        ),
        Arreglo(
            "obligaciones",
            "Obligaciones fiscales",
            [
                Campo("descripcion", "Descripción de la obligación"),
                Campo("descripcion_vencimiento", "Descripción del vencimiento"),
                Campo("fecha_inicio", "Fecha de inicio", FORMATO_FECHA),
                Campo(
                    "fecha_fin",
                    "Fecha de fin. Vacío si no aparece",
                    FORMATO_FECHA,
                ),
            ],
        ),
    ]
