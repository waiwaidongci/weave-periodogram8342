from sqlalchemy import select
from fastapi import HTTPException
from src.models import TraverseStudy,TraversePoint
from src.utils.serialize import row
from .validation import validate_points
from .audit import record

def create_study(db,data,actor):
 if db.scalar(select(TraverseStudy).where(TraverseStudy.name==data.name)):raise HTTPException(409,'测线研究名已存在')
 try:points=validate_points([p.model_dump() for p in data.points])
 except ValueError as error:raise HTTPException(422,str(error))
 study=TraverseStudy(**data.model_dump(exclude={'points'}));db.add(study);db.flush()
 for point in points:db.add(TraversePoint(study_id=study.id,**point))
 db.commit();record(db,actor,'study.imported',{'study_id':study.id,'points':len(points)});return row(study)

def source_data(db,id):
 study=db.get(TraverseStudy,id)
 if not study:raise HTTPException(404,'测线研究不存在')
 return row(study),[row(p) for p in db.scalars(select(TraversePoint).where(TraversePoint.study_id==id).order_by(TraversePoint.position))]

def edit_point(db,id,data,actor):
 point=db.get(TraversePoint,id)
 if not point:raise HTTPException(404,'测点不存在')
 _,points=source_data(db,point.study_id);candidate=[dict(p,position=data.position,thickness=data.thickness) if p['id']==id else p for p in points]
 try:validate_points(candidate)
 except ValueError as error:raise HTTPException(422,str(error))
 point.position=data.position;point.thickness=data.thickness;db.commit();record(db,actor,'point.revised',{'point_id':id});return row(point)
