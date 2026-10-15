"""V329 · Reemplazo de Bonos 3–6: cuatro esquemas de remuneración simulada.

Mantiene intactos los endpoints y reglas de Bonos 1 y 2.
DDI determina el incentivo; variación de inversión es INFORMATIVA.
Asistencia es siempre exactamente el 20% de la bolsa objetivo; el
80% restante cubre ventas/DDI. La asistencia disponible es por TIENDA,
no una validación personal de nómina.

Los montos y meta DDI son parámetros de simulación, nunca pagos autorizados.
"""
from __future__ import annotations

import math
from fastapi import Request, HTTPException

MODEL_NAMES = {
    3: "Puntos ponderados · 50/30/20",
    4: "Objetivos independientes · 50/30/20",
    5: "Ventas con multiplicador DDI · 80/20",
    6: "Resultado colectivo de tienda · 48/32/20",
}
MODEL_METHODS = {
    3: "weighted_points",
    4: "independent_bands",
    5: "ddi_sales_multiplier",
    6: "collective_store",
}
FORMULAS = {
    3: "Bolsa base × [mínimo(100%, 50%×cumplimiento ventas + 30%×cumplimiento DDI) + 20%×asistencia].",
    4: "Bolsa base × [50%×tramo ventas + 30%×tramo DDI + 20%×asistencia]. Tramos: <80%=0, 80–<100%=50%, 100–<110%=100%, ≥110%=120%.",
    5: "Bolsa base × [mínimo(100%, 80%×cumplimiento ventas×multiplicador DDI) + 20%×asistencia]. Multiplicador DDI: 1.10 si cumple la meta; si no 1.00.",
    6: "Bolsa base × [mínimo(100%, 80%×(60%×cumplimiento ventas + 40%×cumplimiento DDI)) + 20%×asistencia].",
}


def finite(value):
    try:
        if value is None or value == "":
            return None
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def between(value, low, high):
    return max(low, min(high, float(value)))


def tier(compliance):
    if compliance < 80:
        return 0.0
    if compliance < 100:
        return .5
    if compliance < 110:
        return 1.0
    return 1.2


def evaluate_model(bonus_no, sales_pct, ddi_reduction_pct, attendance_pct, ddi_target_pct=10.0, base_amount=1000.0):
    """Pure deterministic simulator. None means a required source is missing."""
    b = int(bonus_no)
    if b not in MODEL_NAMES:
        raise ValueError("El simulador V329 solamente admite Bonos 3 a 6")
    target = finite(ddi_target_pct)
    amount = finite(base_amount)
    if target is None or target <= 0 or amount is None or amount < 0:
        raise ValueError("La meta DDI debe ser positiva y la bolsa no negativa")
    sales = finite(sales_pct)
    ddi = finite(ddi_reduction_pct)
    att = finite(attendance_pct)
    if sales is None or ddi is None or att is None:
        return None
    sales_compliance = between(sales / 100.0, 0, 1.5)
    ddi_compliance = between(ddi / target, 0, 1.5)
    attendance_ratio = between(att / 100.0, 0, 1)
    if b == 3:
        commercial = min(1.0, .5 * sales_compliance + .3 * ddi_compliance)
    elif b == 4:
        commercial = .5 * tier(sales_compliance * 100) + .3 * tier(ddi_compliance * 100)
    elif b == 5:
        commercial = min(1.0, .8 * sales_compliance * (1.1 if ddi_compliance >= 1 else 1.0))
    else:
        commercial = min(1.0, .8 * (.6 * sales_compliance + .4 * ddi_compliance))
    attendance = .2 * attendance_ratio  # La asistencia NUNCA recibe multiplicadores.
    pct = (commercial + attendance) * 100.0
    return {
        "commercial_pct": round(commercial * 100, 4),
        "attendance_bonus_pct": round(attendance * 100, 4),
        "compliance_pct": round(pct, 4),
        "sales_compliance_pct": round(sales_compliance * 100, 4),
        "ddi_compliance_pct": round(ddi_compliance * 100, 4),
        "estimated_amount": round(amount * pct / 100, 2),
        "attendance_amount": round(amount * attendance, 2),
        "commercial_amount": round(amount * commercial, 2),
    }


