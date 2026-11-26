"""Pruebas de los tres algoritmos y del solucionador exacto."""
import random

from conecta4.agentes import (AgenteAlfaBeta, AgenteMCTS, AgenteMinimax,
                              PlfromAlgo)
from conecta4.config import crear_agente
from conecta4.experimentos import comparar_jugada, jugar_partida, torneo
from conecta4.juego import Conecta4
from conecta4.solver import SolverExacto
from conecta4.utils import EnvfromGameAndPl2, Episode

juego = Conecta4()

# El jugador 1 gana si juega en la columna 3 (tres en vertical)
GANA_EN_1 = juego.desde_jugadas([3, 0, 3, 0, 3, 1])
# El jugador 1 debe bloquear la columna 0 (tres del rival en vertical)
BLOQUEO = juego.desde_jugadas([3, 0, 3, 0, 6, 0])


def test_minimax_gana_cuando_puede():
    agente = AgenteMinimax(juego, max_lim=2, semilla=0)
    assert agente.decidir(GANA_EN_1) == 3
    assert agente.metricas.valor > 0


def test_minimax_bloquea_la_amenaza():
    agente = AgenteMinimax(juego, max_lim=2, semilla=0)
    assert agente.decidir(BLOQUEO) == 0


def test_alfabeta_gana_y_bloquea():
    for heuristica in ('h1', 'h2', 'nula'):
        agente = AgenteAlfaBeta(juego, max_lim=4, heuristica=heuristica)
        assert agente.decidir(GANA_EN_1) == 3
        assert agente.decidir(BLOQUEO) == 0


def test_mcts_gana_y_bloquea():
    agente = AgenteMCTS(juego, time_lim=1500, semilla=1)
    assert agente.decidir(GANA_EN_1) == 3
    assert agente.decidir(BLOQUEO) == 0


def test_la_poda_no_cambia_el_valor_de_minimax():
    """Alfa-beta sin heurística debe dar el mismo valor que minimax a la
    misma profundidad, generando menos nodos."""
    rng = random.Random(7)
    for _ in range(15):
        num_fichas = rng.randint(4, 24)
        s = juego.desde_jugadas(juego.jugadas_aleatorias(num_fichas, rng))
        minimax = AgenteMinimax(juego, max_lim=4, semilla=0)
        alfabeta = AgenteAlfaBeta(juego, max_lim=4, heuristica='nula')
        minimax.decidir(s)
        alfabeta.decidir(s)
        assert minimax.metricas.valor == alfabeta.metricas.valor
        assert (alfabeta.metricas.nodos_generados
                <= minimax.metricas.nodos_generados)


def test_metricas_de_minimax_en_tablero_vacio():
    agente = AgenteMinimax(juego, max_lim=2, semilla=0)
    agente.decidir(juego.estado_inicial)
    m = agente.metricas
    assert m.nodos_generados == 7 + 49
    assert m.nodos_expandidos == 1 + 7
    assert m.evaluaciones == 49
    assert m.memoria_max == 3       # Pila: raíz + 2 niveles
    assert m.tiempo > 0


def test_mcts_es_reproducible_con_semilla():
    s = juego.desde_jugadas([3, 3, 2, 4])
    a = AgenteMCTS(juego, time_lim=300, semilla=42)
    b = AgenteMCTS(juego, time_lim=300, semilla=42)
    assert a.decidir(s) == b.decidir(s)
    assert a.visitas_acciones == b.visitas_acciones
    assert sum(a.visitas_acciones.values()) == 300


def test_traza_registra_los_primeros_niveles():
    agente = AgenteAlfaBeta(juego, max_lim=5, heuristica='h1')
    agente.decidir(juego.estado_inicial)
    eventos = agente.traza.eventos
    assert eventos[0]['tipo'] == 'entra' and eventos[0]['camino'] == ()
    assert eventos[-1]['tipo'] == 'sale' and eventos[-1]['camino'] == ()
    assert all(len(e['camino']) <= 3 for e in eventos)
    assert any(e['tipo'] == 'poda' for e in eventos)


