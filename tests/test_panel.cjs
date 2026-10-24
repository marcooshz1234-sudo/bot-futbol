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
    {id:2,fecha:'2026-10-24T18:00',local:'Actual',visitante:'Hoy',estado:'2H',actualizado:'2026-10-24T18:29',goles:[2,0]},
    {id:3,fecha:'2026-10-24T16:00',local:'Finalizado',visitante:'Terminado',estado:'FT',goles:[1,0]}
  ]};
`, context);
let live = vm.runInContext('vDirecto()', context);
assert.ok(live.includes('Actual'));
assert.ok(!live.includes('Viejo'));
assert.ok(!live.includes('Finalizado'));
assert.ok(live.includes('✅'));
let finals = vm.runInContext('vDirecto("terminados")', context);
assert.ok(finals.includes('Finalizado'));
assert.ok(!finals.includes('Actual'));
vm.runInContext('D.partidos[1].estado="FT"', context);
assert.ok(!vm.runInContext('vDirecto()', context).includes('Actual'));
assert.ok(vm.runInContext('vDirecto("terminados")', context).includes('Actual'));
assert.ok(html.includes('src="logo.png?v=cl2"'));
const pub = fs.readFileSync('docs/publica/index.html','utf8');
assert.ok(pub.includes('src="../logo.png?v=cl2"'));
assert.ok(pub.includes('href="../icono-180.png?v=cl2"'));
for (const dir of ['docs','docs/publica']) {
  const manifest=JSON.parse(fs.readFileSync(dir+'/manifest.json','utf8'));
  assert.ok(manifest.icons.some(i=>i.sizes==='192x192'));
  assert.ok(manifest.icons.some(i=>i.sizes==='512x512'));
  for(const icon of manifest.icons) assert.ok(fs.existsSync(dir+'/'+icon.src.split('?')[0]));
}
console.log('Panel: directo sin partidos antiguos, traslado a terminados, aciertos y logo correctos.');
