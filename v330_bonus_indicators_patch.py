"""V330 · Seguimiento de indicadores reales para Bonos 3, 4, 5 y 6.

Usa exclusivamente la cartera del corte inicial mensual conservado en V293/V321,
comparada con el último reporte procesado de Capacidades de Análisis Comercial.
No hay simuladores, bonos monetarios ni datos generados como sustitutos.
Bonos 1/2 continúan en sus endpoints y pantallas previos sin cambios.
"""
from __future__ import annotations

from fastapi import HTTPException, Request

MODEL_NAMES = {
    3: "Puntos ponderados",
    4: "Objetivos independientes",
    5: "Multiplicador por DDI",
    6: "Resultado colectivo por tienda",
}
DESIGNS = {3: "3.2", 4: "4.1", 5: "5.2", 6: "6.1"}
WEIGHTS = {
    3: {"sales": 50, "ddi": 30, "attendance": 20},
    4: {"sales": 50, "ddi": 30, "attendance": 20},
    5: {"sales": 80, "ddi": None, "attendance": 20},
    6: {"sales": 48, "ddi": 32, "attendance": 20},
}


def finite(value):
    try:
        if value is None or value == "":
            return None
        import math
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def clamp(value, lo=0.0, hi=100.0):
    return min(hi, max(lo, float(value)))


def tier(pct):
    """Escalones aprobados anteriormente para el componente de ventas o DDI."""
    if pct < 80:
        return 0.0
    if pct < 100:
        return 0.5
    if pct < 110:
        return 1.0
    return 1.2


def ddi_improvement(catalogs, comparable):
    """Porcentaje de modelos del mismo corte inicial con DDI menor en el corte actual.

    Inversión no participa en el numerador, denominador o puntaje.
    No imputa N/D = 0 cuando falta el segundo corte.
    """
    if not comparable:
        return {"pct": None, "models": 0, "improved": 0}
    rows = list(catalogs or [])
    total = sum(max(0, int(finite(x.get("models")) or 0)) for x in rows)
    improved = sum(max(0, int(finite(x.get("ddi_reduced_models")) or 0)) for x in rows)
    if total <= 0:
        return {"pct": None, "models": 0, "improved": 0}
    improved = min(total, improved)
    return {"pct": round(100.0 * improved / total, 2), "models": total, "improved": improved}


def evaluate_store(bonus_no, sales_pct, ddi_models_pct, attendance_pct):
    """Store-only reference score, never an employee bonus/payment."""
    bonus = int(bonus_no)
    if bonus not in MODEL_NAMES:
        raise ValueError("Bono fuera de rango 3–6")
    values = (finite(sales_pct), finite(ddi_models_pct), finite(attendance_pct))
    if any(x is None for x in values):
        return None
    sale, ddi, attendance = values
    sv = clamp(sale, 0, 150) / 100
    dv = clamp(ddi, 0, 100) / 100
    av = clamp(attendance, 0, 100) / 100
    if bonus == 3:
        sales_part = min(75, 50 * sv)
        ddi_part = 30 * dv
        commercial = min(100, sales_part + ddi_part)
    elif bonus == 4:
        sales_part = 50 * tier(clamp(sale, 0, 150))
        ddi_part = 30 * tier(clamp(ddi, 0, 100))
        commercial = sales_part + ddi_part
    elif bonus == 5:
        # No hay meta de DDI autorizada para activar 1.10.
        # Mostrar avances reales, NO autorizar multiplicador ni puntaje global.
        return None
    else:
        sales_part = min(72, 48 * sv)
        ddi_part = 32 * dv
        commercial = min(100, sales_part + ddi_part)
    attendance_part = 20 * av
    return {
        "sales_points": round(sales_part, 2),
        "ddi_points": round(ddi_part, 2),
        "attendance_points": round(attendance_part, 2),
        "evaluation_points": round(commercial + attendance_part, 2),
        "reference_only": True,
    }


