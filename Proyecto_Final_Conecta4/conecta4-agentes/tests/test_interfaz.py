"""Pruebas de la lógica de la interfaz (no abren ninguna ventana)."""
import copy
import time

from conecta4.agentes import AgenteAlfaBeta, AgenteMCTS
from conecta4.juego import Conecta4
from gui.sesion import SesionPartida
from gui.vista_busqueda import ReproductorTraza, fantasmas_de

juego = Conecta4()


def test_reproductor_avanza_y_retrocede():
    """Retroceder y volver a avanzar deja el árbol en el mismo estado."""
    agente = AgenteAlfaBeta(juego, max_lim=5, heuristica='h1')
    accion = agente.decidir(juego.estado_inicial)
    rep = ReproductorTraza(agente.traza)
    rep.ir_a(60)
    nodos_60 = copy.deepcopy(rep.nodos)
    rep.ir_a(rep.total)
    assert () in rep.pv and (accion,) in rep.pv     # Variante principal
    assert rep.frontera() == 0      # Al final no queda nada pendiente
    rep.ir_a(60)                    # Retrocede
    assert rep.nodos == nodos_60
    assert len(fantasmas_de(rep, juego)) == len(rep.actual)


def test_reproductor_mcts_cuenta_las_simulaciones():
    agente = AgenteMCTS(juego, time_lim=200, semilla=3)
    accion = agente.decidir(juego.estado_inicial)
    rep = ReproductorTraza(agente.traza)
    rep.ir_a(rep.total)
    assert rep.nodos[()]['n'] == 200
    visitas = {c[0]: n['n'] for c, n in rep.nodos.items() if len(c) == 1}
    assert visitas == agente.visitas_acciones
    assert (accion,) in rep.pv


def _esperar(sesion, limite=20):
    inicio = time.time()
    while sesion.pendiente() is None and time.time() - inicio < limite:
        time.sleep(0.01)
    assert sesion.pendiente() is not None


def test_sesion_humano_contra_agente():
    config = {1: {'tipo': 'humano', 'nivel': 'facil', 'heuristica': 'h1'},
              2: {'tipo': 'alfabeta', 'nivel': 'facil', 'heuristica': 'h1'}}
    sesion = SesionPartida(juego, juego.estado_inicial, config, semilla=0)
    assert sesion.es_turno_humano()
    assert sesion.jugar_humano(3) is not None
    sesion.aplicar_pendiente()
    assert sesion.cursor == 1 and not sesion.es_turno_humano()
    sesion.solicitar_decision()         # El agente piensa en otro hilo
    _esperar(sesion)
    registro = sesion.pendiente()
    assert registro.metricas.nodos_generados > 0
    assert len(registro.traza) > 0
    sesion.aplicar_pendiente()
    assert sesion.cursor == 2 and sesion.es_turno_humano()
    # Retroceder conserva el historial; jugar otra cosa lo reemplaza
    sesion.retroceder()
    sesion.retroceder()
    assert sesion.cursor == 0 and len(sesion.historial) == 2
    sesion.jugar_humano(0)
    assert len(sesion.historial) == 1
    assert sesion.resumen(2) is None
