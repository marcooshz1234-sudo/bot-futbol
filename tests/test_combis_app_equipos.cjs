// 20/11 (Marcos: «saber rápido de qué partido es cada línea»): partido arriba, grande, azul, con escudos y equipo del jugador
const fs=require('fs'), assert=require('assert'), vm=require('vm');
const html=fs.readFileSync(__dirname+'/../docs/index.html','utf8');
const f=html.slice(html.indexOf('function vCombis'), html.indexOf('function nav('));
const ctx={esc:s=>String(s), D:{combis_semana:{rango:['2026-11-21','2026-11-23'],combis:[{liga:'Serie A',cuota:3,patas:[
  {hora:'2026-11-21T15:00',partido:'Lazio–Lecce',texto:'Gustav Isaksen: comete 1+ falta',cuota:1.53,dato:'x',equipo:'Lazio',logo_l:'L.png',logo_v:'V.png'},
  {hora:'2026-11-21T18:00',partido:'Como–Cagliari',texto:'Ambos marcan',cuota:1.6,dato:'y'}]}]}}};
vm.createContext(ctx); vm.runInContext(f, ctx); const out=vm.runInContext('vCombis()', ctx);
assert.ok(out.includes('<b style="color:#3b82f6;font-size:16px">Lazio–Lecce</b>'), 'partido sin resaltar');
assert.ok(out.includes('L.png') && out.includes('V.png'), 'sin escudos');
assert.ok(out.includes('Gustav Isaksen (Lazio): comete'), 'sin equipo del jugador');
assert.ok(out.includes('Como–Cagliari') && out.includes('Ambos marcan'));
console.log('Combis: partido destacado con escudos y equipo del jugador.');
