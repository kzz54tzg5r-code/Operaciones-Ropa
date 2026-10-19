"""Bono 1: reporting uses the original scores and one consistent source response."""
from types import SimpleNamespace
from fastapi import FastAPI,Request
from v313_bonus_visual_and_cut_patch import bonus1_source_rows,install


def source():
    return {"ranking":[
        {"store":"Olivar","sales_pct":41.7,"sales_actual":417,"sales_goal":1000,"ddi_pct":None,"attendance_pct":100,"attendance_provisional":True,"score":40.9,"score_ready":False,"rank":None},
        {"store":"Centro","sales_pct":100,"sales_actual":1000,"sales_goal":1000,"ddi_pct":0,"attendance_pct":0,"attendance_provisional":False,"score":50,"score_ready":True,"rank":1}],"processing":{"capacity":True},"source_dates":{"opening_capacity":"2026-09-29","current_capacity":"2026-10-13"}}


def test_original_partial_score_and_zero_values_are_not_recalculated():
    original=source();rows=bonus1_source_rows(original)
    assert rows[0]["score"]==40.9 and rows[0]["rank"] is None
    assert rows[0]["score_partial"] is True
    assert "Preparando DDI" in rows[0]["missing_sources"][0]
    assert "Asistencia provisional" in rows[0]["missing_sources"][1]
    assert rows[1]["ddi_pct"]==0 and rows[1]["attendance_pct"]==0
    assert rows[1]["missing_sources"]==[]
    assert original["ranking"][0].get("display_order") is None
    assert [r["store"] for r in bonus1_source_rows(original,"Centro")]==["Centro"]


def test_summary_and_ranking_share_one_snapshot_and_respect_selected_store():
    app=FastAPI();calls=[]
    @app.get('/api/operation/sales-bonus-v293')
    def base(request:Request,month='',store=''):
        calls.append(store);return source()
    @app.get('/api/bonuses-v312')
    def final(request:Request,month='',store='Compañía',bonus=1):
        request.state.bonus_base_v312=base(request,month,store)
        return {"selected_store":store,"month":"2026-10","summary":{"sales_pct":100,"inventory":{}},"ranking":[]}
    install(SimpleNamespace(app=app,require_user=lambda request:{"role":"admin"}))
    endpoint=next(r.endpoint for r in app.routes if getattr(r,'path',None)=='/api/bonuses-v313')
    result=endpoint(Request({'type':'http'}),'2026-10','Centro',1)
    assert len(calls)==1
    assert result['legacy_components']['ddi_pct']==0
    assert result['legacy_components']['attendance_pct']==0
    assert result['legacy_components']['legacy_score_avg']==50
    assert result['bonus1_pending_stores']==0
    assert len(result['bonus1_rows'])==1
