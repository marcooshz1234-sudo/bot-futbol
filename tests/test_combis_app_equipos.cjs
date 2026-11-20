// 20/11 (Marcos): partido destacado con escudos y equipo del jugador; combis plegables; pestaña «Por equipo»
const fs=require('fs'), assert=require('assert'), vm=require('vm');
const html=fs.readFileSync(__dirname+'/../docs/index.html','utf8');
const f=html.slice(html.indexOf('function combiAbierta'), html.indexOf('function nav('))
  + html.slice(html.indexOf('function subTabs'), html.indexOf('\n', html.indexOf('function subTabs')));
const ls={};
const ctx={esc:s=>String(s).replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/'/g,'&#39;').replace(/</g,'&lt;'), sub:{}, pintar(){},
  guardado:k=>ls[k]||null, guardar:(k,v)=>{ls[k]=v}, D:{combis_semana:{rango:['2026-11-21','2026-11-23'],
  combis:[{liga:'Serie A',cuota:3,patas:[
    {hora:'2026-11-21T15:00',partido:'Lazio–Lecce',texto:'Gustav Isaksen: comete 1+ falta',cuota:1.53,dato:'x',equipo:'Lazio',logo_l:'L.png',logo_v:'V.png'},
    {hora:'2026-11-21T18:00',partido:'Como–Cagliari',texto:'Ambos marcan',cuota:1.6,dato:'y'}]}],
  equipos:[{equipo:"Nott'm Forest",liga:'Premier League',partido:"Nott'm Forest–Leeds",hora:'2026-11-22T15:00',logo:'F.png',cuota:2.2,
    patas:[{texto:"Nott'm Forest marca",cuota:1.4,dato:'z'},{texto:'Elanga: 1+ remate',cuota:1.57,dato:'w'}]}]}}};
vm.createContext(ctx); vm.runInContext(f, ctx);
let out=vm.runInContext('vCombis()', ctx);
assert.ok(out.includes('<b style="color:#3b82f6;font-size:16px">Lazio–Lecce</b>'), 'partido sin resaltar');
assert.ok(out.includes('L.png') && out.includes('Gustav Isaksen (Lazio): comete'));
assert.ok(out.includes('▲') && out.includes('Por equipo'));
vm.runInContext('plegarCombi("liga:Serie A", true)', ctx);           // plegar
out=vm.runInContext('vCombis()', ctx);
assert.ok(!out.includes('Gustav Isaksen') && out.includes('▼'), 'no se pliega');
vm.runInContext('sub.combis="equipo"', ctx);
out=vm.runInContext('vCombis()', ctx);
assert.ok(out.includes("Nott&#39;m Forest") && out.includes('F.png') && !out.includes('Elanga'), 'equipo: cerrada por defecto');
vm.runInContext(`plegarCombi("eq:Nott'm Forest|2026-11-22T15:00", false)`, ctx);
out=vm.runInContext('vCombis()', ctx);
assert.ok(out.includes('Elanga: 1+ remate'), 'equipo: no se abre');
console.log('Combis: plegables, por equipo, partido destacado con escudos.');
