'use client';
import {AgGridReact} from 'ag-grid-react';
import {AllCommunityModule,ModuleRegistry,themeQuartz,ColDef} from 'ag-grid-community';
import {useMemo} from 'react';
import {Order} from '../lib/api';
ModuleRegistry.registerModules([AllCommunityModule]);
export default function SpendGrid({orders}:{orders:Order[]}){
 const theme=useMemo(()=>themeQuartz.withParams({backgroundColor:'#111b2b',foregroundColor:'#e9f0fa',headerBackgroundColor:'#19273a',borderColor:'#293a50',accentColor:'#2ed1b7',fontFamily:'Inter, ui-sans-serif, system-ui',fontSize:12}),[]);
 const columns=useMemo<ColDef<Order>[]>(()=>[
  {field:'id',headerName:'Purchase',flex:1.2,minWidth:145},
  {field:'offer_id',headerName:'Supplier offer',flex:1,minWidth:120},
  {field:'amount',headerName:'Total (USD)',flex:.7,minWidth:110,valueFormatter:x=>`$${Number(x.value).toFixed(2)}`},
  {field:'status',headerName:'Payment state',flex:1,minWidth:125},
  {field:'capture_id',headerName:'Capture reference',flex:1.2,minWidth:165,valueFormatter:x=>x.value||'—'}
 ],[]);
 return <div style={{height:Math.max(155,Math.min(350,orders.length*43+55)),width:'100%'}}><AgGridReact theme={theme} rowData={orders} columnDefs={columns} defaultColDef={{sortable:true,filter:true,resizable:true}} pagination={orders.length>6} paginationPageSize={6} overlayNoRowsTemplate={'No orders yet — approve a purchase and initiate checkout.'}/></div>
}
