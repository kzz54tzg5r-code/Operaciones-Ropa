"""V392: Semanas ISO reinician Pend. Ant. en lunes, sin doble conteo.

La lectura FIFO ya existe en el Excel publicado. Solo cuando el endpoint
devuelve cero pese a tener lotes, vuelve a agregar los lotes precalculados
por fecha y tienda autorizada. No vuelve a abrir el XLSX ni toca el disco.
"""
from __future__ import annotations
from collections import defaultdict
from functools import wraps
import math
import unicodedata


def _number(value):
    try:
        result = float(value or 0)
        return result if math.isfinite(result) else 0.0
    except (ValueError, TypeError, OverflowError):
        return 0.0


def _key(value):
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    return " ".join(normalized.encode("ascii", "ignore").decode().casefold().split())


def _belongs(row, kind, period, start="", end=""):
    day = str(row.get("date") or "")[:10]
    if not day or (start and day < start) or (end and day > end):
        return False
    # Nunca interpretar un filtro diario/semanal/mensual vacío como "histórico".
    # Si falta el valor del periodo, no se atribuyen DEV de otros días.
    if kind == "all":
        return True
    if not period:
        return False
    if kind == "day":
        return day == period
    if kind == "month":
        return day.startswith(period)
    if kind == "year":
        return day.startswith(period[:4])
    if kind == "week":
        try:
            from datetime import date
            iso = date.fromisoformat(day).isocalendar()
            return f"{iso.year}-W{iso.week:02d}" == period
        except (ValueError, TypeError):
            return False
    return False


def _pending_opening_for_period(row, kind, period, start="", end=""):
    """Saldo de apertura en día; un solo flujo de entradas en periodos largos.

    El lunes recibe el pendiente del cierre dominical como saldo inicial
    cuando la fuente publica el valor pendiente_anterior de esa tienda.
    Martes a domingo reciben su pendiente previo habitual.
    Semana/Mes/Año agregan sólo movimientos nuevos y nunca suman saldos
    de apertura diariamente; de otro modo se duplicaría el inventario.
    No edita archivos ni cambia la fuente publicada.
    """
    opening = max(_number(row.get("pendiente_anterior")), 0.0)
    selected = str(period or "")[:10] if kind == "day" else ""
    # Compatibilidad con búsquedas por rango de fecha de un solo día.
    if kind == "all" and start and start == end:
        selected = str(start)[:10]
    if selected:
        try:
            from datetime import date
            # El lunes no se reinicia el pendiente operativo: recibe el
            # saldo del domingo anterior. No repetirlo en totales semanales.
            date.fromisoformat(selected)  # valida la fecha seleccionada
            return opening
        except (ValueError, TypeError):
            return 0.0
    # Semanas ISO y periodos de varios días consolidan cada entrada
    # exactamente una vez; el arrastre no forma parte del volumen nuevo.
    if kind in ("week", "month", "year", "all"):
        return 0.0
    return opening


def _prev_sunday_week_balance(old, args, kwargs, kind, period):
    """Devuelve pendientes de cierre de la semana ISO anterior, por tienda.

    El cierre se obtiene de las mismas fuentes y alcance que Centro Operativo;
    no se suma dos veces ni se modifican registros. Si no es verificable,
    evita inventar cifras de arrastre.
    """
    if kind not in ("day", "week"):
        return {}
    try:
        from datetime import date, timedelta
        from copy import deepcopy
        target = date.fromisoformat(str(period)[:10]) if kind=="day" else date.fromisocalendar(int(str(period)[:4]),int(str(period).split("-W")[1]),1)
        if kind=="day" and target.weekday()!=0:
            return {}
        monday=target-timedelta(days=target.weekday())
        sunday=monday-timedelta(days=1)
        iso=sunday.isocalendar()
        previous_week=f"{iso.year}-W{iso.week:02d}"
        # Centro Operativo utiliza filtros nombrados; evitar pasar filtros
        # duplicados si una ruta antigua usa parámetros posicionales.
        if not ("period_type" in kwargs and "period_value" in kwargs):
            return {}
        query=dict(kwargs)
        query.update(period_type="week",period_value=previous_week,
                     start_date="",end_date="")
        earlier=deepcopy(old(*args,**query))
        if not isinstance(earlier,dict):
            return {}
        prior=reconcile_result(earlier,kind="week",period=previous_week)
        return {
            _key(row.get("store")):{
                "acondicionar":max(_number(row.get("pendiente_acondicionar")),0),
                "ubicar":max(_number(row.get("pendiente_ubicar")),0),
            }
            for row in prior.get("stores",[])
            if isinstance(row,dict) and row.get("store")
        }
    except Exception as exc:
        print(f"[V372-CARRY] cierre dominical no disponible: {type(exc).__name__}: {exc}",flush=True)
        return {}


