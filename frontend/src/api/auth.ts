import {request,post} from './client';export const authApi={login:(email:string,password:string)=>post('/auth/login',{email,password}),me:()=>request('/auth/me')};
