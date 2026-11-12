export const fmt=(n:number,d=5)=>Number.isFinite(n)?n.toLocaleString('zh-CN',{maximumFractionDigits:d}):'—';export const clock=(v:string)=>new Date(v).toLocaleString('zh-CN',{hour12:false});
