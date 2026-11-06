export type Requirement={type:string;horsepower:number;voltage:number;rpm:number;shaft_inches:number;max_total_usd:number};
export type Offer={id:string;vendor:string;title:string;part:string;price_usd:number;shipping_usd:number;total_usd:number;lead_days:number;approved_vendor:boolean;reliability:number;eligible:boolean;reasons:string[];score:number};
export type Purchase={id:string;title:string;status:string;requirement:Requirement;selected_offer:string|null;ai_mode:string|null;ai_explanation:string|null;created_at:string};
export type AuditEvent={id:string;event:string;details:Record<string,unknown>;created_at:string};
export type Order={id:string;request_id:string;offer_id:string;amount:string;paypal_order_id:string|null;capture_id:string|null;status:string};
export type Detail=Purchase & {offers:Offer[];audit:AuditEvent[];order:Order|null};
export type Config={paypal_configured:boolean;paypal_client_id:string;ai_configured:boolean;sandbox_only:boolean};
export type Overview={requests:number;approved:number;completed:number;total_spend_usd:number;orders:Order[]};
export const API=process.env.NEXT_PUBLIC_API_URL||'http://localhost:8000';
export const operatorKey = 'proofpay_demo_operator_token';
export function saveOperatorToken(token:string){
 if(typeof window!=='undefined') sessionStorage.setItem(operatorKey,token.trim());
}
export function hasOperatorToken():boolean{
 return typeof window!=='undefined' && Boolean(sessionStorage.getItem(operatorKey));
}
export async function call<T>(path:string, options?:RequestInit):Promise<T>{
 const token=typeof window!=='undefined'?sessionStorage.getItem(operatorKey):null;
 const headers:Record<string,string>={'Content-Type':'application/json'};
 if(options?.method && options.method.toUpperCase()!=='GET' && token) headers['Authorization']='Bearer '+token;
 const res=await fetch(`${API}${path}`,{...options,headers:{...headers,...options?.headers},cache:'no-store'});
 if(!res.ok){const data=await res.json().catch(()=>({detail:'Request failed'}));throw new Error(data.detail||`HTTP ${res.status}`)}
 return res.json();
}
