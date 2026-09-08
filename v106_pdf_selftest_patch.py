"""V106: prueba de humo del generador Semanal/Mensual V105 al arrancar."""
from __future__ import annotations


def install(m):
    if getattr(m,'_V106_PDF_SELFTEST',False):return
    try:
        stores=[];rec=[]
        for i in range(17):
            name=f'Tienda {i+1:02d}'
            total=1800-i*75
            stores.append({
                'store':name,'is_project':i<5,'dev_pzs':max(total*.35,0),'muertos':0,
                'probador':0,'cajas':0,'pendiente_anterior':0,'total_pzs':total,
                'ingresos':total,'recorridos':i%3,'acondicionado':total*(.72 if i%4 else 0),
                'ubicado':total*(.65 if i%5 else 0),'pendiente_acondicionar':total*.28,
                'pendiente_ubicar':total*.35,
            })
            rec.append({
                'store':name,'dev_pzs':total*.35,'converted_pieces':total*.24,
                'conversion_pct':68-i,'return_value':total*120,'recovered_value':total*82,
                'recovery_pct':68.3,'pending_pieces':total*.11,'pending_value':total*38,
            })
        data={
            'period_value':'2026-W36','stores':stores,'recovery_by_store':rec,
            'metrics':{
                'total_pzs':23438,'ingresos':23438,'acondicionado':7999,'pct_acondicionado':34.1,
                'ubicado':8651,'pct_ubicado':36.9,'conversion_pct':72.4,'converted_pieces':15787,
                'recovery_pct':80.6,'recovered_value':4778204,'productivity_pct':134.1,
                'productivity_daily':1051,'pct_recorridos':2.0,'recorridos':16,
            },
        }
        week=m._build_operations_pdf(data,'Reporte Semanal','Compañía')
        month=dict(data);month['period_value']='2026-09'
        monthly=m._build_operations_pdf(month,'Reporte Mensual','Compañía')
        ok=week.startswith(b'%PDF') and monthly.startswith(b'%PDF') and len(week)>5000 and len(monthly)>5000
        if not ok:raise RuntimeError('salida PDF inválida o demasiado pequeña')
        print(f'[V106-SELFTEST] PDF Semanal/Mensual OK · bytes={len(week)}/{len(monthly)}.',flush=True)
    except Exception as exc:
        print(f'[V106-SELFTEST] ERROR {type(exc).__name__}: {exc}',flush=True)
    m._V106_PDF_SELFTEST=True
