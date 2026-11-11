import type { Data } from './api'
export function funnelRoute(step:string,pack:Data):string
export function paymentSummary(user:Data):string
export function saveSettingsPatchWith(request:(path:string,body?:Data)=>Promise<Data>,patch:Data):Promise<Data>
export function realPaidSummary(user:Data):string
export function friendsSummary(user:Data):string
export function attemptsSummary(user:Data):string
export function inviteTries(user:Data):number
