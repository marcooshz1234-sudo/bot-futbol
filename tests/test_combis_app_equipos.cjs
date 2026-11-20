// 20/11: en la pestaña Combis el nombre de los equipos va en negrita y de otro color
const fs=require('fs'), assert=require('assert');
const html=fs.readFileSync(__dirname+'/../docs/index.html','utf8');
const f=html.slice(html.indexOf('function vCombis'), html.indexOf('function nav('));
assert.ok(/<b style="color:#3b82f6">\$\{esc\(x\.partido\)\}<\/b>/.test(f), 'equipos sin resaltar');
console.log('Combis: equipos en negrita y color.');
