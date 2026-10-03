"""Tests de Pydantic, clasificación de estado y reporte de lote."""

from __future__ import annotations

from extractors.constancia_situacion_fiscal import ConstanciaSituacionFiscal
from extractors.schemas.constancia_situacion_fiscal import validar_con_pydantic
from extraction.report import construir_reporte
from extraction.results import construir_resultado


def test_pydantic_rechaza_estatus_invalido() -> None:
    errores = validar_con_pydantic(
        {
            "rfc": "XAXX010101000",
            "fecha_inicio_operaciones": "01/01/2020",
            "estatus_padron": "VIGENTE",
            "codigo_postal": "01000",
        }
    )
    assert errores
    assert any("estatus" in e["campo"] for e in errores)


def test_pydantic_acepta_obligatorios() -> None:
    assert (
        validar_con_pydantic(
            {
                "rfc": "XAXX010101000",
                "fecha_inicio_operaciones": "01/01/2020",
                "estatus_padron": "ACTIVO",
            }
        )
        == []
    )


def test_pydantic_codigo_postal_es_opcional() -> None:
    assert (
        validar_con_pydantic(
            {
                "rfc": "XAXX010101000",
                "fecha_inicio_operaciones": "01/01/2020",
                "estatus_padron": "ACTIVO",
                "codigo_postal": "",
            }
        )
        == []
    )


def test_clasificar_parcial_vs_exito() -> None:
    ext = ConstanciaSituacionFiscal()
    datos = ext.organizar(
        {
            "rfc": "XAXX010101000",
            "fecha_inicio_operaciones": "01/01/2020",
            "estatus_padron": "ACTIVO",
            "codigo_postal": "01000",
            "curp": "MALA",
        }
    )
    errores = ext.validar(datos)
    assert errores
    assert ext.clasificar_estado(datos, errores) == "parcial"
    assert ext.clasificar_estado(datos, []) == "exito"
    assert ext.clasificar_estado({}, [], error_duro="sin texto") == "fallido"


def test_reporte_tasas() -> None:
    ext = ConstanciaSituacionFiscal()
    resultados = [
        construir_resultado(
            archivo="a.txt",
            extractor=ext,
            datos={"rfc": "X"},
            estado="exito",
        ),
        construir_resultado(
            archivo="b.txt",
            extractor=ext,
            datos={"rfc": "X"},
            estado="parcial",
            error="parcial",
        ),
        construir_resultado(
            archivo="c.txt",
            extractor=ext,
            datos={},
            estado="fallido",
            error="fallo",
        ),
    ]
    reporte = construir_reporte(resultados, extractor=ext.clave, modelo="demo")
    assert reporte["resumen"]["total"] == 3
    assert reporte["resumen"]["exitosos"] == 1
    assert reporte["resumen"]["parciales"] == 1
    assert reporte["resumen"]["fallidos"] == 1
    assert reporte["resumen"]["tasa_exito"] == 33.33
