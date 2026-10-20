"""Bono 2: cartera independiente por subcategoría; Bono 1 permanece intacto."""
from __future__ import annotations
import gzip
import json
import math
import os
import threading
import unicodedata
from pathlib import Path
from fastapi import Request, HTTPException

SUBCATEGORIES = ('Chamarra', 'Sudadera', 'Jeans')
_JOBS = set()
_LOCK = threading.Lock()
_SCAN = threading.BoundedSemaphore(1)


def number(value):
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def fold(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(value or '')) if not unicodedata.combining(c)).upper().strip()


def subcategory(value):
    return {'CHAMARRA': 'Chamarra', 'CHAMARRAS': 'Chamarra', 'SUDADERA': 'Sudadera',
            'SUDADERAS': 'Sudadera', 'JEANS': 'Jeans', 'JEAN': 'Jeans'}.get(fold(value))


def coverage(stock, demand):
    stock, demand = number(stock), number(demand)
    return stock / demand if stock is not None and stock >= 0 and demand is not None and demand > 0 else None


def reduction(initial, current):
    return (initial-current)/initial*100 if initial is not None and initial > 0 and current is not None else None


def read_snapshot(path):
    """Aggregate the same article grain as Bono 1, retaining SUG 7 separately.

    MAX avoids counting repeated article-level inventory for size/colour variants,
    matching the original bonus grain. A zero demand is unknown coverage, not 0 DDI.
    """
    from commercial.parsers import _iter_fast_capacity_xlsx, _normalize_capacity_source
    merged = {}
    with _SCAN:
        for raw in _iter_fast_capacity_xlsx(path, chunk_rows=1000):
            if not any(x in raw.columns for x in ('SUBCATEGORIA', 'SUBCATEGORÍA')):
                raise ValueError('Falta la columna Subcategoría en Capacidades')
            demand_col = next((x for x in ('SUG 7', 'SUGERIDO 7', 'VPD') if x in raw.columns), None)
            stock_col = next((x for x in ('__EXISTENCIA_EXACT__','EXISTENCIA','EXISTENCIA TOTAL') if x in raw.columns), None)
            if demand_col is None or stock_col is None:
                raise ValueError('Faltan SUG 7 o Existencia para comparar inventarios')
            work = _normalize_capacity_source(raw, path)
            for idx, (_, row) in enumerate(work.iterrows()):
                cat = subcategory(row.get('Subcategoría'))
                if cat is None or fold(row.get('Tipo catálogo')) != 'VIGENTE':
                    continue
                ident = str(row.get('ID_ART') or '').strip()
                store = str(row.get('Tienda') or '').strip()
                if not store or not ident.isdigit():
                    continue
                demand = number(raw.iloc[idx][demand_col]) if demand_col else None
                item = dict(store=store, id_art=ident, model=str(row.get('Modelo') or ident),
                            catalog=cat, subcategory=cat, existence=number(raw.iloc[idx][stock_col]),
                            investment=number(row.get('Inversión')), sug7=demand)
                key = (fold(store), ident)
                old = merged.get(key)
                if old:
                    if old['catalog'] != cat:
                        raise ValueError(f'Subcategorías contradictorias para ID {ident} en {store}')
                    for field in ('existence', 'investment', 'sug7'):
                        values = [v for v in (old[field], item[field]) if v is not None]
                        old[field] = max(values) if values else None
                else:
                    merged[key] = item
    for item in merged.values():
        item['ddi'] = coverage(item['existence'], item['sug7'])
    return list(merged.values())


def select_targets(rows):
    """Bono 1 selection, replacing catalog by subcategory. Investment is no score."""
    grouped = {}
    for row in rows:
        grouped.setdefault((fold(row['store']), row['catalog']), []).append(row)
    result = []
    for values in grouped.values():
        investments = [x['investment'] for x in values if x['investment'] is not None]
        mean = sum(investments)/len(investments) if investments else None
        result.extend(x for x in values if x['ddi'] is not None and x['ddi'] > 90
                      and mean is not None and x['investment'] is not None and x['investment'] > mean)
    return result


