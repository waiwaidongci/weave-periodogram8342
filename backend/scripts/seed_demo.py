import json
import numpy as np
from sqlalchemy import select,func
from src.config.database import Base,engine,SessionLocal
from src.models import User,TraverseStudy,TraversePoint,FrequencyPlan,SpectrumRun,WeaveNote
from src.utils.security import hash_password
from src.utils.serialize import row
from src.services.analysis import analyze

def seed():
 Base.metadata.create_all(engine)
 with SessionLocal() as db:
  for role,name in [('admin','方绎 · 织纹研究负责人'),('analyst','林纬 · 谱分析员'),('viewer','苏纾 · 补测观察员')]:
   if not db.scalar(select(User).where(User.email==f'{role}@lingdu.demo')):db.add(User(email=f'{role}@lingdu.demo',name=name,role=role,password_hash=hash_password('Lingdu2026!')))
  db.commit();rng=np.random.default_rng(234);names=['LD-34A 十八毫米纹理','LD-34B 双峰织片','LD-34C 恒厚对照']
  for index,name in enumerate(names):
   study=db.scalar(select(TraverseStudy).where(TraverseStudy.name==name))
   if not study:
    study=TraverseStudy(name=name,filename=f'ld-traverse-{index+1}-202611.csv',description=['独立不等距测线，预设18mm合成结构','多个频率共存，不能仅凭峰认定制造原因','恒定厚度RSS0为0，无定义谱'][index]);db.add(study);db.flush();x=np.r_[0.,np.cumsum(rng.uniform(.8,2.3,119))];t=x-x[0];y=.5+.075*np.cos(2*np.pi*t/18-.7)+rng.normal(0,.014,120) if index==0 else .55+.055*np.sin(2*np.pi*t/30)+.04*np.cos(2*np.pi*t/12)+rng.normal(0,.014,120) if index==1 else np.full(120,.5)
    for i,(position,value) in enumerate(zip(x,y)):db.add(TraversePoint(study_id=study.id,reference=f'LD{index+1}-P{i+1:03d}',position=float(position),thickness=float(value)))
    db.commit()
   nameplan=f'LD{index+1}预设10至90毫米频率计划'
   if not db.scalar(select(FrequencyPlan).where(FrequencyPlan.name==nameplan)):db.add(FrequencyPlan(study_id=study.id,name=nameplan,protocol='看数据前固定周期范围10..90mm，201等频网格；不按测试结果选范围。',min_frequency=1/90,max_frequency=1/10,grid_size=201,frequencies=np.linspace(1/90,1/10,201).tolist(),permutations=199,seed=234,created_by='analyst@lingdu.demo'));db.commit()
  run=db.scalar(select(SpectrumRun).where(SpectrumRun.name=='A织片冻结网格谱峰研究'))
  if not run:
   study=db.scalar(select(TraverseStudy).where(TraverseStudy.name==names[0]));points=[row(x) for x in db.scalars(select(TraversePoint).where(TraversePoint.study_id==study.id).order_by(TraversePoint.position))];plan=db.scalar(select(FrequencyPlan).where(FrequencyPlan.study_id==study.id));planrow=row(plan);result=analyze(row(study),points,planrow);run=SpectrumRun(study_id=study.id,plan_id=plan.id,name='A织片冻结网格谱峰研究',source_snapshot={'study':row(study),'points':points},plan_snapshot=planrow,status='completed',result=result,peak_frequency=result['best']['frequency'],max_power=result['observed_max_power'],global_p=result['global_test']['global_p'],created_by='analyst@lingdu.demo');db.add(run);db.commit()
  if not db.scalar(select(WeaveNote).where(WeaveNote.name=='A织片不等距补测初稿')):db.add(WeaveNote(run_id=run.id,name='A织片不等距补测初稿',interpretation='谱峰和全网格p提供空间周期证据，不能认定织机制造原因。',next_step='另取独立织片，预先保持频率计划并补测不等距位置，核对采样窗口和混叠。',result_snapshot=run.result,created_by='analyst@lingdu.demo'));db.commit()
  counts={m.__tablename__:db.scalar(select(func.count()).select_from(m)) for m in [User,TraverseStudy,TraversePoint,FrequencyPlan,SpectrumRun,WeaveNote]};print(json.dumps(counts));return counts
if __name__=='__main__':seed()
