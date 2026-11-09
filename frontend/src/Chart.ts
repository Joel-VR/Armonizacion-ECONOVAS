import React from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts'
const data = [{mes:'Ene',actual:120,anterior:85},{mes:'Feb',actual:160,anterior:110},{mes:'Mar',actual:135,anterior:92},{mes:'Abr',actual:210,anterior:140},{mes:'May',actual:260,anterior:185},{mes:'Jun',actual:320,anterior:220},{mes:'Jul',actual:410,anterior:290},{mes:'Ago',actual:540,anterior:380},{mes:'Sep',actual:470,anterior:340},{mes:'Oct',actual:350,anterior:260},{mes:'Nov',actual:240,anterior:175},{mes:'Dic',actual:180,anterior:120}]
export function mountChart(element: HTMLElement): Root {
 const root = createRoot(element)
 root.render(React.createElement(ResponsiveContainer, {width:'100%',height:300, children: React.createElement(BarChart, {data, margin:{top:10,right:10,left:-20,bottom:0}}, React.createElement(CartesianGrid,{stroke:'#edf0ed',vertical:false}), React.createElement(XAxis,{dataKey:'mes',axisLine:false,tickLine:false,tick:{fill:'#929b95',fontSize:12}}), React.createElement(YAxis,{axisLine:false,tickLine:false,tick:{fill:'#929b95',fontSize:12}}), React.createElement(Tooltip), React.createElement(Legend), React.createElement(Bar,{dataKey:'anterior',name:'2024',fill:'#d7e3dc',radius:[4,4,0,0]}), React.createElement(Bar,{dataKey:'actual',name:'2025',fill:'#ef7544',radius:[4,4,0,0]}))}))
 return root
}
