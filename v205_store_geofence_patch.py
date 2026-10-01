"""V205 · Geocerca por tienda para acceso de perfiles asignados a tienda.

Seguridad:
- Super Administrador, Administrador y Director: exentos.
- Perfiles con tienda asignada: geocerca obligatoria sólo cuando la tienda
  tiene geolocalización ACTIVADA y coordenadas configuradas.
- La validación se repite cada 5 min; el permiso de servidor dura 10 min.
- El servidor protege los endpoints mediante require_user.
- No se persisten coordenadas del usuario; sólo se calcula distancia al verificar.
"""
from __future__ import annotations

import math
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import Request, HTTPException
from fastapi.responses import HTMLResponse

MX = ZoneInfo("America/Mexico_City")
EXEMPT_REAL_ROLES = {"superadmin", "admin", "director"}
STORE_BOUND_ROLES = {"tienda", "colaborador", "colaborador_lenceria", "colaborador_operativo"}
VERIFY_TTL_SECONDS = 600
MAX_ACCEPTABLE_ACCURACY_M = 250.0


def install(m):
    if getattr(m, "_V205_STORE_GEOFENCE", False):
        return

    # ------------------------------------------------------------------
    # Persistencia de configuración por tienda
    # ------------------------------------------------------------------
    with m.db() as con:
        cols = {str(r["name"]) for r in con.execute("PRAGMA table_info(stores)").fetchall()}
        additions = (
            ("geo_enabled", "INTEGER NOT NULL DEFAULT 0"),
            ("geo_lat", "REAL"),
            ("geo_lon", "REAL"),
            ("geo_radius_m", "REAL NOT NULL DEFAULT 200"),
            ("geo_updated_at", "TEXT DEFAULT ''"),
            ("geo_updated_by", "TEXT DEFAULT ''"),
        )
        for name, definition in additions:
            if name not in cols:
                con.execute(f"ALTER TABLE stores ADD COLUMN {name} {definition}")

    def _store_geo(store_name: str):
        key = m.login_key(store_name)
        with m.db() as con:
            rows = con.execute(
                """SELECT id,name,active,project,geo_enabled,geo_lat,geo_lon,
                          geo_radius_m,geo_updated_at,geo_updated_by
                   FROM stores ORDER BY name"""
            ).fetchall()
        for row in rows:
            if m.login_key(row["name"]) == key:
                return dict(row)
        return None

    def _geo_state(user: dict, request: Request):
        if not user:
            return {
                "required": False, "exempt": False, "configured": False,
                "enabled": False, "verified": False, "store": "",
            }
        real_role = str(user.get("real_role") or user.get("role") or "").strip().lower()
        effective_role = str(user.get("role") or "").strip().lower()
        store = str(user.get("store") or "").strip()
        exempt = real_role in EXEMPT_REAL_ROLES
        cfg = _store_geo(store) if store else None
        enabled = bool(cfg and cfg.get("geo_enabled"))
        configured = bool(
            cfg
            and cfg.get("geo_lat") is not None
            and cfg.get("geo_lon") is not None
            and float(cfg.get("geo_radius_m") or 0) > 0
        )
        # La regla depende de tener tienda asignada y no ser un rol exento.
        # No activamos bloqueo si el administrador todavía no terminó la
        # configuración de coordenadas, evitando lockout accidental.
        required = bool(store and not exempt and enabled and configured)
        stamp = str((cfg or {}).get("geo_updated_at") or "")
        verified = False
        expires_at = float(request.session.get("geo_verified_until") or 0)
        if required:
            verified = (
                expires_at > time.time()
                and m.login_key(request.session.get("geo_store") or "") == m.login_key(store)
                and str(request.session.get("geo_config_stamp") or "") == stamp
            )
        return {
            "required": required,
            "exempt": exempt,
            "configured": configured,
            "enabled": enabled,
            "verified": verified,
            "store": store,
            "radius_m": float((cfg or {}).get("geo_radius_m") or 200),
            "config_stamp": stamp,
            "expires_at": expires_at if verified else 0,
            "effective_role": effective_role,
            "real_role": real_role,
        }

    def _distance_m(lat1, lon1, lat2, lon2):
        r = 6371000.0
        p1, p2 = math.radians(lat1), math.radians(lat2)
        dp = math.radians(lat2 - lat1)
        dl = math.radians(lon2 - lon1)
        a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
        return 2 * r * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1 - a)))

    # ------------------------------------------------------------------
    # Añadir estado de geocerca al usuario retornado por login/sesión
    # ------------------------------------------------------------------
    _base_current_user = m.current_user

    def _v205_current_user(request: Request):
        user = _base_current_user(request)
        if not user:
            return user
        state = _geo_state(user, request)
        user["geofence_required"] = state["required"]
        user["geofence_exempt"] = state["exempt"]
        user["geofence_configured"] = state["configured"]
        user["geofence_enabled"] = state["enabled"]
        user["geofence_verified"] = state["verified"]
        user["geofence_store"] = state["store"]
        user["geofence_radius_m"] = state["radius_m"]
        return user

    m.current_user = _v205_current_user

    # ------------------------------------------------------------------
    # Endpoints de verificación y administración
    # ------------------------------------------------------------------
    _base_require_user = m.require_user

    @m.app.get("/api/geofence/status")
    def geofence_status(request: Request):
        user = _base_require_user(request)
        state = _geo_state(user, request)
        return {
            "required": state["required"],
            "exempt": state["exempt"],
            "configured": state["configured"],
            "enabled": state["enabled"],
            "verified": state["verified"],
            "store": state["store"],
            "radius_m": state["radius_m"],
            "expires_at": state["expires_at"],
        }

    @m.app.post("/api/geofence/verify")
    async def geofence_verify(request: Request):
        user = _base_require_user(request)
        state = _geo_state(user, request)
        if state["exempt"] or not state["required"]:
            request.session.pop("geo_verified_until", None)
            request.session.pop("geo_store", None)
            request.session.pop("geo_config_stamp", None)
            return {
                "ok": True, "allowed": True, "required": False,
                "store": state["store"], "reason": "exempt_or_not_enabled",
            }

        body = await request.json()
        try:
            lat = float(body.get("latitude"))
            lon = float(body.get("longitude"))
            accuracy = max(float(body.get("accuracy") or 0), 0.0)
        except Exception:
            raise HTTPException(400, "Ubicación inválida")

        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise HTTPException(400, "Ubicación inválida")
        if accuracy > MAX_ACCEPTABLE_ACCURACY_M:
            request.session.pop("geo_verified_until", None)
            request.session.pop("geo_store", None)
            request.session.pop("geo_config_stamp", None)
            return {
                "ok": True, "allowed": False, "required": True,
                "store": state["store"], "reason": "low_accuracy",
                "accuracy_m": round(accuracy, 1),
                "message": "La precisión de ubicación es insuficiente. Activa ubicación precisa e inténtalo nuevamente.",
            }

        cfg = _store_geo(state["store"])
        if not cfg or cfg.get("geo_lat") is None or cfg.get("geo_lon") is None:
            raise HTTPException(409, "La tienda aún no tiene geocerca configurada")

        distance = _distance_m(
            lat, lon, float(cfg["geo_lat"]), float(cfg["geo_lon"])
        )
        radius = float(cfg.get("geo_radius_m") or 200)
        # Pequeña tolerancia de precisión GPS, acotada a 50 m.
        tolerance = min(max(accuracy, 0.0), 50.0)
        allowed = distance <= radius + tolerance
        if allowed:
            request.session["geo_verified_until"] = time.time() + VERIFY_TTL_SECONDS
            request.session["geo_store"] = str(cfg["name"])
            request.session["geo_config_stamp"] = str(cfg.get("geo_updated_at") or "")
        else:
            request.session.pop("geo_verified_until", None)
            request.session.pop("geo_store", None)
            request.session.pop("geo_config_stamp", None)

        return {
            "ok": True,
            "allowed": allowed,
            "required": True,
            "store": str(cfg["name"]),
            "distance_m": round(distance, 1),
            "radius_m": radius,
            "accuracy_m": round(accuracy, 1),
            "expires_in_seconds": VERIFY_TTL_SECONDS if allowed else 0,
            "message": (
                "Ubicación verificada correctamente."
                if allowed
                else f"Estás fuera del perímetro autorizado de {cfg['name']}."
            ),
        }

    @m.app.get("/api/geofence/admin/stores")
    def geofence_admin_stores(request: Request):
        actor = _base_require_user(request, ("superadmin", "admin"))
        with m.db() as con:
            rows = con.execute(
                """SELECT id,name,active,project,geo_enabled,geo_lat,geo_lon,
                          geo_radius_m,geo_updated_at,geo_updated_by
                   FROM stores ORDER BY name"""
            ).fetchall()
        return {
            "stores": [dict(r) for r in rows],
            "editable": str(actor.get("role") or "") in ("superadmin", "admin"),
            "default_radius_m": 200,
            "note": "La geocerca sólo bloquea perfiles con tienda asignada. Director, Administrador y Super Administrador están exentos.",
        }

    @m.app.put("/api/geofence/admin/stores/{store_id}")
    async def geofence_admin_update(store_id: int, request: Request):
        actor = _base_require_user(request, ("superadmin", "admin"))
        body = await request.json()
        enabled = 1 if bool(body.get("enabled")) else 0

        def maybe_float(value):
            if value is None or str(value).strip() == "":
                return None
            try:
                return float(value)
            except Exception:
                raise HTTPException(400, "Coordenadas inválidas")

        lat = maybe_float(body.get("latitude"))
        lon = maybe_float(body.get("longitude"))
        try:
            radius = float(body.get("radius_m") or 200)
        except Exception:
            raise HTTPException(400, "Radio inválido")

        if lat is not None and not (-90 <= lat <= 90):
            raise HTTPException(400, "Latitud inválida")
        if lon is not None and not (-180 <= lon <= 180):
            raise HTTPException(400, "Longitud inválida")
        if radius < 50 or radius > 2000:
            raise HTTPException(400, "El radio debe estar entre 50 y 2,000 metros")
        if enabled and (lat is None or lon is None):
            raise HTTPException(400, "Configura latitud y longitud antes de activar la geocerca")

        now = datetime.now(MX).isoformat(timespec="seconds")
        with m.db() as con:
            old = con.execute("SELECT id,name FROM stores WHERE id=?", (store_id,)).fetchone()
            if not old:
                raise HTTPException(404, "Tienda no encontrada")
            con.execute(
                """UPDATE stores
                   SET geo_enabled=?,geo_lat=?,geo_lon=?,geo_radius_m=?,
                       geo_updated_at=?,geo_updated_by=?,updated_at=?,updated_by=?
                   WHERE id=?""",
                (
                    enabled, lat, lon, radius, now, str(actor.get("username") or ""),
                    now, str(actor.get("username") or ""), store_id,
                ),
            )
        return {
            "ok": True,
            "message": f"Geolocalización de {old['name']} actualizada.",
            "enabled": bool(enabled),
        }

    # ------------------------------------------------------------------
    # Protección central. Las rutas existentes resuelven require_user en
    # tiempo de ejecución, así que esta sustitución protege módulos previos.
    # ------------------------------------------------------------------
    BYPASS_PATHS = {
        "/api/geofence/status",
        "/api/geofence/verify",
        "/api/me/profile-onboarding",
        "/api/me/change-password",
    }

    def _v205_require_user(request: Request, roles=None):
        user = _base_require_user(request, roles)
        path = str(getattr(request.url, "path", "") or "")
        if path in BYPASS_PATHS or path.startswith("/api/geofence/admin/"):
            return user
        state = _geo_state(user, request)
        if state["required"] and not state["verified"]:
            raise HTTPException(
                428,
                f"Verifica tu ubicación en {state['store']} para continuar."
            )
        return user

    m.require_user = _v205_require_user

    # ------------------------------------------------------------------
    # UX
    # ------------------------------------------------------------------
    css = r'''<style id="v205-geofence-css">
#v205GeoOverlay{
  position:fixed;inset:0;z-index:2147483000;
  display:none;place-items:center;padding:20px;
  background:rgba(7,29,53,.78);
  backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);
}
#v205GeoOverlay.on{display:grid!important}
.v205-geo-card{
  width:min(430px,100%);background:#fff;border:1px solid #d8e4ef;
  border-radius:22px;padding:24px;box-shadow:0 28px 80px rgba(0,0,0,.28);
  text-align:center;color:#123f73
}
.v205-geo-icon{
  width:68px;height:68px;margin:0 auto 13px;border-radius:20px;
  display:grid;place-items:center;background:linear-gradient(145deg,#eaf4ff,#dceeff);
  color:#0c65b5;border:1px solid #cfe2f5
}
.v205-geo-icon svg{width:34px;height:34px}
.v205-geo-card h2{margin:0;font-size:21px;font-weight:950;letter-spacing:-.025em}
.v205-geo-store{margin:7px 0 4px;font-size:14px;font-weight:900;color:#0d64b2}
.v205-geo-msg{margin:10px 0 15px;color:#667b91;font-size:11px;line-height:1.5}
.v205-geo-actions{display:grid;gap:8px}
.v205-geo-primary,.v205-geo-secondary{
  min-height:48px;border-radius:12px;font-weight:950;cursor:pointer
}
.v205-geo-primary{border:0;background:linear-gradient(135deg,#176fe8,#0b82ee);color:#fff}
.v205-geo-secondary{border:1px solid #d5e0eb;background:#fff;color:#536f8a}
.v205-geo-primary:disabled{opacity:.55}
.v205-geo-foot{font-size:8px;color:#8595a8;margin-top:11px;line-height:1.4}

/* Configuración en Metas y tiendas */
#v205GeoAdminPanel{margin-top:16px}
.v205-geo-admin-note{
  border:1px solid #b9d8f5;background:#eef7ff;color:#285a87;
  border-radius:12px;padding:10px 12px;font-size:8.5px;line-height:1.45;margin:7px 0 10px
}
.v205-geo-tablewrap{overflow:auto;-webkit-overflow-scrolling:touch;border:1px solid #d8e4ef;border-radius:12px}
.v205-geo-table{width:100%;min-width:1050px;border-collapse:separate;border-spacing:0;font-size:8px;background:#fff}
.v205-geo-table th{position:sticky;top:0;background:#124d84;color:#fff;padding:8px 7px;text-align:left;white-space:nowrap}
.v205-geo-table td{padding:7px;border-bottom:1px solid #e7eef5;color:#284f76;vertical-align:middle}
.v205-geo-table input[type="number"]{width:118px;min-height:36px;border:1px solid #ccd9e7;border-radius:8px;padding:6px;color:#123f73;background:#fbfdff}
.v205-geo-table input.geo-radius{width:84px}
.v205-geo-table input[type="checkbox"]{width:18px;height:18px;accent-color:#176fe8}
.v205-geo-row-actions{display:flex;gap:5px;white-space:nowrap}
.v205-geo-mini{border:1px solid #cbd9e7;background:#fff;color:#174f85;border-radius:8px;padding:7px 8px;font-weight:850;font-size:7.5px}
.v205-geo-save{background:#176fe8;color:#fff;border-color:#176fe8}
.v205-geo-status{display:inline-flex;padding:4px 7px;border-radius:999px;font-weight:900;font-size:7px}
.v205-geo-status.on{background:#dcfce7;color:#166534}.v205-geo-status.off{background:#f1f5f9;color:#64748b}.v205-geo-status.pending{background:#fff7ed;color:#c2410c}
@media(max-width:900px){
 .v205-geo-card{padding:20px 17px;border-radius:19px}
 .v205-geo-card h2{font-size:19px}
}
</style>'''

    js = r'''<script id="v205-geofence-js">
(function(){
  if(window.__V205_GEOFENCE)return;
  window.__V205_GEOFENCE=true;

  const q=(s,r=document)=>r.querySelector(s);
  const qa=(s,r=document)=>[...r.querySelectorAll(s)];
  const esc=s=>String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  let geoPromise=null,geoTimer=0,lastGeoUser=null;

  async function G(url,opt){
    if(typeof api==='function')return api(url,{timeoutMs:30000,...(opt||{})});
    const r=await fetch(url,{credentials:'same-origin',...(opt||{})});
    const raw=await r.text();let d={};try{d=raw?JSON.parse(raw):{}}catch(_){}
    if(!r.ok)throw Error(d.detail||d.message||('HTTP '+r.status));
    return d;
  }

  function overlay(){
    let el=q('#v205GeoOverlay');
    if(el)return el;
    el=document.createElement('div');el.id='v205GeoOverlay';
    el.innerHTML='<div class="v205-geo-card">'+
      '<div class="v205-geo-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M20 10c0 5-8 12-8 12S4 15 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="2.5"/></svg></div>'+
      '<h2>Verificación de ubicación</h2><div id="v205GeoStore" class="v205-geo-store"></div>'+
      '<div id="v205GeoMsg" class="v205-geo-msg">Necesitamos confirmar que estás en tu tienda asignada.</div>'+
      '<div class="v205-geo-actions"><button id="v205GeoRetry" class="v205-geo-primary">Verificar ubicación</button>'+
      '<button id="v205GeoLogout" class="v205-geo-secondary">Cerrar sesión</button></div>'+
      '<div class="v205-geo-foot">La ubicación se usa para validar el acceso. El sistema no guarda un historial de tus coordenadas.</div>'+
      '</div>';
    document.body.appendChild(el);
    q('#v205GeoLogout').onclick=async()=>{
      try{await fetch('/api/logout',{method:'POST',credentials:'same-origin'})}catch(_){}
      location.reload();
    };
    return el;
  }

  function showGeo(store,msg){
    const el=overlay();el.classList.add('on');
    q('#v205GeoStore').textContent=store||'Tienda asignada';
    q('#v205GeoMsg').textContent=msg||'Necesitamos confirmar que estás en tu tienda asignada.';
  }
  function hideGeo(){q('#v205GeoOverlay')?.classList.remove('on')}

  function getPosition(){
    return new Promise((resolve,reject)=>{
      if(!navigator.geolocation){reject(new Error('Este dispositivo no permite obtener ubicación.'));return}
      navigator.geolocation.getCurrentPosition(
        p=>resolve(p),
        e=>{
          let msg='No fue posible obtener tu ubicación.';
          if(e.code===1)msg='Permite el acceso a tu ubicación para entrar a la aplicación.';
          else if(e.code===2)msg='No se pudo determinar tu ubicación. Verifica GPS, Wi‑Fi o señal móvil.';
          else if(e.code===3)msg='La ubicación tardó demasiado. Inténtalo nuevamente.';
          reject(new Error(msg));
        },
        {enableHighAccuracy:true,timeout:18000,maximumAge:0}
      );
    });
  }

  async function performGeoVerification(status){
    const retry=q('#v205GeoRetry');
    showGeo(status.store,'Obteniendo tu ubicación precisa…');
    if(retry){retry.disabled=true;retry.textContent='Verificando…'}
    try{
      const p=await getPosition();
      q('#v205GeoMsg').textContent='Validando distancia con '+(status.store||'tu tienda')+'…';
      const r=await G('/api/geofence/verify',{
        method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({
          latitude:p.coords.latitude,
          longitude:p.coords.longitude,
          accuracy:p.coords.accuracy
        })
      });
      if(!r.allowed){
        showGeo(r.store,r.message||'Estás fuera del perímetro autorizado.');
        return false;
      }
      q('#v205GeoMsg').textContent='Ubicación verificada. Abriendo Operaciones Ropa…';
      await new Promise(res=>setTimeout(res,350));
      hideGeo();
      return true;
    }catch(e){
      showGeo(status.store,e.message||String(e));
      return false;
    }finally{
      if(retry){retry.disabled=false;retry.textContent='Verificar ubicación'}
    }
  }

  async function ensureGeo(user,force=false){
    if(geoPromise&&!force)return geoPromise;
    geoPromise=(async()=>{
      let status;
      try{status=await G('/api/geofence/status')}catch(e){return user}
      lastGeoUser=user||lastGeoUser;
      if(!status.required||status.exempt){
        hideGeo();return user;
      }
      if(status.verified&&!force){
        hideGeo();return user;
      }
      showGeo(status.store);
      const retry=q('#v205GeoRetry');
      const run=()=>performGeoVerification(status);
      if(retry)retry.onclick=run;
      const ok=await run();
      if(!ok){
        // Mantener la promesa pendiente hasta que el usuario logre validar.
        return await new Promise(resolve=>{
          if(retry)retry.onclick=async()=>{
            const accepted=await run();
            if(accepted)resolve(user);
          };
        });
      }
      return user;
    })();
    try{return await geoPromise}finally{geoPromise=null}
  }

  function installEnterGuard(){
    if(typeof window.enter!=='function'||window.enter.__v205Geo)return;
    const base=window.enter;
    const wrapped=async function(user){
      const allowedUser=await ensureGeo(user,false);
      const out=await base.call(this,allowedUser);
      startPeriodicCheck();
      return out;
    };
    wrapped.__v205Geo=true;
    try{window.enter=wrapped;enter=wrapped}catch(_){window.enter=wrapped}
  }

  function currentUser(){
    try{return USER||lastGeoUser}catch(_){return lastGeoUser}
  }

  function startPeriodicCheck(){
    clearInterval(geoTimer);
    geoTimer=setInterval(async()=>{
      const u=currentUser();if(!u)return;
      try{
        const s=await G('/api/geofence/status');
        if(s.required&&!s.exempt){
          // Renovar cuando queden menos de 5 minutos o por seguridad cada ciclo.
          await ensureGeo(u,true);
        }
      }catch(_){}
    },5*60*1000);
  }

  document.addEventListener('visibilitychange',()=>{
    if(document.visibilityState!=='visible')return;
    const u=currentUser();if(!u)return;
    setTimeout(async()=>{
      try{
        const s=await G('/api/geofence/status');
        if(s.required&&!s.exempt&&!s.verified)await ensureGeo(u,true);
      }catch(_){}
    },250);
  });

  // ----------------------------------------------------------------
  // Configuración para Metas y tiendas
  // ----------------------------------------------------------------
  async function renderGeoAdmin(){
    const title=String(q('#operativoDynamicTitle')?.textContent||'');
    const host=q('#operativoDynamicContent');
    if(!host||!title.toLowerCase().includes('configuración de metas'))return;
    let data;
    try{data=await G('/api/geofence/admin/stores')}catch(_){return}
    q('#v205GeoAdminPanel')?.remove();
    const panel=document.createElement('div');panel.id='v205GeoAdminPanel';
    const rows=(data.stores||[]).map(r=>{
      const configured=r.geo_lat!=null&&r.geo_lon!=null;
      const status=r.geo_enabled&&configured
        ?'<span class="v205-geo-status on">Activa</span>'
        :r.geo_enabled
          ?'<span class="v205-geo-status pending">Falta ubicación</span>'
          :'<span class="v205-geo-status off">Desactivada</span>';
      return '<tr data-v205-store="'+r.id+'"><td><b>'+esc(r.name)+'</b></td>'+
        '<td><input class="geo-enabled" type="checkbox" '+(r.geo_enabled?'checked':'')+'></td>'+
        '<td><input class="geo-lat" type="number" step="0.000001" placeholder="19.000000" value="'+(r.geo_lat==null?'':r.geo_lat)+'"></td>'+
        '<td><input class="geo-lon" type="number" step="0.000001" placeholder="-99.000000" value="'+(r.geo_lon==null?'':r.geo_lon)+'"></td>'+
        '<td><input class="geo-radius" type="number" min="50" max="2000" step="10" value="'+Number(r.geo_radius_m||200)+'"></td>'+
        '<td>'+status+'</td><td>'+esc(r.geo_updated_by||'')+'</td>'+
        '<td><div class="v205-geo-row-actions"><button class="v205-geo-mini geo-current">Usar mi ubicación</button><button class="v205-geo-mini v205-geo-save geo-save">Guardar</button></div></td></tr>';
    }).join('');
    panel.innerHTML='<div class="title">Geolocalización de acceso</div>'+
      '<div class="v205-geo-admin-note"><b>Regla:</b> usuarios con tienda asignada sólo podrán entrar dentro del radio configurado. Director, Administrador y Super Administrador no requieren ubicación. La geocerca no se activa hasta tener coordenadas válidas.</div>'+
      '<div class="v205-geo-tablewrap"><table class="v205-geo-table"><thead><tr><th>Tienda</th><th>Geocerca</th><th>Latitud</th><th>Longitud</th><th>Radio (m)</th><th>Estado</th><th>Actualizó</th><th>Acción</th></tr></thead><tbody>'+rows+'</tbody></table></div>'+
      '<div id="v205GeoAdminMsg" class="msg"></div>';
    host.appendChild(panel);

    qa('.geo-current',panel).forEach(btn=>btn.onclick=async()=>{
      const tr=btn.closest('tr');const msg=q('#v205GeoAdminMsg');
      btn.disabled=true;msg.textContent='Obteniendo ubicación del dispositivo…';
      try{
        const p=await getPosition();
        tr.querySelector('.geo-lat').value=Number(p.coords.latitude).toFixed(6);
        tr.querySelector('.geo-lon').value=Number(p.coords.longitude).toFixed(6);
        msg.style.color='var(--green)';msg.textContent='Ubicación capturada. Revisa el radio y pulsa Guardar.';
      }catch(e){msg.style.color='var(--red)';msg.textContent=e.message||String(e)}
      finally{btn.disabled=false}
    });

    qa('.geo-save',panel).forEach(btn=>btn.onclick=async()=>{
      const tr=btn.closest('tr'),msg=q('#v205GeoAdminMsg');
      const id=tr.dataset.v205Store;
      const body={
        enabled:tr.querySelector('.geo-enabled').checked,
        latitude:tr.querySelector('.geo-lat').value,
        longitude:tr.querySelector('.geo-lon').value,
        radius_m:tr.querySelector('.geo-radius').value
      };
      btn.disabled=true;msg.textContent='Guardando geocerca…';
      try{
        const r=await G('/api/geofence/admin/stores/'+id,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
        msg.style.color='var(--green)';msg.textContent=r.message;
        setTimeout(renderGeoAdmin,250);
      }catch(e){msg.style.color='var(--red)';msg.textContent='Error: '+(e.message||e)}
      finally{btn.disabled=false}
    });
  }

  function installGoalsHook(){
    if(typeof window.renderGoalsConfig!=='function'||window.renderGoalsConfig.__v205Geo)return;
    const base=window.renderGoalsConfig;
    const wrapped=async function(){
      const out=await base.apply(this,arguments);
      setTimeout(renderGeoAdmin,30);
      return out;
    };
    wrapped.__v205Geo=true;
    try{window.renderGoalsConfig=wrapped;renderGoalsConfig=wrapped}catch(_){window.renderGoalsConfig=wrapped}
  }

  function setup(){installEnterGuard();installGoalsHook()}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',setup,{once:true});else setup();
  [150,500,1200,2400].forEach(ms=>setTimeout(setup,ms));
  window.addEventListener('pageshow',()=>setTimeout(setup,80),{passive:true});
  console.info('[V205] Geocerca por tienda instalada.');
})();
</script>'''

    @m.app.middleware("http")
    async def v205_html(request, call_next):
        response = await call_next(request)
        if request.url.path != "/" or getattr(response, "status_code", 200) != 200:
            return response
        try:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            html = body.decode("utf-8", errors="replace")
            if "v205-geofence-css" not in html:
                html = html.replace("</head>", css + "</head>", 1)
            if "v205-geofence-js" not in html:
                html = html.replace("</body>", js + "</body>", 1)
            headers = dict(getattr(response, "headers", {}) or {})
            headers.pop("content-length", None)
            headers.update({
                "Cache-Control":"no-store, no-cache, must-revalidate, max-age=0",
                "Pragma":"no-cache","Expires":"0","X-Operations-UI-Version":"V205",
            })
            return HTMLResponse(html,status_code=response.status_code,headers=headers)
        except Exception as exc:
            print(f"[V205] HTML warning: {type(exc).__name__}: {exc}", flush=True)
            return response

    m._V205_STORE_GEOFENCE = True
    print("[V205] Geocerca por tienda instalada; roles directivos exentos.", flush=True)
