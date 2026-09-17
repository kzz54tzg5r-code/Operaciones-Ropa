from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
import math, re, unicodedata

from fastapi import Request


def install(m):
    if getattr(m, "_V167_BACKEND", False):
        return

    def norm(v):
        t = unicodedata.normalize("NFKD", str(v or ""))
        t = "".join(ch for ch in t if not unicodedata.combining(ch))
        return " ".join(t.casefold().strip().split())

    def num(v):
        try:
            x = float(v or 0)
            return x if math.isfinite(x) else 0.0
        except Exception:
            return 0.0

    def bounds(kind, value):
        kind = str(kind or "week").lower()
        value = str(value or "").strip()
        today = date.today()
        if kind == "day":
            d = datetime.strptime((value or today.isoformat())[:10], "%Y-%m-%d").date()
            return d, d
        if kind == "week":
            mt = re.fullmatch(r"(\d{4})-W(\d{1,2})", value, re.I)
            if mt:
                y, w = int(mt.group(1)), int(mt.group(2))
            else:
                iso = today.isocalendar(); y, w = iso.year, iso.week
            d = date.fromisocalendar(y, w, 1)
            return d, d + timedelta(days=6)
        if kind == "month":
            mt = re.fullmatch(r"(\d{4})-(\d{1,2})", value)
            y, mo = (int(mt.group(1)), int(mt.group(2))) if mt else (today.year, today.month)
            d = date(y, mo, 1)
            nxt = date(y + (1 if mo == 12 else 0), 1 if mo == 12 else mo + 1, 1)
            return d, nxt - timedelta(days=1)
        if kind == "year":
            y = int(value or today.year)
            return date(y, 1, 1), date(y, 12, 31)
        return date(2000, 1, 1), today

    def hour_of(v):
        mt = re.search(r"(?:^|\s)([01]?\d|2[0-3]):([0-5]\d)", str(v or ""))
        if mt:
            return int(mt.group(1))
        try:
            x = float(v)
            if 0 <= x < 1:
                return int(x * 24)
        except Exception:
            pass
        return None

    def selected_store(actor, requested):
        try:
            return str(m.effective_store(actor, requested) or "Compañía")
        except Exception:
            return str(requested or "Compañía")

    def accepted(r, selected, area, activity, start, end):
        ds = str(r.get("date") or "")[:10]
        try:
            d = date.fromisoformat(ds)
        except Exception:
            return None
        if not (start <= d <= end):
            return None
        if selected != "Compañía" and norm(r.get("store")) != norm(selected):
            return None
        if str(area or "") not in ("", "Todas", "Todos") and norm(r.get("area")) != norm(area):
            return None
        if str(activity or "") not in ("", "Todas", "Todos"):
            act = r.get("activity") or r.get("activity_original") or ""
            if norm(act) != norm(activity):
                return None
        return d

    @m.app.get("/api/operations/routes-store-day-v167")
    def routes_store_day(request: Request, period_type: str="week", period_value: str="", store: str="Compañía", area: str="Todas", activity: str="Todas"):
        actor = m.require_user(request)
        start, end = bounds(period_type, period_value)
        selected = selected_store(actor, store)
        grouped = defaultdict(float)
        for r in list((m.load_ops() or {}).get("rows") or []):
            d = accepted(r, selected, area, activity, start, end)
            if not d:
                continue
            value = num(r.get("recorridos"))
            if value > 0:
                grouped[(d.isoformat(), str(r.get("store") or "Sin tienda"))] += value
        rows = [{"date": d, "store": s, "routes": v} for (d, s), v in grouped.items()]
        rows.sort(key=lambda x: (x["date"], x["store"]))
        return {"rows": rows, "total": sum(x["routes"] for x in rows)}

    def shift_month(d, delta):
        y, mo = d.year, d.month + delta
        while mo <= 0:
            y -= 1; mo += 12
        while mo > 12:
            y += 1; mo -= 12
        return date(y, mo, 1)

    def windows(kind, value):
        start, end = bounds(kind, value)
        if kind == "day":
            return [(start - timedelta(days=i), start - timedelta(days=i), (start - timedelta(days=i)).isoformat()) for i in range(3, -1, -1)]
        if kind == "week":
            out = []
            for i in range(3, -1, -1):
                s = start - timedelta(days=7*i); iso = s.isocalendar()
                out.append((s, s + timedelta(days=6), f"{iso.year}-W{iso.week:02d}"))
            return out
        if kind == "month":
            out = []
            for i in range(3, -1, -1):
                s = shift_month(start, -i); nxt = shift_month(s, 1)
                out.append((s, nxt - timedelta(days=1), s.strftime("%Y-%m")))
            return out
        return [(start, end, str(start.year))]

    @m.app.get("/api/operations/collection-trend-v167")
    def collection_trend(request: Request, period_type: str="week", period_value: str="", store: str="Compañía", area: str="Todas", activity: str="Todas"):
        actor = m.require_user(request)
        selected = selected_store(actor, store)
        source = list((m.load_ops() or {}).get("rows") or [])
        periods = []
        for start, end, label in windows(period_type, period_value):
            hourly = defaultdict(lambda: {"muertos":0.0, "cajas":0.0, "probador":0.0})
            for r in source:
                d = accepted(r, selected, area, activity, start, end)
                if not d:
                    continue
                h = hour_of(r.get("start_time"))
                if h is None:
                    continue
                hourly[h]["muertos"] += num(r.get("muertos"))
                hourly[h]["cajas"] += num(r.get("cajas"))
                hourly[h]["probador"] += num(r.get("probador"))
            hours = []
            for h in sorted(hourly):
                x = hourly[h]; total = sum(x.values())
                hours.append({"hour":h, "label":f"{h:02d}:00", **x, "total":total})
            periods.append({"label":label, "hours":hours, "total":sum(x["total"] for x in hours)})
        return {"period_type":period_type, "periods":periods}

    def money_value(text):
        vals = []
        for token in re.findall(r"-?\$?\s*\d[\d,]*(?:\.\d+)?", str(text or "")):
            try:
                v = float(token.replace("$","").replace(",","").strip())
            except Exception:
                continue
            if v >= 1000 and not (2020 <= v <= 2100):
                vals.append(v)
        return max(vals) if vals else 0.0

    def pdf_compare(path: Path, year: int):
        result = {"target_sales":0.0, "previous_sales":0.0}
        try:
            import pdfplumber
            candidates = {"target":[], "previous":[]}
            with pdfplumber.open(path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text(x_tolerance=2, y_tolerance=3) or ""
                    for line in text.splitlines():
                        key = norm(line); v = money_value(line)
                        if not v:
                            continue
                        if "meta" in key or "presupuesto" in key or "objetivo" in key:
                            candidates["target"].append(v)
                        if str(year-1) in key or "ano pasado" in key or "año pasado" in key or "ano anterior" in key or "año anterior" in key:
                            candidates["previous"].append(v)
                    try:
                        tables = page.extract_tables() or []
                    except Exception:
                        tables = []
                    for table in tables:
                        rows = [[str(c or "") for c in (row or [])] for row in (table or []) if row]
                        if not rows:
                            continue
                        width = max(len(r) for r in rows)
                        for r in rows:
                            r.extend([""]*(width-len(r)))
                        head = [" ".join(r[c] for r in rows[:min(4,len(rows))]) for c in range(width)]
                        meta_cols = [i for i,h in enumerate(head) if any(x in norm(h) for x in ("meta","presupuesto","objetivo"))]
                        prev_cols = [i for i,h in enumerate(head) if str(year-1) in norm(h) or any(x in norm(h) for x in ("ano pasado","ano anterior","venta anterior"))]
                        for row in rows[1:]:
                            for i in meta_cols:
                                if i < len(row):
                                    v = money_value(row[i])
                                    if v: candidates["target"].append(v)
                            for i in prev_cols:
                                if i < len(row):
                                    v = money_value(row[i])
                                    if v: candidates["previous"].append(v)
            if candidates["target"]: result["target_sales"] = max(candidates["target"])
            if candidates["previous"]: result["previous_sales"] = max(candidates["previous"])
        except Exception as exc:
            result["error"] = f"{type(exc).__name__}: {exc}"
        return result

    def entries():
        out = []
        for raw in list((m.load_manifest() or {}).get("sales") or []):
            e = dict(raw)
            y, mo = int(e.get("year") or 0), int(e.get("month") or 0)
            if y <= 0 or mo not in range(1,13):
                continue
            if num(e.get("target_sales")) <= 0 or num(e.get("previous_sales")) <= 0:
                path = m.resolve_entry_path(e)
                if path.exists() and path.suffix.lower() == ".pdf":
                    cmp = pdf_compare(path, y); upd = {}
                    if num(e.get("target_sales")) <= 0 and num(cmp.get("target_sales")) > 0: upd["target_sales"] = cmp["target_sales"]
                    if num(e.get("previous_sales")) <= 0 and num(cmp.get("previous_sales")) > 0: upd["previous_sales"] = cmp["previous_sales"]
                    if upd:
                        try: m.update_entry("sales", str(e.get("id") or ""), **upd); e.update(upd)
                        except Exception: pass
            out.append(e)
        return out

    def canon(v):
        s = " ".join(str(v or "Compañía").split()).strip() or "Compañía"
        return "Compañía" if norm(s) in ("compania","company") else s

    @m.app.get("/api/commercial-sales-summary-v167")
    def sales_summary(request: Request, year: int|None=None, through_month: int|None=None):
        m.require_user(request)
        yy = int(year or datetime.now().year); cut = max(1, min(12, int(through_month or 12)))
        es = entries(); latest = {}
        for e in es:
            key = (int(e.get("year") or 0), int(e.get("month") or 0), canon(e.get("store")))
            old = latest.get(key)
            if old is None or str(e.get("uploaded_at") or "") >= str(old.get("uploaded_at") or ""): latest[key] = e
        def values(y, mo):
            vals = [e for (ey,em,_),e in latest.items() if ey == y and em == mo]
            company = [e for e in vals if canon(e.get("store")) == "Compañía"]
            use = company if company else vals
            return {
                "sales":sum(num(e.get("total_sales")) for e in use),
                "pieces":sum(num(e.get("total_pieces")) for e in use),
                "prev":sum(num(e.get("previous_sales")) for e in use),
                "goal":sum(num(e.get("target_sales")) for e in use),
            }
        with m.db() as con:
            manual = {int(r["month"]):num(r["target"]) for r in con.execute("SELECT month,target FROM sales_goals WHERE year=? AND store='Compañía'", (yy,)).fetchall()}
        labels = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]; months = []
        for mo in range(1,13):
            cur = values(yy,mo); prev = values(yy-1,mo)
            current = cur["sales"]; previous = prev["sales"] or cur["prev"]; goal = manual.get(mo,0.0) or cur["goal"]
            months.append({"month":mo,"label":labels[mo-1],"target":goal,"current":current,"previous":previous,"pieces":cur["pieces"],
                           "diff_goal":current-goal if goal else None,"pct_goal":(current/goal-1)*100 if goal else None,
                           "diff_previous":current-previous if previous else None,"pct_previous":(current/previous-1)*100 if previous else None})
        use = months[:cut]; tc=sum(x["current"] for x in use); tg=sum(x["target"] for x in use); tp=sum(x["previous"] for x in use)
        return {"year":yy,"previous_year":yy-1,"months":months,"available_years":sorted({int(e.get("year") or 0) for e in es if int(e.get("year") or 0)>0}|{yy,yy-1},reverse=True),
                "totals":{"current":tc,"target":tg,"previous":tp,"diff_goal":tc-tg if tg else None,"pct_goal":(tc/tg-1)*100 if tg else None,
                          "diff_previous":tc-tp if tp else None,"pct_previous":(tc/tp-1)*100 if tp else None}}

    @m.app.get("/api/commercial-sales-stores-v167")
    def sales_stores(request: Request, year: int|None=None, month: int|None=None):
        m.require_user(request)
        yy = int(year or datetime.now().year); mo = max(1,min(12,int(month or datetime.now().month)))
        es=entries(); latest={}
        for e in es:
            ey, em, st = int(e.get("year") or 0), int(e.get("month") or 0), canon(e.get("store"))
            if ey not in (yy, yy-1) or em != mo: continue
            key=(ey,st); old=latest.get(key)
            if old is None or str(e.get("uploaded_at") or "") >= str(old.get("uploaded_at") or ""): latest[key]=e
        stores=sorted({st for _,st in latest if st!="Compañía"})
        if not stores and any(st=="Compañía" for _,st in latest): stores=["Compañía"]
        with m.db() as con:
            goals={str(r["store"]):num(r["target"]) for r in con.execute("SELECT store,target FROM sales_goals WHERE year=? AND month=?", (yy,mo)).fetchall()}
        rows=[]
        for st in stores:
            cur=latest.get((yy,st),{}); prev=latest.get((yy-1,st),{})
            current=num(cur.get("total_sales")); previous=num(prev.get("total_sales")) or num(cur.get("previous_sales")); goal=goals.get(st,0.0) or num(cur.get("target_sales"))
            rows.append({"store":st,"target":goal,"current":current,"previous":previous,"pieces":num(cur.get("total_pieces")),
                         "diff_goal":current-goal if goal else None,"pct_goal":(current/goal-1)*100 if goal else None,
                         "diff_previous":current-previous if previous else None,"pct_previous":(current/previous-1)*100 if previous else None})
        return {"year":yy,"month":mo,"rows":rows}

    m._V167_BACKEND = True
    print("[V167-BACKEND] rutas/tendencia/ventas instaladas.", flush=True)