def compare_rows(initial, current):
    lookup = {(fold(x['store']), x['id_art']): x for x in current or []}
    result = []
    for row in initial:
        cur = lookup.get((fold(row['store']), row['id_art']))
        final = cur['existence'] if cur else None
        fixed = coverage(final, row['sug7'])
        current_ddi = cur['ddi'] if cur else None
        result.append(dict(store=row['store'], id_art=row['id_art'], model=row['model'],
                           catalog=row['catalog'], subcategory=row['catalog'],
                           initial_existence=row['existence'], current_existence=final,
                           initial_sug7=row['sug7'], current_sug7=cur['sug7'] if cur else None,
                           initial_ddi=row['ddi'], current_ddi=current_ddi, fixed_ddi=fixed,
                           ddi_reduction_pct=reduction(row['ddi'], fixed),
                           initial_investment=row['investment'], current_investment=cur['investment'] if cur else None,
                           investment_reduction_pct=reduction(row['investment'], cur['investment'] if cur else None),
                           deliveries=None, deliveries_status='Sin fuente de movimientos del periodo',
                           comparison_status='Comparable' if fixed is not None else 'Sin registro final comparable',
                           ddi_reduced=fixed is not None and fixed < row['ddi']))
    return result


def inventory(rows):
    def total(key):
        vals = [x.get(key) for x in rows]
        return sum(vals) if vals and all(v is not None for v in vals) else None
    initial = coverage(total('initial_existence'), total('initial_sug7'))
    current = coverage(total('current_existence'), total('current_sug7'))
    fixed = coverage(total('current_existence'), total('initial_sug7'))
    return dict(initial_ddi=initial, current_ddi=current, fixed_ddi=fixed,
                ddi_reduction_pct=reduction(initial, fixed), initial_existence=total('initial_existence'),
                current_existence=total('current_existence'), initial_investment=total('initial_investment'),
                current_investment=total('current_investment'), deliveries=None,
                initial_models=len(rows), current_models=None)


def store_metric(source, rows):
    cats = []
    values = []
    for cat in SUBCATEGORIES:
        xs = [x for x in rows if x['catalog'] == cat]
        comparable = bool(xs) and all(x['fixed_ddi'] is not None for x in xs)
        pct = 100*sum(x['ddi_reduced'] for x in xs)/len(xs) if comparable else None
        if pct is not None:
            values.append(pct)
        cats.append(dict(catalog=cat, models=len(xs), ddi_reduction_pct=pct, inventory=inventory(xs)))
    # Average of populated subcategories, as in Bono 1; no partial denominator.
    active = [c for c in cats if c['models']]
    ddi = sum(values)/len(values) if active and len(values) == len(active) else None
    sale = number(source.get('sales_pct'))
    att = number(source.get('attendance_pct'))
    ready = sale is not None and ddi is not None and att is not None and not source.get('attendance_provisional')
    score = sum(min(100, max(0, v))*w for v, w in ((sale,.5),(ddi,.3),(att,.2)) if v is not None)
    reasons = []
    if sale is None: reasons.append('Ventas o meta pendientes')
    if ddi is None: reasons.append('DDI sin comparación completa')
    if source.get('attendance_provisional') or att is None: reasons.append('Asistencia pendiente')
    return dict(source, ddi_pct=ddi, score=round(score, 2), score_ready=ready, rank=None,
                missing_sources=reasons, catalogs=cats, inventory=inventory(rows), target_models=len(rows))


