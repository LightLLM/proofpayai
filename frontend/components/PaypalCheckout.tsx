'use client';
import {useEffect,useRef,useState} from 'react';
import {call,Config} from '../lib/api';
import {AlertCircle,LockKeyhole,ShieldCheck} from 'lucide-react';

type PaypalButtonsInstance={render:(element:HTMLElement)=>Promise<void>|void;close?:()=>void};
type PaypalGlobal={Buttons:(options:{style?:Record<string,string>;createOrder:()=>Promise<string>;onApprove:(data:{orderID:string})=>Promise<void>;onError:(error:unknown)=>void;onCancel:()=>void})=>PaypalButtonsInstance};
declare global{interface Window{paypal?:PaypalGlobal}}

export default function PaypalCheckout({rid,config,onComplete}:{rid:string;config:Config|null;onComplete:()=>void}){
 const el=useRef<HTMLDivElement>(null);const [error,setError]=useState('');const [notice,setNotice]=useState('');
 useEffect(()=>{
  if(!config?.paypal_configured||!el.current)return;
  let cancelled=false;let btn:PaypalButtonsInstance|undefined;
  const mount=()=>{
   if(cancelled||!window.paypal||!el.current)return;
   el.current.replaceChildren();
   btn=window.paypal.Buttons({style:{layout:'vertical',color:'gold',shape:'rect',label:'paypal'},
    createOrder:async()=>{setError('');setNotice('Creating a PayPal sandbox order…');const order=await call<{id:string}>(`/api/requests/${rid}/paypal/create-order`,{method:'POST'});return order.id},
    onApprove:async(data)=>{try{setNotice('Verifying PayPal capture…');await call(`/api/requests/${rid}/paypal/capture`,{method:'POST',body:JSON.stringify({paypal_order_id:data.orderID})});setNotice('Sandbox payment verified.');onComplete()}catch(e){setError(e instanceof Error?e.message:String(e))}},
    onError:(e)=>{setError(`PayPal checkout error: ${String(e)}`);setNotice('')},onCancel:()=>setNotice('Buyer cancelled checkout. No payment confirmed.')});
   void btn.render(el.current);
  };
  if(window.paypal){mount()}else{
   const script=document.createElement('script');script.src=`https://www.paypal.com/sdk/js?client-id=${encodeURIComponent(config.paypal_client_id)}&currency=USD&intent=capture&components=buttons`;
   script.async=true;script.dataset.proofpay='paypal';script.onload=mount;script.onerror=()=>setError('PayPal SDK could not load. Check network and browser blockers.');document.body.appendChild(script);
  }
  return()=>{cancelled=true;btn?.close?.();document.querySelector('script[data-proofpay="paypal"]')?.remove()};
 },[rid,config?.paypal_client_id,config?.paypal_configured,onComplete]);
 if(!config?.paypal_configured)return <div className="checkout-placeholder"><LockKeyhole size={20}/><div><strong>Connect sandbox credentials to pay</strong><p>Set PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET in backend/.env. Other procurement features work without them.</p></div></div>;
 return <div className="checkout"><div className="sandbox-box"><ShieldCheck size={17}/> Sandbox only · An authorized buyer must approve within PayPal</div><div ref={el} className="paypal-target"/>{notice&&<p className="hint">{notice}</p>}{error&&<p className="error"><AlertCircle size={14}/>{error}</p>}</div>
}