def aggregate(rows, comparable):
    """Company panorama: sales weighted by goals, DDI by model counts."""
    def average(key):
        vals = [finite(r.get(key)) for r in rows]
        vals = [v for v in vals if v is not None]
        return round(sum(vals) / len(vals), 2) if vals else None

    # La falta de ventas NO equivale a 0% y no debe diluir el macro.
    known_sales = [r for r in rows if finite(r.get("sales_pct")) is not None
                   and (finite(r.get("sales_goal")) or 0) > 0]
    sum_goal = sum(finite(r.get("sales_goal")) or 0 for r in known_sales)
    sum_sales = sum(finite(r.get("sales_actual")) or 0 for r in known_sales)
    sales_pct = round(sum_sales / sum_goal * 100, 2) if sum_goal > 0 else None
    eligible = [r for r in rows if r.get("ddi_models_pct") is not None]
    total_models = sum(r["ddi_models"] for r in eligible)
    improved_models = sum(r["ddi_improved_models"] for r in eligible)
    ddi_models_pct = round(100 * improved_models / total_models, 2) if total_models > 0 else None
    inventory = {}
    for key in ("initial_investment", "current_investment", "initial_existence", "current_existence"):
        vals = [finite(r["inventory"].get(key)) for r in eligible]
        vals = [v for v in vals if v is not None]
        inventory[key] = round(sum(vals), 2) if vals and comparable else None
    weighted_rows = [r for r in eligible if r.get("initial_ddi") is not None and r.get("current_ddi") is not None]
    denom = sum(r["ddi_models"] for r in weighted_rows)
    if denom:
        inventory["initial_ddi"] = round(sum(r["initial_ddi"] * r["ddi_models"] for r in weighted_rows) / denom, 2)
        inventory["current_ddi"] = round(sum(r["current_ddi"] * r["ddi_models"] for r in weighted_rows) / denom, 2)
    else:
        inventory["initial_ddi"] = None
        inventory["current_ddi"] = None
    init_ddi, cur_ddi = inventory["initial_ddi"], inventory["current_ddi"]
    inventory["ddi_reduction_pct"] = round(100 * (init_ddi - cur_ddi) / init_ddi, 2) if init_ddi is not None and init_ddi > 0 and cur_ddi is not None else None
    init_inv, cur_inv = inventory["initial_investment"], inventory["current_investment"]
    inventory["capital_variation_mxn"] = round(init_inv - cur_inv, 2) if init_inv is not None and cur_inv is not None else None
    return {
        "sales_pct": sales_pct,
        "attendance_reference": average("attendance_reference"),
        "ddi_models_pct": ddi_models_pct,
        "ddi_models": total_models if comparable else 0,
        "ddi_improved_models": improved_models if comparable else 0,
        "inventory": inventory,
        "stores_total": len(rows),
        "stores_with_ddi": len(eligible),
    }


