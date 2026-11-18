const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const html = fs.readFileSync('docs/index.html', 'utf8');
const source = html.match(/<script>([\s\S]*?)<\/script>/)[1];
const context = vm.createContext({
  document: {querySelector: () => ({innerHTML: '', textContent: '', classList: {add(){}, remove(){}}}), addEventListener(){}},
  localStorage: {getItem(){return null}, setItem(){}},
  location: {pathname: '/'}, window: {}, navigator: {},
  setInterval(){}, setTimeout(){}, fetch: () => new Promise(() => {}), console,
});
vm.runInContext(source, context);
assert.ok(vm.runInContext('icono({estado:"no_jugo"})', context).includes('No jugó'));
assert.ok(!vm.runInContext('icono({estado:"no_jugo"})', context).includes('⏳'));
assert.ok(vm.runInContext('icono({estado:"sin_datos",estado_partido:"FT"})', context).includes('Sin datos'));
vm.runInContext(`
D = {generado:'2026-10-24 18:30', hoy:'2026-10-24', manana:'2026-10-25',
  dias:{'2026-10-24':{picks:[{partido_id:2,texto:'Más de 1,5 goles',cuota:1.4,estado:'verde'}]}},
  publicados_hoy:[], partidos:[
    {id:1,fecha:'2026-10-23T20:00',local:'Viejo',visitante:'Ayer',estado:'2H',actualizado:'2026-10-23T21:00',goles:[0,0]},
    {id:2,fecha:'2026-10-24T18:00',local:'EquipoEnJuego',visitante:'Hoy',estado:'2H',actualizado:'2026-10-24T18:29',goles:[2,0]},
    {id:3,fecha:'2026-10-24T16:00',local:'Finalizado',visitante:'Terminado',estado:'FT',goles:[1,0]}
  ]};
`, context);
let live = vm.runInContext('vDirecto()', context);
assert.ok(live.includes('EquipoEnJuego'));
assert.ok(!live.includes('Viejo'));
assert.ok(!live.includes('Finalizado'));
assert.ok(live.includes('✅'));
let finals = vm.runInContext('vDirecto("terminados")', context);
assert.ok(finals.includes('Finalizado'));
assert.ok(!finals.includes('EquipoEnJuego'));
vm.runInContext('D.partidos[1].estado="FT"', context);
assert.ok(!vm.runInContext('vDirecto()', context).includes('EquipoEnJuego'));
assert.ok(vm.runInContext('vDirecto("terminados")', context).includes('EquipoEnJuego'));
assert.ok(html.includes('src="logo.png?v=cl4"'));
const pub = fs.readFileSync('docs/publica/index.html','utf8');
assert.ok(pub.includes('src="../logo.png?v=cl4"'));
assert.ok(pub.includes('href="../icono-180.png?v=cl5"'));
for (const dir of ['docs','docs/publica']) {
  const manifest=JSON.parse(fs.readFileSync(dir+'/manifest.json','utf8'));
  assert.ok(manifest.icons.some(i=>i.sizes==='192x192'));
  assert.ok(manifest.icons.some(i=>i.sizes==='512x512'));
  for(const icon of manifest.icons) assert.ok(fs.existsSync(dir+'/'+icon.src.split('?')[0]));
}
console.log('Panel: directo sin partidos antiguos, traslado a terminados, aciertos y logo correctos.');

assert.ok(vm.runInContext('progresoPick({progreso:{texto:"1 de 2 paradas",porcentaje:50}})', context).includes('width:50%'));
assert.ok(vm.runInContext('avisoDatos(new Date(Date.now()-25*60000).toISOString(),true)', context).includes('Datos atrasados'));
assert.ok(!vm.runInContext('avisoDatos(new Date(Date.now()-5*60000).toISOString(),true)', context).includes('Datos atrasados'));
vm.runInContext(`D.resumenes={'2026-10-24':{cuentas:{verde:1,rojo:2,sin_resolver:1,pendiente:0,sin_datos:0,no_jugo:1},combis:[{titulo:'Segura',estado:'no_jugo'}]}}`,context);
assert.ok(vm.runInContext('vResumen()',context).includes('Jugador sin participación'));
vm.runInContext(`D.bot={redes:{},claves_caducan:'2026-12-21',errores:[{post:'Falló',fecha:'2026-10-24T18:00',red:'telegram',error:'Telegram 429',clave:'abc',reintentable:true}],spam:[]}`,context);
assert.ok(vm.runInContext('vBot()',context).includes('https://t.me/combilocas_publica_bot?start=retry_abc'));
vm.runInContext(`D.bot.errores[0].reintentable=false;D.bot.errores[0].bloqueo='Fuera de plazo'`,context);
assert.ok(!vm.runInContext('vBot()',context).includes('start=retry_'));