def _allocate_sunday_work(result, source, balance, kind, period, canon=None):
    """El lunes consume primero el saldo del domingo; la semana excluye
    sólo esas piezas de sus avances nuevos, por tienda y por actividad.
    """
    if not balance or not isinstance(result,dict):
        return result
    from datetime import date
    if kind=="day":
        for row in result.get("stores",[]):
            prior=balance.get(_key(row.get("store")))
            if prior:
                row["pendiente_anterior"]=prior["acondicionar"]
                row["pendiente_anterior_ubicar"]=prior["ubicar"]
        return result
    if kind!="week":
        return result
    try:
        monday=date.fromisocalendar(int(period[:4]),int(period.split("-W")[1]),1).isoformat()
    except (ValueError,IndexError):
        return result
    monday_work=defaultdict(lambda:dict(acondicionado=0.,ubicado=0.))
    for row in (source.get("rows") or []):
        if not isinstance(row,dict) or str(row.get("date") or "")[:10]!=monday:
            continue
        st=canon(row.get("store")) if callable(canon) else row.get("store")
        slot=monday_work[_key(st)]
        slot["acondicionado"]+=max(_number(row.get("acondicionado")),0)
        slot["ubicado"]+=max(_number(row.get("ubicado")),0)
    for row in result.get("stores",[]):
        key=_key(row.get("store"))
        prior=balance.get(key)
        if prior is None:
            continue
        monday_ops=monday_work.get(key,{})
        for field,pending_field,label in (
            ("acondicionado","acondicionar","acondicionado"),
            ("ubicado","ubicar","ubicado"),
        ):
            reported=max(_number(row.get(field)),0)
            old_work=min(reported,max(_number(monday_ops.get(field)),0),
                         prior[pending_field])
            row[field]=reported-old_work
            row[f"{field}_arrastre_domingo"]=old_work
            row[f"{field}_total_realizado"]=reported
    return result