def install(m):
    if getattr(m, "_V330_BONUS_INDICATORS", False):
        return
    def base_endpoint():
        for route in getattr(m.app, "routes", []):
            if getattr(route, "path", None) == "/api/operation/sales-bonus-v293" and "GET" in getattr(route, "methods", ()):
                return route.endpoint
        raise HTTPException(503, "La fuente de Bonos no está disponible")

    @m.app.get("/api/bonuses-v330")
    def bonuses_v330(request: Request, month: str = "", store: str = "Compañía", bonus: int = 3):
        actor = m.require_user(request)
        b = int(bonus)
        if b not in MODEL_NAMES:
            raise HTTPException(400, "Bono inválido: utilice 3, 4, 5 o 6")
        role = str(actor.get("role") or "").lower()
        requested = str(store or "Compañía")
        base = base_endpoint()(request=request, month=month, store="" if requested == "Compañía" else requested)
        available = list(base.get("stores") or [])
        if role in ("tienda", "colaborador_operativo", "colaborador_lenceria"):
            assigned = str(actor.get("store") or "")
            # Los permisos reales de V293 son autoridad; nunca ampliar ese ámbito.
            requested = next((s for s in available if s.casefold() == assigned.casefold()), available[0] if len(available) == 1 else "")
        selected_store = requested if requested in available else "Compañía"
        dates = dict(base.get("source_dates") or {})
        processing = dict(base.get("processing") or {})
        opening_id = dates.get("opening_capacity_id")
        latest_id = dates.get("current_capacity_id")
        comparable = bool(
            opening_id and latest_id and opening_id != latest_id
            and not processing.get("capacity")
        )
        rows = []
        for source in base.get("ranking") or []:
            st = str(source.get("store") or "")
            if st not in available:
                continue
            inv = dict(source.get("inventory") or {})
            ddi = ddi_improvement(source.get("catalogs"), comparable)
            sale = finite(source.get("sales_pct"))
            attendance = finite(source.get("attendance_pct"))
            initial_inv = finite(inv.get("initial_investment")) if comparable else None
            current_inv = finite(inv.get("current_investment")) if comparable else None
            initial_ddi = finite(inv.get("initial_ddi")) if ddi["pct"] is not None else None
            current_ddi = finite(inv.get("current_ddi")) if ddi["pct"] is not None else None
            ddi_reduction_pct = round(100 * (initial_ddi - current_ddi) / initial_ddi, 2) if initial_ddi is not None and initial_ddi > 0 and current_ddi is not None else None
            components = evaluate_store(b, sale, ddi["pct"], attendance)
            status = "Esperando corte inicial" if not opening_id else "Esperando corte de avance" if opening_id == latest_id or not latest_id else "Procesando Capacidades" if processing.get("capacity") else "Sin modelos elegibles" if ddi["pct"] is None else "Falta venta / meta" if sale is None else "Falta asistencia" if attendance is None else "Evaluación de tienda" if b != 5 else "Meta DDI por autorizar"
            rows.append({
                "store": st, "bonus_no": b, "sales_pct": sale,
                "sales_actual": finite(source.get("sales_actual")),
                "sales_goal": finite(source.get("sales_goal")),
                "attendance_reference": attendance,
                "attendance_scope": "tienda",
                "ddi_models_pct": ddi["pct"],
                "ddi_models": ddi["models"],
                "ddi_improved_models": ddi["improved"],
                "ddi_reduction_pct": ddi_reduction_pct,
                "initial_ddi": initial_ddi, "current_ddi": current_ddi,
                "inventory": {
                    "initial_ddi": initial_ddi, "current_ddi": current_ddi,
                    "ddi_reduction_pct": ddi_reduction_pct,
                    "initial_investment": initial_inv, "current_investment": current_inv,
                    "capital_variation_mxn": round(initial_inv - current_inv, 2) if initial_inv is not None and current_inv is not None else None,
                },
                "score": components["evaluation_points"] if components else None,
                "components": components,
                "ready": bool(components),
                "classification": status,
                "reference_only": True,
            })
        rows.sort(key=lambda x: (x["score"] is None, -(x["score"] or 0), -(x["ddi_models_pct"] or 0), x["store"]))
        for index, row in enumerate(rows, 1):
            row["rank"] = index if row.get("ddi_models_pct") is not None else None
        chosen = next((r for r in rows if r["store"] == selected_store), None)
        overview = aggregate(rows, comparable) if selected_store == "Compañía" else {
            "sales_pct": chosen["sales_pct"], "attendance_reference": chosen["attendance_reference"],
            "ddi_models_pct": chosen["ddi_models_pct"], "ddi_models": chosen["ddi_models"],
            "ddi_improved_models": chosen["ddi_improved_models"], "inventory": chosen["inventory"],
            "stores_total": 1, "stores_with_ddi": 1 if chosen["ddi_models_pct"] is not None else 0,
        } if chosen else aggregate([], comparable)
        return {
            "version": "V330-REAL-INDICATORS", "is_v330": True, "bonus_no": b,
            "month": base.get("month"), "months": base.get("months") or [],
            "selected_store": selected_store, "stores": ["Compañía"] + available if role not in ("tienda","colaborador_operativo","colaborador_lenceria") else available,
            "can_admin": role in ("admin","superadmin"),
            "summary": overview, "ranking": rows, "selected": chosen,
            "source_dates": dates, "processing": processing,
            "details": (base.get("selected") or {}).get("details") or [] if selected_store != "Compañía" else [],
            "catalogs": ((base.get("selected") or {}).get("ddi") or {}).get("catalogs") or [],
            "model": {
                "name": MODEL_NAMES[b], "design": DESIGNS[b], "weights": WEIGHTS[b],
                "cut_comparable": comparable,
                "attendance_scope": "tienda (referencial)",
                "investment_is_informational": True,
                "multiplier_needs_authorized_ddi_target": b == 5,
            },
            "rules": {
                "source": "Corte inicial mensual guardado + último corte procesado en Análisis Comercial; misma cartera por tienda e ID_ART.",
                "ddi": "Indicador DDI = modelos con DDI menor al inicial / modelos del corte inicial; también se reporta reducción del DDI promedio.",
                "investment": "Variación neta de inversión = inversión del corte inicial − inversión del corte actual; informativo, no genera puntos.",
                "attendance": "20% del esquema; dato capturado por tienda es informativo y NO equivale a asistencia individual.",
                "payment": "No se calculan, visualizan ni autorizan importes de bono.",
                "multiplier": "Bono 5 muestra los indicadores reales; la activación del multiplicador requiere una meta de DDI autorizada.",
            },
        }

    m._V330_BONUS_INDICATORS = True
    print("[V330] Bono 3–6: vistas de indicadores reales, sin simulación ni pagos.", flush=True)