def install(m):
    if getattr(m, '_V340_BONUS2', False): return
    root = Path(m.DATA_ROOT)/'cache_bonus2_subcategories_v340'
    root.mkdir(parents=True, exist_ok=True)

    def dataset(entry):
        path = m.resolve_entry_path(entry)
        if not path.is_file(): return {'status':'error', 'error':'No se encuentra el archivo de Capacidades', 'rows':[]}
        import hashlib
        key = hashlib.sha256((str(entry.get('id'))+str(path.stat().st_mtime_ns)+str(path.stat().st_size)).encode()).hexdigest()
        dest = root/(key+'.json.gz')
        if dest.is_file():
            with gzip.open(dest, 'rt', encoding='utf-8') as f: return json.load(f)
        def build():
            try: data = {'status':'ready', 'rows':read_snapshot(path)}
            except Exception as exc: data = {'status':'error', 'error':str(exc)[:250], 'rows':[]}
            try:
                temp = dest.with_suffix('.tmp')
                with gzip.open(temp, 'wt', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, allow_nan=False)
                os.replace(temp, dest)
            finally:
                with _LOCK: _JOBS.discard(key)
        with _LOCK:
            if key not in _JOBS:
                _JOBS.add(key)
                threading.Thread(target=build, daemon=True, name='b2-subcategories').start()
        return {'status':'pending', 'rows':[]}

    def payload(request, month='', store='Compañía'):
        actor = m.require_user(request)
        handler = next(r.endpoint for r in m.app.routes if getattr(r,'path','') == '/api/operation/sales-bonus-v293')
        base = handler(request=request, month=month, store='' if store=='Compañía' else store)
        allowed = list(base.get('stores') or [])
        if store != 'Compañía' and store not in allowed: raise HTTPException(403,'No puedes consultar esta tienda')
        restricted = str(actor.get('role') or '').lower() in ('tienda','colaborador','colaborador_operativo','colaborador_lenceria')
        selected = base['selected_store'] if restricted else store
        month = base['month']
        pick = m._sales_bonus_opening_capacity_v293(month)
        initial = dataset(pick[2]) if pick else {'status':'missing','rows':[]}
        dates = dict(base.get('source_dates') or {})
        dates['opening_capacity'] = pick[0].isoformat() if pick else ''
        dates['opening_capacity_id'] = str(pick[2].get('id') or '') if pick else ''
        current_id = str(dates.get('current_capacity_id') or '')
        manifest_path = Path(m.COMMERCIAL_DATA_ROOT)/'manifest.json'
        manifest = json.loads(manifest_path.read_text()) if manifest_path.is_file() else {}
        entries = list(manifest.get('capacities') or []) + list(manifest.get('bonus_initial_capacity_entries') or [])
        entry = next((e for e in entries if str(e.get('id'))==current_id), None)
        current = dataset(entry) if entry and pick and current_id != str(pick[2].get('id')) else {'status':'missing','rows':[]}
        targets = select_targets(initial['rows'])
        all_details = compare_rows(targets, current['rows'] if current['status']=='ready' else None)
        canonical = {fold(name): name for name in allowed}
        all_details = [dict(x,store=canonical[fold(x['store'])]) for x in all_details if fold(x['store']) in canonical]
        ranking = [store_metric(r, [x for x in all_details if fold(x['store'])==fold(r['store'])]) for r in base.get('ranking') or []]
        ranking.sort(key=lambda r:(not r['score_ready'], -r['score'], r['store']))
        rank = 0
        for order, row in enumerate(ranking,1):
            if row['score_ready']: rank += 1; row['rank'] = rank
            row['display_order'] = order
        visible = [r for r in ranking if selected=='Compañía' or r['store']==selected]
        details = [x for x in all_details if x['store'] in allowed and (selected=='Compañía' or fold(x['store'])==fold(selected))]
        def average(key, complete=False):
            vals = [number(r.get(key)) for r in visible if not complete or r['score_ready']]
            vals = [v for v in vals if v is not None]
            return sum(vals)/len(vals) if vals else None
        sales_rows = [r for r in visible if number(r.get('sales_pct')) is not None]
        goal = sum(r.get('sales_goal') or 0 for r in sales_rows)
        sales = 100*sum(r.get('sales_actual') or 0 for r in sales_rows)/goal if goal>0 else None
        inv = inventory(details)
        legacy = dict(sales_pct=sales, ddi_pct=average('ddi_pct'), attendance_pct=average('attendance_pct'),
                      attendance_provisional_stores=sum(bool(r.get('attendance_provisional')) for r in visible),
                      legacy_score_avg=average('score',True), stores_with_score=sum(r['score_ready'] for r in visible), inventory=inv)
        errors = [d.get('error') for d in (initial,current) if d.get('error')]
        pending = any(d['status']=='pending' for d in (initial,current))
        return dict(version='V340-B2-SUBCATEGORIES', b2_subcategories=True, month=month, months=base.get('months'),
                    stores=allowed if restricted else ['Compañía',*allowed], selected_store=selected,
                    can_admin=base.get('can_edit_attendance',False), can_edit_attendance=False,
                    source_dates=dates, processing=dict(capacity=pending,sales=(base.get('processing') or {}).get('sales',False)),
                    source_error=' · '.join(errors), b2_status='pending' if pending else 'error' if errors else initial['status'],
                    summary=dict(sales_pct=sales, inventory=inv, stores_total=len(visible)), legacy_components=legacy,
                    selected=dict(formula='50% ventas · 30% DDI por subcategoría · 20% asistencia. Inversión informativa.'),
                    ranking=visible, bonus2_rows=visible, details=details if selected!='Compañía' else [],
                    subcategories=list(SUBCATEGORIES), weights=dict(sales=50,ddi=30,attendance=20))

    @m.app.get('/api/bonuses-b2-v340')
    def endpoint(request:Request, month:str='', store:str='Compañía'):
        return payload(request,month,store)
    m._v340_bonus2_payload = payload
    m._V340_BONUS2 = True