def reconcile_result(result, fifo=(), kind="all", period="", start="", end="", canon=None):
    """Usa exclusivamente recovery_by_store para determinar las tiendas visibles.

    Respeta el recorte de la API a tiendas Proyecto y las restricciones de rol
    antes de sumar; las tiendas externas jamás aparecen por efecto del rescate.
    """
    if not isinstance(result, dict):
        return result
    store_rows = result.get("stores")
    recovery_rows = result.get("recovery_by_store")
    if not isinstance(store_rows, list) or not isinstance(recovery_rows, list):
        return result

    allowed = {_key(row.get("store")): row for row in recovery_rows if row.get("store")}
    source_dev = sum(max(_number(row.get("dev_pzs")), 0) for row in recovery_rows)
    restored = False
    unseen = 0.0
    matched = 0.0

    if source_dev == 0 and allowed:
        sums = defaultdict(lambda: dict(dev_pzs=0., converted_pieces=0.,
                                         return_value=0., recovered_value=0.))
        for item in fifo or ():
            if not isinstance(item, dict) or not _belongs(item, kind, period, start, end):
                continue
            actual = canon(item.get("store")) if callable(canon) else item.get("store")
            key = _key(actual)
            dev = max(_number(item.get("dev_pzs")), 0.0)
            if key not in allowed:
                unseen += dev
                continue
            slot = sums[key]
            slot["dev_pzs"] += dev
            slot["converted_pieces"] += min(max(_number(item.get("converted_pieces")), 0.0), dev)
            slot["return_value"] += max(_number(item.get("return_value")), 0.0)
            slot["recovered_value"] += max(_number(item.get("recovered_value")), 0.0)
            matched += dev
        if matched > 0:
            for key, entry in allowed.items():
                numbers = sums.get(key) or {}
                for field in ("dev_pzs", "converted_pieces", "return_value", "recovered_value"):
                    entry[field] = numbers.get(field, 0.0)
                dev, conv = entry["dev_pzs"], entry["converted_pieces"]
                val, recovered = entry["return_value"], entry["recovered_value"]
                entry["conversion_pct"] = conv / dev * 100 if dev else 0.0
                entry["recovery_pct"] = recovered / val * 100 if val else 0.0
                entry["pending_pieces"] = max(dev - conv, 0.0)
                entry["pending_value"] = max(val - recovered, 0.0)
            restored = True

    by_store = {_key(row.get("store")): row for row in recovery_rows}
    for row in store_rows:
        matching = by_store.get(_key(row.get("store")))
        # No incluir devoluciones que no pertenecen al alcance del usuario.
        dev = max(_number((matching or {}).get("dev_pzs", row.get("dev_pzs"))), 0.0)
        # Total pzs (Detalle Operativo) = DEV del periodo + Muertos + Probador
        # + Cajas + Pendiente anterior, por tienda y periodo ya filtrados.
        # No sumar "recolectadas" otra vez: es el subtotal de los motivos.
        # Nunca usar "total_pzs"/"ingresos" como insumo de esta suma:
        # reconcile_result puede ejecutarse repetidamente sobre datos cacheados.
        # El lunes usa el saldo inicial publicado (cierre del domingo).
        # Semana/Mes/Año suman movimientos nuevos, NO aperturas diarias.
        components = ("muertos", "probador", "cajas", "pendiente_anterior")
        if any(key in row for key in components):
            row["pendiente_anterior"] = _pending_opening_for_period(
                row, kind, period, start, end
            )
        if any(key in row for key in components):
            total = dev + sum(max(_number(row.get(key)), 0.0) for key in components)
        else:
            # Compatibilidad con cargas antiguas sin desglose de motivos.
            # No inferir un desglose que la fuente no proporciona.
            legacy = row.get("recolectadas")
            if legacy is None:
                legacy = row.get("ingresos", row.get("total_pzs", 0))
            total = max(_number(legacy), 0.0)
        row["dev_pzs"] = dev
        acondicionado = max(_number(row.get("acondicionado")), 0.0)
        ubicado = max(_number(row.get("ubicado")), 0.0)
        row["total_pzs"] = total
        row["ingresos"] = total
        row["pendiente_acondicionar"] = max(total - acondicionado, 0.0)
        # La cola de Ubicado puede ser mayor a la de Acondicionado.
        # El lunes conserva el cierre dominical de cada etapa por separado.
        ubic_base=total
        if kind=="day" and str(period or "")[:10]:
            try:
                from datetime import date
                if date.fromisoformat(str(period)[:10]).weekday()==0:
                    ubic_base=total-max(_number(row.get("pendiente_anterior")),0)+max(_number(row.get("pendiente_anterior_ubicar")),0)
            except (ValueError,TypeError):
                pass
        row["pendiente_ubicar"] = max(ubic_base - ubicado, 0.0)
        row["pct_acondicionado"] = acondicionado / total * 100 if total else 0.0
        row["pct_ubicado"] = ubicado / total * 100 if total else 0.0
        # Campo heredado separado: permite conservar análisis circuito.
        row["pct_ubicado_acondicionado"] = ubicado / acondicionado * 100 if acondicionado else 0.0
    store_rows.sort(key=lambda r: (-_number(r.get("total_pzs")), str(r.get("store") or "")))
    metrics = result.setdefault("metrics", {})
    def total(field):
        return sum(_number(r.get(field)) for r in store_rows)
    for field in ("total_pzs", "dev_pzs", "ingresos", "pendiente_anterior",
                  "pendiente_acondicionar", "pendiente_ubicar", "muertos",
                  "cajas", "probador", "acondicionado", "ubicado"):
        metrics[field] = total(field)
    metrics["cambios"] = metrics["dev_pzs"]
    base = metrics["total_pzs"]
    metrics["pct_acondicionado"] = metrics["acondicionado"] / base * 100 if base else 0.0
    metrics["pct_ubicado"] = metrics["ubicado"] / base * 100 if base else 0.0
    metrics["pct_ubicado_acondicionado"] = (
        metrics["ubicado"] / metrics["acondicionado"] * 100 if metrics["acondicionado"] else 0.0
    )
    metrics["pct_procesado"] = metrics["pct_ubicado"]
    # Recuperación se agrega desde las filas YA filtradas, nunca desde
    # las tiendas ajenas al usuario ni desde los totales generales del Excel.
    rec_dev = sum(_number(r.get("dev_pzs")) for r in recovery_rows)
    converted = sum(_number(r.get("converted_pieces")) for r in recovery_rows)
    value = sum(_number(r.get("return_value")) for r in recovery_rows)
    recovered = sum(_number(r.get("recovered_value")) for r in recovery_rows)
    metrics.update(
        converted_pieces=converted, conversion_pct=converted / rec_dev * 100 if rec_dev else 0.0,
        return_value=value, recovered_value=recovered,
        recovery_pct=recovered / value * 100 if value else 0.0,
        pending_recovery_pieces=max(rec_dev - converted, 0.0),
        pending_recovery_value=max(value - recovered, 0.0),
    )
    meta = result.setdefault("recovery_source", {})
    if isinstance(meta, dict):
        meta["period_dev_pzs"] = rec_dev
        meta["fifo_restored_from_published_data"] = restored
        if restored:
            meta["source_ready"] = True
            meta["source_warning"] = ""
        elif rec_dev == 0 and unseen > 0:
            meta["source_warning"] = (
                "Existen DEV en el Excel publicado para el periodo, pero no se "
                "identificaron tiendas coincidentes dentro del alcance autorizado."
            )
    if restored:
        print(f"[V372-DEV] {kind}:{period} DEV recuperadas desde FIFO precalculado: {matched:.0f}; "
              f"fuera de alcance={unseen:.0f}", flush=True)
    return result