def test_solver_coincide_con_minimax_completo():
    rng = random.Random(3)
    solver = SolverExacto(juego)
    for _ in range(5):
        s = juego.desde_jugadas(juego.jugadas_aleatorias(34, rng))
        exactos = solver.valores_acciones(s)
        minimax = AgenteMinimax(juego, max_lim=42, semilla=0)
        minimax.decidir(s)
        assert minimax.metricas.valores_acciones == exactos


def test_solver_reconoce_jugada_ganadora():
    rng = random.Random(11)
    jugadas = juego.jugadas_aleatorias(28, rng)
    s = juego.desde_jugadas(jugadas)
    solver = SolverExacto(juego)
    optimas = solver.jugadas_optimas(s)
    assert len(optimas) >= 1
    assert solver.es_optima(s, optimas[0]) is True
    assert solver.es_optima(juego.estado_inicial, 3) is None


def test_partida_completa_y_torneo():
    a = crear_agente(juego, 'alfabeta', 'facil', 'h1', semilla=0)
    b = crear_agente(juego, 'aleatorio', semilla=0)
    partida = jugar_partida(juego, a, b)
    assert partida['ganador'] in (0, 1, 2)
    assert juego.es_terminal(partida['estado_final'])
    configs = [{'algoritmo': 'alfabeta', 'nivel': 'facil'},
               {'algoritmo': 'aleatorio'}]
    partidas = torneo(juego, configs, aperturas=[[], [3]], semilla=0)
    assert len(partidas) == 4


def test_comparar_jugada_misma_instancia():
    configs = [{'algoritmo': 'minimax', 'nivel': 'facil'},
               {'algoritmo': 'alfabeta', 'nivel': 'facil'},
               {'algoritmo': 'mcts', 'nivel': 'facil'}]
    filas = comparar_jugada(juego, GANA_EN_1, configs, semilla=0)
    assert len(filas) == 3
    assert filas[0]['accion'] == 3 and filas[1]['accion'] == 3


def test_episodio_con_las_clases_del_curso():
    """Los agentes funcionan con Episode y EnvfromGameAndPl2 del curso."""
    juego_local = Conecta4()
    otro = AgenteMinimax(juego_local, max_lim=2, semilla=0)
    env = EnvfromGameAndPl2(juego_local, otro)
    agente = AgenteAlfaBeta(juego_local, max_lim=4, heuristica='h1')
    episodio = Episode(environment=env, agent=agente,
                       model_name='alfa-beta', num_rounds=21)
    datos = episodio.run()
    assert episodio.done
    assert len(datos) >= 4
    # PlfromAlgo también sirve para crear agentes a partir de una función
    jugador = PlfromAlgo(lambda s: juego_local.acciones(s)[0])
    jugador.states.append(juego_local.estado_inicial)
    assert jugador.make_decision() == 0


def test_alfabeta_con_heuristica_coincide_con_minimax_con_heuristica():
    """Con la misma función de evaluación y la misma profundidad, la poda
    alfa-beta devuelve el mismo valor que minimax sin poda."""
    rng = random.Random(5)
    for _ in range(6):
        num_fichas = rng.randint(2, 22)
        s = juego.desde_jugadas(juego.jugadas_aleatorias(num_fichas, rng))
        for heuristica in ('h1', 'h2'):
            minimax = AgenteMinimax(juego, max_lim=4, semilla=0)
            minimax.heuristica = heuristica     # Minimax con evaluación
            alfabeta = AgenteAlfaBeta(juego, max_lim=4,
                                      heuristica=heuristica)
            minimax.decidir(s)
            alfabeta.decidir(s)
            assert abs(minimax.metricas.valor
                       - alfabeta.metricas.valor) < 1e-9
