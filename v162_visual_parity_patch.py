from fastapi.responses import HTMLResponse

def install(m):
    if getattr(m,'_V162_VISUAL',False): return
    css='''<style id="v162-visual-css">
.hero{min-height:84px!important;padding:14px 16px!important;border-radius:16px!important}.hero h1{font-size:22px!important}.hero p{font-size:8.5px!important}
#v158FilterBar{padding:9px!important;border-radius:15px!important;margin:7px 0!important}
#v158FilterBar .v158-grid{display:grid!important;grid-template-columns:repeat(3,minmax(0,1fr))!important;gap:6px!important}
#v158FilterBar .v158-field label{font-size:6.8px!important;margin:0 0 4px 2px!important}
#v158FilterBar .v158-field select,#v158FilterBar .v158-field input{height:40px!important;min-height:40px!important;border-radius:10px!important;font-size:10px!important;padding:6px 22px 6px 7px!important}
#v158FilterBar .v158-actions{grid-column:1/-1!important;width:100%!important}.v158-apply{width:100%!important;height:43px!important;border-radius:10px!important;font-size:12px!important}.v158-more,#v158Quick,#v158MorePanel{display:none!important}
#operativoNav:not(.hidden),#analysisNav:not(.hidden),.v125-tabs:not(.hidden){display:grid!important;grid-template-columns:repeat(5,minmax(0,1fr))!important;gap:4px!important;overflow:visible!important;padding:4px!important}
#operativoNav .switch,#analysisNav .switch,.v125-tab{min-width:0!important;padding:7px 2px!important;font-size:7.2px!important;white-space:normal!important;text-align:center!important;line-height:1.15!important}
.report-kpis,.kpis,.v149-kpis,.v126-kpis{display:grid!important;grid-template-columns:repeat(4,minmax(0,1fr))!important;gap:5px!important}
.report-kpi,.kpi,.v149-kpi,.v126-kpi{min-width:0!important;min-height:80px!important;padding:8px 5px!important;border-radius:12px!important;box-shadow:none!important}
.report-kpi .rk-label,.lab,.v149-kpi small,.v126-kpi small{font-size:6.1px!important;line-height:1.15!important}.report-kpi .rk-value,.val,.v149-kpi b,.v126-kpi b{font-size:16px!important;line-height:1!important;margin:6px 0 4px!important}.report-kpi .rk-sub,.note,.v149-kpi span,.v126-kpi span{font-size:5.8px!important;line-height:1.2!important}
.v162-staff{background:#eefbf4!important;border-color:#c7ead6!important}.v162-staff small,.v162-staff b{color:#168448!important}.title{font-size:17px!important;margin:9px 0 4px!important}.subtitle{font-size:8px!important}
@media(max-width:900px){.main{padding:7px 7px 74px!important}.report-kpis,.kpis,.v149-kpis,.v126-kpis{grid-template-columns:repeat(4,minmax(0,1fr))!important}}
</style>'''
    @m.app.middleware('http')
    async def _v162_visual(request,call_next):
        r=await call_next(request)
        if request.url.path!='/' or getattr(r,'status_code',200)!=200:return r
        b=b''
        async for c in r.body_iterator:b+=c
        h=b.decode('utf-8',errors='replace')
        if 'v162-visual-css' not in h:h=h.replace('</head>',css+'</head>',1)
        headers=dict(getattr(r,'headers',{}) or {});headers.pop('content-length',None);headers['Cache-Control']='no-store, no-cache, must-revalidate, max-age=0'
        return HTMLResponse(h,status_code=r.status_code,headers=headers)
    m._V162_VISUAL=True
    print('[V162] Visual boceto compacto activo.',flush=True)