def install(m):
    if getattr(m, "_V372_DEV_CALCULATIONS", False):
        return
    old = m.operations

    @wraps(old)
    def operations_fixed(*args, **kwargs):
        # V367 envuelve operations(*args, **kwargs) SIN __wrapped__. Una firma
        # inspect.signature(old) da sólo "args"/"kwargs"; bind_partial coloca
        # period_type dentro de bound.arguments["kwargs"] y V372 lo veía
        # erróneamente como "all". Así llegaban al DÍA totales históricos.
        # V153 envía siempre filtros nominales. Se respetan directamente.
        params = dict(kwargs)
        if len(args) > 1:
            positional = (
                "store", "period_type", "period_value", "area", "activity",
                "start_date", "end_date", "compact", "project_only"
            )
            for field, value in zip(positional, args[1:]):
                params.setdefault(field, value)
        kind = str(params.get("period_type") or "all").strip().lower()
        period = str(params.get("period_value") or "").strip()
        start = str(params.get("start_date") or "").strip()
        end = str(params.get("end_date") or "").strip()
        result = old(*args, **kwargs)
        if not isinstance(result, dict):
            return result
        reported = result.get("recovery_by_store") or ()
        no_dev = not any(_number(r.get("dev_pzs")) > 0 for r in reported)
        fifo = ()
        # Fail closed: un periodo inválido o incompleto NO puede habilitar
        # una reconstrucción histórica, aunque sí se conserva el reporte base.
        supported = kind in ("day", "week", "month", "year", "all")
        selected = kind == "all" or bool(period)
        if no_dev and supported and selected:
            source = m.load_ops()
            fifo = m._get_recovery_fifo_rows(source) or ()
            if kind == "day" and period == "2026-10-25":
                # Diagnóstico de solo lectura (sin IDs de producto ni datos de usuarios).
                matched_items=[r for r in fifo if _belongs(r,kind,period,start,end)]
                allowed_keys={_key(r.get("store")) for r in reported if r.get("store")}
                source_keys=sorted({_key(getattr(m,"_normalize_store_value",lambda x:x)(r.get("store"))) for r in matched_items})
                print(
                    "[V386-DIAG] day=2026-10-25"
                    f" fifo_total={len(fifo)} matched_day={len(matched_items)}"
                    f" day_dev={sum(_number(r.get('dev_pzs')) for r in matched_items):.0f}"
                    f" matched_allowed_dev={sum(_number(r.get('dev_pzs')) for r in matched_items if _key(getattr(m,'_normalize_store_value',lambda x:x)(r.get('store'))) in allowed_keys):.0f}"
                    f" report_stores={len(allowed_keys)} source_stores={len(source_keys)}"
                    f" recognized_stores={', '.join(sorted(allowed_keys.intersection(source_keys)))}"
                    f" sample_source_dates={','.join(sorted({str(r.get('date')) for r in fifo})[-3:])}",
                    flush=True,
                )
        canon=getattr(m, "_normalize_store_value", None)
        # Sólo cuando existe un cierre dominical calculable se descuenta
        # la parte del trabajo del lunes que pertenecía a esa cola.
        balance=_prev_sunday_week_balance(old,args,kwargs,kind,period)
        if balance:
            result=_allocate_sunday_work(result,m.load_ops(),balance,kind,period,canon)
        return reconcile_result(result, fifo, kind, period, start, end, canon)
    m.operations = operations_fixed
    # V153 calls m.operations at request time for both main and project-scope.
    m._V372_DEV_CALCULATIONS = True
    print("[V372] DEV FIFO + pendientes desde Total Pzs instalados", flush=True)