def install(m):
    if getattr(m, "_V329_EMPLOYEE_BONUS_MODELS", False):
        return
    def endpoint(path):
        for route in m.app.routes:
            if getattr(route, "path", None) == path and "GET" in getattr(route, "methods", set()):
                return route.endpoint
        raise HTTPException(503, "No está disponible la base de Bonos")

    @m.app.get("/api/bonuses-v329")
    def bonuses_v329(
        request: Request,
        month: str = "",
        store: str = "Compañía",
        bonus: int = 3,
        ddi_target: float = 10.0,
        base_amount: float = 1000.0,
    ):
        actor = m.require_user(request)
        b = int(bonus)
        if b not in MODEL_NAMES:
            raise HTTPException(400, "Bono inválido para nuevos modelos")
        if not 0.1 <= ddi_target <= 100 or not 0 <= base_amount <= 100000:
            raise HTTPException(400, "Parámetros de simulación fuera de rango")
        # Ambos endpoints preservan ámbito de actor, rol y periodo ya existentes.
        base = endpoint("/api/operation/sales-bonus-v293")(
            request=request, month=month, store="" if store == "Compañía" else store
        )
        dates = dict(base.get("source_dates") or {})
        opening = dates.get("opening_capacity_id") or dates.get("opening_capacity")
        current = dates.get("current_capacity_id") or dates.get("current_capacity")
        cuts_ready = bool(opening and current and opening != current and not (base.get("processing") or {}).get("capacity"))
        stores = list(base.get("stores") or [])
        actor_store = str(actor.get("store") or "")
        requested = str(store or "Compañía")
        if actor_store in stores and str(actor.get("role") or "").lower() in (
            "tienda", "colaborador", "colaborador_operativo", "colaborador_lenceria"
        ):
            requested = actor_store
        selected_store = requested if requested in stores else "Compañía"
        rows = []
        for record in base.get("ranking") or []:
            store_name = str(record.get("store") or "")
            if store_name not in stores:
                continue
            inv = dict(record.get("inventory") or {})
            sales_pct = finite(record.get("sales_pct"))
            ddi_pct = finite(inv.get("ddi_reduction_pct")) if cuts_ready else None
            att_pct = finite(record.get("attendance_pct"))
            result = evaluate_model(b, sales_pct, ddi_pct, att_pct, ddi_target, base_amount)
            ready = result is not None
            initial_inv = finite(inv.get("initial_investment"))
            current_inv = finite(inv.get("current_investment")) if cuts_ready else None
            delta_inv = round(initial_inv - current_inv, 2) if initial_inv is not None and current_inv is not None else None
            rows.append({
                "bonus_no": b, "store": store_name, "sales_pct": sales_pct,
                "attendance_reference": att_pct, "attendance_scored": True,
                "inventory": inv,
                "eligible": bool(ready and result["compliance_pct"] > 0),
                "ready": ready, "classification": "Simulación calculada" if ready else "Datos incompletos",
                "indicator": result["compliance_pct"] if ready else None,
                "score": result["compliance_pct"] if ready else None,
                "level": None,
                "extra": {
                    "ddi_reduction_pct": ddi_pct,
                    "ddi_compliance_pct": result["ddi_compliance_pct"] if ready else (round(between(ddi_pct / ddi_target,0,1.5)*100,2) if ddi_pct is not None else None),
                    "sales_compliance_pct": result["sales_compliance_pct"] if ready else sales_pct,
                    "capital_variation_mxn": delta_inv,
                    "estimated_amount": result["estimated_amount"] if ready else None,
                    "commercial_pct": result["commercial_pct"] if ready else None,
                    "attendance_bonus_pct": result["attendance_bonus_pct"] if ready else None,
                },
            })
        rows.sort(key=lambda x: (not x["ready"], -(x["indicator"] or 0), x["store"]))
        for rank, row in enumerate(rows, 1):
            row["rank"] = rank if row["ready"] else None
        selected = next((r for r in rows if r["store"] == selected_store), None)
        raw = next((r for r in (base.get("ranking") or []) if r.get("store") == selected_store), None)
        ready_rows = [r for r in rows if r["ready"]]
        sales_rows = [r for r in (base.get("ranking") or []) if finite(r.get("sales_pct")) is not None]
        total_goal = sum(finite(x.get("sales_goal")) or 0 for x in sales_rows)
        total_actual = sum(finite(x.get("sales_actual")) or 0 for x in sales_rows)
        sales_company = round(total_actual / total_goal * 100, 2) if total_goal > 0 else None
        def average(vals):
            vals = [x for x in vals if x is not None]
            return round(sum(vals) / len(vals), 2) if vals else None
        def sum_known(vals):
            vals = [x for x in vals if x is not None]
            return round(sum(vals), 2) if vals else None
        inv_rows = [r["inventory"] for r in rows]
        summary_inv = {
            k: (sum_known([finite(v.get(k)) for v in inv_rows]) if "investment" in k or "existence" in k else average([finite(v.get(k)) for v in inv_rows]))
            for k in ("initial_ddi","current_ddi","ddi_reduction_pct","initial_investment","current_investment","initial_existence","current_existence")
        }
        summary = {
            "sales_pct": sales_company,
            "stores_total": len(rows), "stores_enabled": len(ready_rows),
            "stores_sales_100": sum(1 for r in rows if r["sales_pct"] is not None and r["sales_pct"] >= 100),
            "attendance_reference": average([r["attendance_reference"] for r in rows]),
            "score_avg": average([r["indicator"] for r in ready_rows]),
            "inventory": summary_inv,
        }
        if selected:
            summary.update({
                "sales_pct": selected["sales_pct"], "stores_total": 1,
                "stores_enabled": 1 if selected["ready"] else 0,
                "attendance_reference": selected["attendance_reference"],
                "score_avg": selected["indicator"], "inventory": selected["inventory"],
            })
        investment = summary["inventory"]
        inv_initial = finite(investment.get("initial_investment"))
        inv_current = finite(investment.get("current_investment")) if cuts_ready else None
        summary["capital_variation_mxn"] = round(inv_initial - inv_current, 2) if inv_initial is not None and inv_current is not None else None

        return {
            "version": "V329-EMPLOYEE-BONUS-SIMULATION",
            "month": base.get("month"), "months": base.get("months") or [],
            "bonus_no": b, "can_admin": str(actor.get("role") or "").lower() in ("admin", "superadmin"),
            "stores": ["Compañía"] + stores,
            "selected_store": selected_store,
            "summary": summary, "ranking": rows, "selected": selected,
            "details": (base.get("selected") or {}).get("details") or [] if selected_store != "Compañía" else [],
            "catalogs": ((base.get("selected") or {}).get("ddi") or {}).get("catalogs") or [],
            "source_dates": dates, "processing": base.get("processing") or {},
            "model": {
                "name": MODEL_NAMES[b], "method": MODEL_METHODS[b], "formula": FORMULAS[b],
                "sales_weight_pct": 50 if b in (3, 4) else (80 if b == 5 else 48),
                "ddi_weight_pct": 30 if b in (3, 4) else (0 if b == 5 else 32),
                "attendance_weight_pct": 20, "ddi_target_pct": ddi_target,
                "base_amount": base_amount, "cut_comparable": cuts_ready,
                "simulation_only": True, "individual_attendance_required": True,
            },
            "is_v329": True,
            "rules": {
                "sales": "Ventas vs meta; los sobrecumplimientos tienen límites por metodología.",
                "ddi": "Reducción DDI = (DDI inicial - DDI actual)/DDI inicial × 100. Cumplimiento = reducción real / meta DDI simulada.",
                "investment": "La inversión solamente muestra la variación neta entre cortes; NO aporta puntos ni pago.",
                "attendance": "20% del bono objetivo, proporcional a asistencia elegible individual. El dato de tienda NO sustituye registro individual.",
                "cost": "Importes de ejemplo; no son montos de nómina ni obligaciones de pago.",
            },
        }

    m._V329_EMPLOYEE_BONUS_MODELS = True
    print("[V329] Bono 3–6: ponderado, independiente, multiplicador y colectivo; asistencia 20%; inversión informativa.", flush=True)
