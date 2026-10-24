import unittest
from unittest.mock import patch
from datetime import datetime, timedelta
import copy
import picks
import app_datos
import escalera
import plantillas
import valor


class PreferenciasTest(unittest.TestCase):
    def test_solo_12_fuera_ganadores_empates_y_otras_dobles_dentro(self):
        for opcion in ('Home/Away',' Home / Away ','12','1/2'):
            self.assertTrue(picks.es_sin_empate('Double Chance',opcion))
            self.assertTrue(picks.excluido('Double Chance',opcion))
        for mercado,opcion in [('Match Winner','Home'),('Match Winner','Away'),('Match Winner','Draw'),
                ('Double Chance','Home/Draw'),('Double Chance','Draw/Away'),('First Half Winner','Home'),
                ('To Win Either Half','Away'),('Results/Both Teams Score','Home/Yes'),('Draw No Bet','Home'),
                ('Goals Over/Under','Over 1.5'),('Both Teams Score','Yes'),('Shots.1x2','Home')]:
            with self.subTest(mercado=mercado,opcion=opcion):
                self.assertFalse(picks.es_sin_empate(mercado,opcion))
                self.assertFalse(picks.excluido(mercado,opcion))

    def test_panel_no_recupera_un_12_futuro_de_la_cache(self):
        ahora = datetime(2026, 10, 25, 0, 30, tzinfo=picks.MADRID)
        p = {'mercado':'Double Chance','opcion':'Home/Away','fecha':'2026-10-25T17:30'}
        self.assertFalse(app_datos.registro_visible(p, ahora))
        self.assertTrue(app_datos.registro_visible(dict(p, fecha='2026-10-24T17:30'), ahora))
        self.assertTrue(app_datos.registro_visible(dict(p, opcion='Home/Draw'), ahora))

    def seleccion(self,i,mercado='Goals Over/Under',tipo='goles',cuota=1.4):
        dia=(datetime.now(picks.MADRID)+timedelta(days=1)).strftime('%Y-%m-%d')
        return {'partido_id':i,'mercado':mercado,'opcion':'Over 1.5' if tipo=='goles' else 'Home/Away',
                'tipo':tipo,'cuota':cuota,'frecuencia':.9,'ventaja':.1,'fecha':dia+'T20:00',
                'texto':'Más de 1,5 goles','detalle':'9/10'}

    def test_combinadores_y_escalera_rechazan_cache_con_resultados(self):
        a=self.seleccion(1,'Double Chance','resultado'); b=self.seleccion(2)
        self.assertIsNone(picks.combinar([a,b],1.8,2.4,2,2,2))
        self.assertIsNone(picks.combi_partido([dict(a,cuota=12)]))
        self.assertIsNone(escalera.elegir({'picks':[a,b]}))
        self.assertEqual(plantillas.mejores_para_lista([a,b]),[b])

    def test_plantillas_no_publican_combi_con_cuota_de_cache_prohibida(self):
        a=self.seleccion(1,'Double Chance','resultado'); b=self.seleccion(2)
        dia=a['fecha'][:10]
        d={'picks':[a,b], 'combis':{'cuota_3':{'picks':[a,b],'cuota':3.0}}}
        with patch.object(plantillas,'leer',return_value={}):
            self.assertEqual(plantillas.posts_del_dia(dia,d),[])

    def test_modelo_conserva_tabla_pero_no_recomienda_resultado(self):
        mod={'fiable':True}
        ex={'cuotas':{'Double Chance':[['Home/Away','2.0']], 'Match Winner':[['Home','2.0']], 'Goals Over/Under':[['Over 1.5','2.0']]}}
        with patch.object(valor,'modelo',return_value=mod),patch.object(valor,'prob_seleccion',return_value=.8),patch.object(valor,'prob_casa',return_value=.8):
            _,filas,elegidos=valor.evaluar({},ex,{}, {})
        self.assertEqual(len(filas),3)
        self.assertEqual([p['mercado'] for p in elegidos],['Match Winner','Goals Over/Under'])


if __name__=='__main__':
    unittest.main()
