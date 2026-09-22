"""V190 · Checklist Lencería + perfiles colaboradores.

- Colaborador operativo: conserva el flujo de captura de productividad existente.
- Colaborador de lencería: entra directo a Checklist Lencería de su tienda.
- Captura manual Top 10 por familia y compara contra ranking real de capacidades.
"""
from __future__ import annotations

from datetime import datetime
import math
import re
import unicodedata

import pandas as pd


def install(m):
    if getattr(m, "_V190_LINGERIE_CHECKLIST", False):
        return

    from fastapi import HTTPException, Request
    from fastapi.responses import HTMLResponse

    ROLE_LINGERIE = "colaborador_lenceria"
    ROLE_OPERATION = "colaborador_operativo"
    EDIT_ROLES = ("superadmin", "admin", ROLE_LINGERIE)
    VIEW_ROLES = ("superadmin", "admin", "director", "tienda", ROLE_LINGERIE)

    m.ROLES = tuple(dict.fromkeys(tuple(m.ROLES) + (ROLE_LINGERIE, ROLE_OPERATION, "colaborador")))
    m.ROLE_LABELS["colaborador"] = "Colaborador operativo"
    m.ROLE_LABELS[ROLE_OPERATION] = "Colaborador operativo"
    m.ROLE_LABELS[ROLE_LINGERIE] = "Colaborador de lencería"
    m.REPORT_TABS.setdefault("commercial.lingerie_checklist", "Checklist lencería")

    with m.db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS lingerie_champion_checklist(
            period TEXT NOT NULL,
            store TEXT NOT NULL,
            family TEXT NOT NULL,
            rank INTEGER NOT NULL,
            entry_value TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL,
            updated_by TEXT NOT NULL,
            PRIMARY KEY(period,store,family,rank)
        )""")
        con.execute("CREATE INDEX IF NOT EXISTS ix_lingerie_checklist_store_period ON lingerie_champion_checklist(store,period)")
        # Unificar el nombre del perfil operativo nuevo sin perder cuentas creadas
        # con el rol histórico "colaborador".
        con.execute("UPDATE users SET role=? WHERE role='colaborador'", (ROLE_OPERATION,))

    old_require_user = m.require_user

    def require_user_v190(request, roles=None):
        user = old_require_user(request, roles)
        if str(user.get("role") or "") == ROLE_LINGERIE and roles is None:
            path = str(request.url.path or "")
            allowed = (
                "/api/lingerie-checklist",
                "/api/me/change-password",
                "/api/me/complete-temporary-password",
            )
            if path.startswith("/api/") and not any(path.startswith(prefix) for prefix in allowed):
                raise HTTPException(403, "El perfil Colaborador de lencería sólo tiene acceso a Checklist Lencería")
        return user

    m.require_user = require_user_v190

    def norm(value):
        text = unicodedata.normalize("NFD", str(value or ""))
        text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
        return " ".join(text.casefold().strip().split())

    def canonical_store(value):
        fn = getattr(m, "_canonical_capacity_store_name", None)
        return str(fn(value) if callable(fn) else value or "").strip()

    def allowed_stores(actor):
        if actor.get("role") in ("tienda", ROLE_LINGERIE):
            assigned = canonical_store(actor.get("store") or "")
            return [assigned] if assigned else []
        stores = [canonical_store(x) for x in (m.store_names(True) or list(getattr(m, "PROJECT_STORES", [])))]
        out = []
        seen = set()
        for store in stores:
            key = norm(store)
            if store and key not in seen:
                seen.add(key)
                out.append(store)
        return out

    def resolve_store(actor, requested):
        stores = allowed_stores(actor)
        if actor.get("role") in ("tienda", ROLE_LINGERIE):
            if not stores:
                raise HTTPException(409, "El usuario no tiene tienda asignada")
            return stores[0]
        wanted = canonical_store(requested)
        if wanted and any(norm(x) == norm(wanted) for x in stores):
            return next(x for x in stores if norm(x) == norm(wanted))
        if stores:
            return stores[0]
        raise HTTPException(409, "No hay tiendas activas configuradas")

    _catalog_cache = {}

    def lingerie_scope(period, store):
        periods = m._capacity_period_options(period or "")
        selected = period if period and period in periods else (periods[0] if periods else "")
        frame = m._capacity_frame_for_period(selected)
        if frame is None or frame.empty:
            return selected, pd.DataFrame()

        work = m._capacity_scope_v45(frame, store, "Todas", "Todos")
        if work is None or work.empty:
            return selected, pd.DataFrame()

        mask = pd.Series(False, index=work.index)
        for col in ("Área reporte", "Sección", "Categoría", "Ubicación detalle", "Pasillo operativo"):
            if col not in work.columns:
                continue
            values = work[col].fillna("").astype(str).map(norm)
            mask = mask | values.str.contains("lenceria", regex=False)

        return selected, work.loc[mask]

    def family_series(work):
        if work is None or work.empty:
            return pd.Series(dtype="object")
        if "Subcategoría" in work.columns:
            fam = work["Subcategoría"].fillna("").astype(str).str.strip()
        else:
            fam = pd.Series("", index=work.index)
        if "Categoría" in work.columns:
            fallback = work["Categoría"].fillna("").astype(str).str.strip()
            empty = fam.isin(["", "nan", "None"])
            fam = fam.mask(empty, fallback)
        fam = fam.replace({"": "Sin familia", "nan": "Sin familia", "None": "Sin familia"})
        return fam

    def ranking_metric(period, work):
        is_month = bool(re.fullmatch(r"\d{4}-\d{2}", str(period or "")))
        value_candidates = ("Venta $ mes", "Venta $ 7", "Venta $") if is_month else ("Venta $ 7", "Venta $ mes", "Venta $")
        pieces_candidates = ("Venta pzas", "Venta pzas 30", "Venta pzas 7") if is_month else ("Venta pzas 7", "Venta pzas 30", "Venta pzas")
        value_col = next((x for x in value_candidates if x in work.columns), "")
        pieces_col = next((x for x in pieces_candidates if x in work.columns), "")
        return value_col, pieces_col

    def catalog_for(period, store):
        entry = m._capacity_source_entry(period or "") or {}
        stamp = str(entry.get("id") or entry.get("uploaded_at") or entry.get("name") or period or "")
        key = (stamp, norm(store))
        cached = _catalog_cache.get(key)
        if cached is not None:
            return cached

        selected, work = lingerie_scope(period, store)
        if work.empty or "ID_ART" not in work.columns:
            payload = {"period": selected, "families": [], "models": {}, "metric": "Venta $"}
            _catalog_cache[key] = payload
            return payload

        fam = family_series(work)
        value_col, pieces_col = ranking_metric(selected, work)
        slim = pd.DataFrame(index=work.index)
        slim["family"] = fam
        slim["id_art"] = work["ID_ART"].fillna("").astype(str).str.strip()
        slim["model"] = work.get("Modelo", pd.Series("", index=work.index)).fillna("").astype(str).str.strip()
        slim["brand"] = work.get("Marca", pd.Series("", index=work.index)).fillna("").astype(str).str.strip()
        slim["sales_value"] = pd.to_numeric(work[value_col], errors="coerce").fillna(0.0) if value_col else 0.0
        slim["sales_pzas"] = pd.to_numeric(work[pieces_col], errors="coerce").fillna(0.0) if pieces_col else 0.0
        slim["suggested"] = pd.to_numeric(work["VPD"], errors="coerce").fillna(0.0) if "VPD" in work.columns else 0.0
        slim["existence"] = pd.to_numeric(work["Existencia"], errors="coerce").fillna(0.0) if "Existencia" in work.columns else 0.0
        slim = slim[~slim["id_art"].isin(["", "nan", "None"])]

        if slim.empty:
            payload = {"period": selected, "families": [], "models": {}, "metric": value_col or "Venta $"}
            _catalog_cache[key] = payload
            return payload

        grouped = slim.groupby(["family", "id_art"], sort=False, observed=True, dropna=False).agg(
            model=("model", "first"),
            brand=("brand", "first"),
            sales_value=("sales_value", "max"),
            sales_pzas=("sales_pzas", "max"),
            suggested=("suggested", "max"),
            existence=("existence", "max"),
        ).reset_index()

        models = {}
        for family, g in grouped.groupby("family", sort=False, observed=True):
            ordered = g.sort_values(
                ["sales_value", "sales_pzas", "suggested", "existence"],
                ascending=[False, False, False, False],
            ).reset_index(drop=True)
            rows = []
            for idx, row in ordered.iterrows():
                rows.append({
                    "rank": int(idx) + 1,
                    "id_art": str(row["id_art"]),
                    "model": str(row["model"] or ""),
                    "brand": str(row["brand"] or ""),
                    "sales_value": float(row["sales_value"] or 0),
                    "sales_pzas": float(row["sales_pzas"] or 0),
                    "suggested": float(row["suggested"] or 0),
                    "existence": float(row["existence"] or 0),
                })
            models[str(family)] = rows

        families = sorted(models, key=lambda x: norm(x))
        payload = {
            "period": selected,
            "families": families,
            "models": models,
            "metric": value_col or "Venta $",
        }
        if len(_catalog_cache) >= 36:
            _catalog_cache.pop(next(iter(_catalog_cache)))
        _catalog_cache[key] = payload
        return payload

    def captured_rows(period, store, family):
        with m.db() as con:
            rows = con.execute(
                "SELECT rank,entry_value,updated_at,updated_by FROM lingerie_champion_checklist "
                "WHERE period=? AND store=? AND family=? ORDER BY rank",
                (period, store, family),
            ).fetchall()
        return [dict(r) for r in rows]

    def resolve_manual(value, real_rows):
        raw = str(value or "").strip()
        if not raw:
            return None
        key = norm(raw)
        id_guess = norm(raw.split(" - ", 1)[0].strip())
        for row in real_rows:
            if norm(row.get("id_art")) in (key, id_guess):
                return row
        exact_model = [row for row in real_rows if norm(row.get("model")) == key]
        if len(exact_model) == 1:
            return exact_model[0]
        return None

    def comparison_payload(period, store, family):
        cat = catalog_for(period, store)
        selected = cat["period"]
        real_all = list((cat.get("models") or {}).get(family) or [])
        saved = captured_rows(selected, store, family)
        saved_map = {int(r["rank"]): r for r in saved}
        top10 = real_all[:10]

        comparison = []
        top10_hits = 0
        exact_hits = 0
        captured_count = 0
        for rank in range(1, 11):
            saved_row = saved_map.get(rank, {})
            entry = str(saved_row.get("entry_value") or "").strip()
            resolved = resolve_manual(entry, real_all) if entry else None
            if entry:
                captured_count += 1
            actual_rank = int(resolved["rank"]) if resolved else None
            in_top10 = bool(actual_rank and actual_rank <= 10)
            exact = bool(actual_rank == rank) if actual_rank else False
            if in_top10:
                top10_hits += 1
            if exact:
                exact_hits += 1
            real = top10[rank - 1] if rank - 1 < len(top10) else {}
            comparison.append({
                "rank": rank,
                "entry_value": entry,
                "captured_id_art": resolved.get("id_art") if resolved else "",
                "captured_model": resolved.get("model") if resolved else "",
                "captured_brand": resolved.get("brand") if resolved else "",
                "actual_rank": actual_rank,
                "in_top10": in_top10,
                "exact": exact,
                "rank_difference": (actual_rank - rank) if actual_rank else None,
                "real_id_art": real.get("id_art", ""),
                "real_model": real.get("model", ""),
                "real_brand": real.get("brand", ""),
                "sales_pzas": float(real.get("sales_pzas") or 0),
                "sales_value": float(real.get("sales_value") or 0),
                "suggested": float(real.get("suggested") or 0),
                "existence": float(real.get("existence") or 0),
            })

        with m.db() as con:
            summary_rows = con.execute(
                "SELECT family,COUNT(CASE WHEN TRIM(entry_value)<>'' THEN 1 END) AS captured,"
                "MAX(updated_at) AS updated_at,MAX(updated_by) AS updated_by "
                "FROM lingerie_champion_checklist WHERE period=? AND store=? GROUP BY family ORDER BY family",
                (selected, store),
            ).fetchall()
        summary_map = {str(r["family"]): dict(r) for r in summary_rows}
        family_summary = []
        for fam in cat.get("families", []):
            r = summary_map.get(fam, {})
            family_summary.append({
                "family": fam,
                "captured": int(r.get("captured") or 0),
                "complete": int(r.get("captured") or 0) >= 10,
                "updated_at": str(r.get("updated_at") or ""),
                "updated_by": str(r.get("updated_by") or ""),
            })

        return {
            "period": selected,
            "store": store,
            "family": family,
            "families": cat.get("families", []),
            "metric": cat.get("metric") or "Venta $",
            "captured": saved,
            "real_top10": top10,
            "comparison": comparison,
            "summary": {
                "captured_count": captured_count,
                "top10_hits": top10_hits,
                "exact_hits": exact_hits,
                "coverage_pct": top10_hits / 10 * 100.0,
                "position_accuracy_pct": exact_hits / 10 * 100.0,
            },
            "family_summary": family_summary,
        }

    @m.app.get("/api/lingerie-checklist/meta")
    def lingerie_meta(request: Request, period: str = "", store: str = ""):
        actor = m.require_user(request)
        if actor.get("role") not in VIEW_ROLES:
            raise HTTPException(403, "No autorizado")
        selected_store = resolve_store(actor, store)
        cat = catalog_for(period, selected_store)
        entry = m._capacity_source_entry(cat.get("period") or "") or {}
        return {
            "period": cat.get("period") or "",
            "periods": m._capacity_period_options(cat.get("period") or ""),
            "store": selected_store,
            "stores": allowed_stores(actor),
            "families": cat.get("families", []),
            "metric": cat.get("metric") or "Venta $",
            "source_file": str(entry.get("name") or ""),
            "editable": actor.get("role") in EDIT_ROLES,
            "locked_store": actor.get("role") in ("tienda", ROLE_LINGERIE),
        }

    @m.app.get("/api/lingerie-checklist/data")
    def lingerie_data(request: Request, period: str = "", store: str = "", family: str = ""):
        actor = m.require_user(request)
        if actor.get("role") not in VIEW_ROLES:
            raise HTTPException(403, "No autorizado")
        selected_store = resolve_store(actor, store)
        cat = catalog_for(period, selected_store)
        families = cat.get("families", [])
        selected_family = family if family in families else (families[0] if families else "")
        payload = comparison_payload(cat.get("period") or period, selected_store, selected_family) if selected_family else {
            "period": cat.get("period") or period,
            "store": selected_store,
            "family": "",
            "families": [],
            "metric": cat.get("metric") or "Venta $",
            "captured": [],
            "real_top10": [],
            "comparison": [],
            "summary": {"captured_count": 0, "top10_hits": 0, "exact_hits": 0, "coverage_pct": 0.0, "position_accuracy_pct": 0.0},
            "family_summary": [],
        }
        payload["editable"] = actor.get("role") in EDIT_ROLES
        payload["locked_store"] = actor.get("role") in ("tienda", ROLE_LINGERIE)
        return payload

    @m.app.post("/api/lingerie-checklist/save")
    async def lingerie_save(request: Request):
        actor = m.require_user(request)
        if actor.get("role") not in EDIT_ROLES:
            raise HTTPException(403, "No autorizado para capturar")
        body = await request.json()
        period = str(body.get("period") or "").strip()
        store = resolve_store(actor, body.get("store") or "")
        family = " ".join(str(body.get("family") or "").split()).strip()
        entries = body.get("entries") or []
        if not family:
            raise HTTPException(400, "Selecciona una familia")

        cat = catalog_for(period, store)
        selected = cat.get("period") or period
        if family not in (cat.get("families") or []):
            raise HTTPException(400, "La familia no existe en el reporte de capacidades")

        values = {}
        for item in entries:
            try:
                rank = int(item.get("rank"))
            except Exception:
                continue
            if 1 <= rank <= 10:
                values[rank] = " ".join(str(item.get("value") or "").split()).strip()[:120]

        nonempty = [norm(v) for v in values.values() if v]
        if len(nonempty) != len(set(nonempty)):
            raise HTTPException(400, "No repitas el mismo modelo dentro del Top 10")

        now = datetime.now().isoformat(timespec="seconds")
        with m.db() as con:
            con.execute(
                "DELETE FROM lingerie_champion_checklist WHERE period=? AND store=? AND family=?",
                (selected, store, family),
            )
            for rank in range(1, 11):
                value = values.get(rank, "")
                if not value:
                    continue
                con.execute(
                    "INSERT INTO lingerie_champion_checklist(period,store,family,rank,entry_value,updated_at,updated_by) "
                    "VALUES(?,?,?,?,?,?,?)",
                    (selected, store, family, rank, value, now, str(actor.get("username") or "")),
                )

        payload = comparison_payload(selected, store, family)
        payload["editable"] = True
        payload["message"] = f"Checklist guardado: {payload['summary']['captured_count']}/10 modelos capturados"
        return payload

    css = r'''<style id="v190-lingerie-css">
#page-lingerie-checklist .lingerie-toolbar{display:grid;grid-template-columns:repeat(3,minmax(0,1fr)) auto;gap:8px;align-items:end}
#page-lingerie-checklist .lingerie-kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin:10px 0}
#page-lingerie-checklist .lingerie-kpi{background:#fff;border:1px solid #dce4ee;border-radius:12px;padding:11px}
#page-lingerie-checklist .lingerie-kpi span{display:block;font-size:8px;color:#667085;font-weight:900;text-transform:uppercase}
#page-lingerie-checklist .lingerie-kpi b{display:block;font-size:22px;color:#123f78;margin-top:5px}
#page-lingerie-checklist .lingerie-input{width:100%;min-width:160px;border:1px solid #cfd9e6;border-radius:8px;padding:8px;color:#173f78;background:#fff}
#page-lingerie-checklist .lingerie-state{font-weight:900}
#page-lingerie-checklist .lingerie-exact{color:#16884c}.lingerie-top{color:#b77900}.lingerie-miss{color:#c52f2f}
#page-lingerie-checklist .lingerie-savebar{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-top:9px}
#page-lingerie-checklist .lingerie-caption{font-size:9px;color:#667085;line-height:1.45}
#page-lingerie-checklist .lingerie-current-store{font-weight:950;color:#123f78}
@media(max-width:900px){
 #page-lingerie-checklist .lingerie-toolbar{grid-template-columns:1fr 1fr}
 #page-lingerie-checklist .lingerie-toolbar .primary{grid-column:1/-1}
 #page-lingerie-checklist .lingerie-kpis{grid-template-columns:1fr 1fr}
 #page-lingerie-checklist .lingerie-kpi b{font-size:18px}
 #page-lingerie-checklist .table{min-width:980px}
}
</style>'''

    page = r'''<section class="page" id="page-lingerie-checklist">
  <div class="title">Checklist lencería</div>
  <div class="subtitle">Captura manual de los 10 modelos campeones por familia y comparación contra la venta real del reporte de capacidades.</div>

  <div class="panel lingerie-toolbar">
    <div class="filter"><label>Periodo</label><select id="lingeriePeriod"></select></div>
    <div class="filter"><label>Tienda</label><select id="lingerieStore"></select></div>
    <div class="filter"><label>Familia</label><select id="lingerieFamily"></select></div>
    <button class="primary" id="lingerieRefresh">Actualizar</button>
  </div>
  <div class="lingerie-caption" id="lingerieSource">Cargando fuente...</div>

  <div class="lingerie-kpis">
    <div class="lingerie-kpi"><span>Capturados</span><b id="lingerieCaptured">0/10</b></div>
    <div class="lingerie-kpi"><span>Coinciden Top 10</span><b id="lingerieTopHits">0</b></div>
    <div class="lingerie-kpi"><span>Posición exacta</span><b id="lingerieExactHits">0</b></div>
    <div class="lingerie-kpi"><span>Cobertura Top 10</span><b id="lingerieCoverage">0%</b></div>
  </div>

  <div class="title">Captura manual · del mayor al menor</div>
  <div class="panel">
    <div class="lingerie-caption">Escribe el <b>ID_ART</b> o el <b>Modelo</b>. El orden 1 → 10 representa la percepción de los modelos campeones de la familia seleccionada.</div>
    <div class="tablewrap model-sticky-table"><table class="table"><thead><tr><th>Posición</th><th>ID_ART / Modelo capturado</th><th>Modelo identificado</th><th>Estado vs real</th></tr></thead><tbody id="lingerieCaptureRows"></tbody></table></div>
    <div class="lingerie-savebar"><button class="primary" id="lingerieSave">Guardar familia</button><span class="msg" id="lingerieMsg"></span></div>
  </div>

  <div class="title">Comparativo · capturado vs datos reales</div>
  <div class="subtitle" id="lingerieMetricNote">Ranking real por venta del periodo.</div>
  <div class="tablewrap model-sticky-table"><table class="table"><thead><tr>
    <th>Pos.</th><th>Capturado</th><th>Rank real capturado</th><th>Resultado</th>
    <th>Top real ID_ART</th><th>Top real Modelo</th><th>Marca</th><th>Vta pzas</th><th>Venta $</th><th>Sugerido</th><th>Existencia</th>
  </tr></thead><tbody id="lingerieCompareRows"></tbody></table></div>

  <div class="title">Avance por familia</div>
  <div class="tablewrap"><table class="table"><thead><tr><th>Familia</th><th>Capturados</th><th>Estatus</th><th>Última actualización</th><th>Usuario</th></tr></thead><tbody id="lingerieFamilySummary"></tbody></table></div>
</section>'''

    js = r'''<script id="v190-lingerie-js">
(function(){
  const q=s=>document.querySelector(s),qa=s=>[...document.querySelectorAll(s)];
  const esc=s=>String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
  const nf=n=>Number(n||0).toLocaleString('es-MX',{maximumFractionDigits:0});
  const money=n=>'$'+Number(n||0).toLocaleString('es-MX',{maximumFractionDigits:0});
  const pct=n=>Number(n||0).toLocaleString('es-MX',{maximumFractionDigits:1})+'%';

  if(typeof roleLabel==='object'){
    roleLabel.colaborador='Colaborador operativo';
    roleLabel.colaborador_operativo='Colaborador operativo';
    roleLabel.colaborador_lenceria='Colaborador de lencería';
  }

  function ensureRoleOptions(){
    const nr=q('#newRole');
    if(nr){
      [...nr.options].filter(o=>o.value==='colaborador').forEach(o=>o.remove());
      let op=[...nr.options].find(o=>o.value==='colaborador_operativo');
      if(op)op.textContent='Colaborador operativo';
      else nr.insertBefore(new Option('Colaborador operativo','colaborador_operativo'),nr.firstChild);
      if(![...nr.options].some(o=>o.value==='colaborador_lenceria'))nr.insertBefore(new Option('Colaborador de lencería','colaborador_lenceria'),nr.firstChild);
      const sync=()=>{const s=q('#newStore');if(s)s.disabled=!['tienda','colaborador_operativo','colaborador_lenceria'].includes(nr.value)};
      nr.onchange=sync;sync();
    }
    qa('.userEditRole').forEach(sel=>{
      [...sel.options].filter(o=>o.value==='colaborador').forEach(o=>o.remove());
      let op=[...sel.options].find(o=>o.value==='colaborador_operativo');
      if(op)op.textContent='Colaborador operativo';else sel.add(new Option('Colaborador operativo','colaborador_operativo'));
      if(![...sel.options].some(o=>o.value==='colaborador_lenceria'))sel.add(new Option('Colaborador de lencería','colaborador_lenceria'));
    });
  }
  ensureRoleOptions();
  const oldLoadUsers=window.loadUsers;
  if(typeof oldLoadUsers==='function')window.loadUsers=async function(){await oldLoadUsers();ensureRoleOptions()};

  function ensureNav(){
    const nav=q('#analysisNav');if(!nav)return;
    let btn=nav.querySelector('[data-sub="lingerie-checklist"]');
    if(!btn){
      btn=document.createElement('button');
      btn.className='switch';btn.dataset.sub='lingerie-checklist';btn.dataset.tabKey='commercial.lingerie_checklist';btn.textContent='Checklist lencería';
      const upload=nav.querySelector('[data-sub="analysis-upload"]');nav.insertBefore(btn,upload||null);
    }
    if(!btn.dataset.bound190){
      btn.dataset.bound190='1';
      btn.addEventListener('click',ev=>{ev.preventDefault();ev.stopImmediatePropagation();openLingerieChecklist()},{capture:true});
    }
    return btn;
  }
  ensureNav();

  let META=null,DATA=null;
  function setOptions(sel,items,value){
    if(!sel)return;sel.innerHTML='';
    (items||[]).forEach(v=>sel.add(new Option(v,v)));
    if(value&&[...sel.options].some(o=>o.value===value))sel.value=value;
  }
  async function loadMeta(){
    const period=q('#lingeriePeriod')?.value||'';
    const store=q('#lingerieStore')?.value||USER?.store||'';
    const params=new URLSearchParams({period,store});
    META=await api('/api/lingerie-checklist/meta?'+params,{timeoutMs:90000});
    setOptions(q('#lingeriePeriod'),META.periods,META.period);
    setOptions(q('#lingerieStore'),META.stores,META.store);
    q('#lingerieStore').disabled=!!META.locked_store;
    const oldFamily=q('#lingerieFamily')?.value||'';
    setOptions(q('#lingerieFamily'),META.families,(META.families||[]).includes(oldFamily)?oldFamily:(META.families||[])[0]);
    q('#lingerieSource').innerHTML='Tienda: <span class="lingerie-current-store">'+esc(META.store)+'</span> · Fuente: '+esc(META.source_file||'capacidades')+' · Ranking real: '+esc(META.metric||'Venta $');
  }
  function statusText(r){
    if(!r.entry_value)return '<span class="check-na">Pendiente</span>';
    if(!r.actual_rank)return '<span class="lingerie-state lingerie-miss">No localizado</span>';
    if(r.exact)return '<span class="lingerie-state lingerie-exact">✓ Posición exacta</span>';
    if(r.in_top10)return '<span class="lingerie-state lingerie-top">Top 10 · real #'+r.actual_rank+'</span>';
    return '<span class="lingerie-state lingerie-miss">Fuera Top 10 · real #'+r.actual_rank+'</span>';
  }
  function renderData(d){
    DATA=d;
    const cmp=d.comparison||[],summary=d.summary||{};
    q('#lingerieCaptured').textContent=(summary.captured_count||0)+'/10';
    q('#lingerieTopHits').textContent=nf(summary.top10_hits);
    q('#lingerieExactHits').textContent=nf(summary.exact_hits);
    q('#lingerieCoverage').textContent=pct(summary.coverage_pct);
    q('#lingerieMetricNote').textContent='Ranking real por '+(d.metric||'Venta $')+' · desempate por venta en piezas, sugerido y existencia.';

    q('#lingerieCaptureRows').innerHTML=cmp.map(r=>'<tr>'+
      '<td><b>#'+r.rank+'</b></td>'+
      '<td><input class="lingerie-input" data-ling-rank="'+r.rank+'" value="'+esc(r.entry_value||'')+'" placeholder="ID_ART o Modelo" '+(d.editable?'':'disabled')+'></td>'+
      '<td>'+(r.captured_id_art?'<b>'+esc(r.captured_id_art)+'</b> · '+esc(r.captured_model||''):'—')+'</td>'+
      '<td>'+statusText(r)+'</td></tr>').join('');

    q('#lingerieCompareRows').innerHTML=cmp.map(r=>'<tr>'+
      '<td><b>#'+r.rank+'</b></td>'+
      '<td>'+esc(r.entry_value||'—')+'</td>'+
      '<td>'+(r.actual_rank?('#'+r.actual_rank):'—')+'</td>'+
      '<td>'+statusText(r)+'</td>'+
      '<td>'+esc(r.real_id_art||'—')+'</td>'+
      '<td>'+esc(r.real_model||'—')+'</td>'+
      '<td>'+esc(r.real_brand||'—')+'</td>'+
      '<td>'+nf(r.sales_pzas)+'</td>'+
      '<td>'+money(r.sales_value)+'</td>'+
      '<td>'+Number(r.suggested||0).toLocaleString('es-MX',{maximumFractionDigits:1})+'</td>'+
      '<td>'+nf(r.existence)+'</td></tr>').join('');

    q('#lingerieFamilySummary').innerHTML=(d.family_summary||[]).map(r=>'<tr>'+
      '<td><b>'+esc(r.family)+'</b></td><td>'+r.captured+'/10</td>'+
      '<td>'+(r.complete?'<span class="status ok">Completo</span>':'<span class="status warn">Pendiente</span>')+'</td>'+
      '<td>'+esc(r.updated_at||'—')+'</td><td>'+esc(r.updated_by||'—')+'</td></tr>').join('')||'<tr><td colspan="5">No hay familias disponibles.</td></tr>';
    q('#lingerieSave').classList.toggle('hidden',!d.editable);
  }
  async function loadData(){
    const family=q('#lingerieFamily')?.value||'';
    const params=new URLSearchParams({period:q('#lingeriePeriod')?.value||'',store:q('#lingerieStore')?.value||'',family});
    try{
      q('#lingerieMsg').textContent='Cargando comparación...';
      const d=await api('/api/lingerie-checklist/data?'+params,{timeoutMs:120000});
      renderData(d);q('#lingerieMsg').textContent='';
    }catch(e){q('#lingerieMsg').textContent='Error: '+e.message}
  }
  async function refreshMetaAndData(){
    try{await loadMeta();await loadData()}catch(e){q('#lingerieMsg').textContent='Error: '+e.message}
  }
  async function save(){
    const entries=qa('[data-ling-rank]').map(input=>({rank:Number(input.dataset.lingRank),value:input.value}));
    try{
      q('#lingerieMsg').textContent='Guardando...';
      const d=await api('/api/lingerie-checklist/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
        period:q('#lingeriePeriod')?.value||'',store:q('#lingerieStore')?.value||'',family:q('#lingerieFamily')?.value||'',entries
      }),timeoutMs:120000});
      renderData(d);q('#lingerieMsg').style.color='var(--green)';q('#lingerieMsg').textContent=d.message||'Guardado';
    }catch(e){q('#lingerieMsg').style.color='var(--red)';q('#lingerieMsg').textContent='Error: '+e.message}
  }

  async function openLingerieChecklist(direct=false){
    MAIN='analysis';SUB='lingerie-checklist';
    qa('.page').forEach(x=>x.classList.toggle('active',x.id==='page-lingerie-checklist'));
    q('#operativoNav')?.classList.add('hidden');
    q('#analysisNav')?.classList.remove('hidden');
    q('#globalFilters')?.classList.add('hidden');
    qa('#analysisNav [data-sub]').forEach(x=>x.classList.toggle('active',x.dataset.sub==='lingerie-checklist'));
    if(q('#heroTitle'))q('#heroTitle').textContent='Checklist lencería';
    if(q('#heroSub'))q('#heroSub').textContent='Top 10 por familia · captura vs datos reales';
    await refreshMetaAndData();
  }
  window.openLingerieChecklist=openLingerieChecklist;

  q('#lingerieRefresh')?.addEventListener('click',refreshMetaAndData);
  q('#lingeriePeriod')?.addEventListener('change',refreshMetaAndData);
  q('#lingerieStore')?.addEventListener('change',refreshMetaAndData);
  q('#lingerieFamily')?.addEventListener('change',loadData);
  q('#lingerieSave')?.addEventListener('click',save);

  const oldEnter=window.enter;
  if(typeof oldEnter==='function'){
    window.enter=async function(u){
      if(u?.role==='colaborador_lenceria'){
        USER=u;
        q('#loginView')?.classList.add('hidden');q('#appView')?.classList.remove('hidden');
        if(q('#profileName'))q('#profileName').textContent=u.username||'Colaborador';
        if(q('#profileRole'))q('#profileRole').textContent='Colaborador de lencería';
        if(q('#profileMeta'))q('#profileMeta').textContent='Checklist lencería';
        q('#viewRoleBox')?.classList.add('hidden');
        qa('.superOnly,.adminOnly').forEach(x=>x.classList.add('hidden'));
        qa('[data-main]').forEach(x=>x.classList.toggle('hidden',x.dataset.main!=='analysis'));
        const main=q('[data-main="analysis"]');if(main){main.classList.remove('hidden');main.classList.add('active');main.innerHTML='Checklist lencería<small>Captura Top 10 por familia</small>'}
        q('#operativoNav')?.classList.add('hidden');q('#analysisNav')?.classList.remove('hidden');
        ensureNav();qa('#analysisNav [data-sub]').forEach(x=>x.classList.toggle('hidden',x.dataset.sub!=='lingerie-checklist'));
        qa('#mobileMainNav [data-main]').forEach(x=>x.classList.toggle('hidden',x.dataset.main!=='analysis'));
        refreshHeaderClock?.();
        await openLingerieChecklist(true);
        return;
      }
      await oldEnter(u);
      ensureNav();ensureRoleOptions();
      if(u?.role==='colaborador'&&q('#profileRole'))q('#profileRole').textContent='Colaborador operativo';
    };
  }

  console.info('[V190] Checklist lencería y perfiles colaboradores activos.');
})();
</script>'''

    @m.app.middleware("http")
    async def v190_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            # La versión base actual ya incluye la pestaña y su JS nativo.
            # Sólo inyectar la interfaz V190 como respaldo en versiones antiguas;
            # mezclar ambos frontends genera IDs duplicados y listeners cruzados.
            if 'page-lingerie-checklist' not in html:
                if 'v190-lingerie-css' not in html:
                    html = html.replace("</head>", css + "</head>", 1)
                html = html.replace("</main>", page + "</main>", 1)
                if 'v190-lingerie-js' not in html:
                    html = html.replace("</body>", js + "</body>", 1)
            return HTMLResponse(html, status_code=response.status_code, headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-Operations-UI-Version": "V190",
            })
        except Exception as exc:
            print(f"[V190] HTML warning: {type(exc).__name__}: {exc}", flush=True)
            return response

    m._V190_LINGERIE_CHECKLIST = True
    print("[V190] Checklist Lencería activo · Top 10 manual vs capacidades.", flush=True)