// 18/11: pestaña 📲 Telegram del panel (docs/panel): botones que escriben en control.json
{
  const ph = fs.readFileSync('docs/panel/index.html', 'utf8');
  const src = ph.match(/<script>([\s\S]*?)<\/script>/)[1].replace(/\ncargar\(\);\s*$/, '\n');
  const almacen = {};
  const ctx = vm.createContext({
    document: {querySelector: () => ({innerHTML: '', textContent: '', style: {}, value: ''}), addEventListener(){}},
    localStorage: {getItem: k => almacen[k] ?? null, setItem: (k, v) => { almacen[k] = String(v); }, removeItem: k => { delete almacen[k]; }},
    window: {}, navigator: {}, setTimeout(){}, fetch: () => new Promise(() => {}), console, Intl, TextEncoder, TextDecoder, atob, btoa,
  });
  vm.runInContext(src, ctx);
  assert.equal(vm.runInContext('tab', ctx), 'tg');   // se abre en Telegram
  // aprobar = lo mismo que el «✅ Publicar» del bot; no se duplica
  vm.runInContext('var c = {aprobados:{}, cancelados:["x"]}', ctx);
  assert.equal(vm.runInContext('TG_ACC.aprobar(c, "v1", "2026-11-18T10:00")', ctx), true);
  assert.equal(vm.runInContext('c.aprobados.v1', ctx), '2026-11-18T10:00');
  assert.equal(vm.runInContext('TG_ACC.aprobar(c, "v1", "2026-11-18T11:00")', ctx), false);
  assert.equal(vm.runInContext('TG_ACC.cancelar(c, "p2"); TG_ACC.nosale(c, "p2"); c.cancelados.filter(x=>x==="p2").length', ctx), 1);
  assert.equal(vm.runInContext('TG_ACC.recuperar(c, "x"); c.cancelados.includes("x")', ctx), false);
  // base64 con emojis y tildes ida y vuelta (control.json lleva textos con emojis)
  assert.equal(vm.runInContext('b64aTexto(textoAb64("✅ Ñandú 🇩🇰"))', ctx), '✅ Ñandú 🇩🇰');
  assert.match(vm.runInContext('horaMadrid(new Date("2026-11-18T09:05:00Z"))', ctx), /^2026-11-18T10:05$/);
  vm.runInContext(`D = {comentarios:[], redes:[], telegram:{hoy:'2026-11-17', picks:1, cuenta:{verde:0,rojo:0,va_bien:1,va_mal:0,pendiente:0},
    aprobar:[{id:'v9', fecha:'2026-11-17T21:55', tipo:'Verde', titulo:'Gol en Alemania', partido:'', texto:'PARA DENTRO', foto:null, por:'Varias patas', falta_cuota:false}],
    proximo:[{id:'p8', fecha:'2026-11-17T22:15', tipo:'Verde', titulo:'Ambos marcan', partido:'', texto:'t', foto:null}],
    enviados:[{id:'e1', fecha:'2026-11-17T19:00', hora:'19:00', mid:524, tipo:'Pick de Claude', titulo:'Ambos marcan en Israel – Austria', partido:'Israel – Austria', texto:'t', foto:null,
      directo:{estado:'va_mal', picks:[{texto:'Ambos marcan', partido:'Israel – Austria', estado:'va_mal', marcador:[1,0], minuto:60, fin:false, progreso:'1 de 2 equipos que marcan'}]}}],
    no_salen:[], avisos:[{hora:'14:53', t:'🚫 prohibido'}], pausa:false}}`, ctx);
  let v = vm.runInContext('vTelegram()', ctx);
  assert.ok(v.includes('Conecta la app'));                       // sin clave: pide conectar…
  assert.ok(v.includes('disabled'));                              // …y los botones no hacen nada
  assert.ok(v.includes('🟠 Va mal') && v.includes("1-0 · 60'"));  // estado y marcador en directo
  assert.ok(v.includes('🚫 prohibido'));
  almacen.cl_token_github = 'x';
  v = vm.runInContext('vTelegram()', ctx);
  assert.ok(!v.includes('Conecta la app') && v.includes("tgAccion('aprobar','v9')") && v.includes("tgAccion('cancelar','p8')"));
  assert.ok(!v.includes('github_pat_') || v.includes('placeholder'));   // la clave nunca se pinta
  vm.runInContext('tgHecho("v9", {acc:"aprobar", estado:"ok"})', ctx);
  v = vm.runInContext('vTelegram()', ctx);
  assert.ok(v.includes('Aprobado: sale en la próxima vuelta') && !v.includes("tgAccion('aprobar','v9')"));
  console.log('Panel 📲 Telegram: aprobar/cancelar en control.json, directo, avisos y clave.');
}
