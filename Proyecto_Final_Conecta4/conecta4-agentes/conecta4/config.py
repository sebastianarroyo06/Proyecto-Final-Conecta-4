"""
Configuración de los agentes: algoritmos disponibles, niveles de
dificultad y una función para crear cada agente por nombre.

La dificultad se controla con el parámetro de búsqueda de cada algoritmo
(más búsqueda = mejor juego, pero más tiempo por jugada):

    Minimax    -> profundidad límite d
    Alfa-beta  -> profundidad límite d
    MCTS       -> número de simulaciones N por jugada
"""
from conecta4.agentes import (AgenteAleatorio, AgenteAlfaBeta, AgenteMCTS,
                              AgenteMinimax)

# Identificadores de los algoritmos y su nombre para mostrar
ALGORITMOS = {
    'minimax': 'Minimax',
    'alfabeta': 'Alfa-beta',
    'mcts': 'MCTS',
    'aleatorio': 'Aleatorio',
}

NIVELES = ['facil', 'medio', 'dificil']

NOMBRES_NIVELES = {'facil': 'Fácil', 'medio': 'Medio', 'dificil': 'Difícil'}

# Parámetro de búsqueda de cada algoritmo según la dificultad
PARAMETROS = {
    'minimax': {'facil': 2, 'medio': 4, 'dificil': 6},
    'alfabeta': {'facil': 2, 'medio': 5, 'dificil': 8},
    'mcts': {'facil': 200, 'medio': 1000, 'dificil': 5000},
}


def crear_agente(juego, algoritmo: str, nivel: str = 'medio',
                 heuristica: str = 'h1', semilla: int = None,
                 parametro: int = None):
    """Crea un agente a partir de su nombre y su nivel de dificultad.

    Input:
        - juego, objeto Conecta4
        - algoritmo, 'minimax', 'alfabeta', 'mcts' o 'aleatorio'
        - nivel, 'facil', 'medio' o 'dificil'
        - heuristica, 'h1' o 'h2' (solo la usa alfa-beta)
        - semilla, entero para que las decisiones sean reproducibles
        - parametro (opcional), profundidad o número de simulaciones;
          si se da, reemplaza al valor del nivel de dificultad
    Output:
        - objeto agente con el método ``decidir(estado)``
    """
    if algoritmo == 'aleatorio':
        return AgenteAleatorio(juego, semilla=semilla)
    if parametro is None:
        parametro = PARAMETROS[algoritmo][nivel]
    if algoritmo == 'minimax':
        return AgenteMinimax(juego, max_lim=parametro, semilla=semilla)
    if algoritmo == 'alfabeta':
        return AgenteAlfaBeta(juego, max_lim=parametro,
                              heuristica=heuristica, semilla=semilla)
    if algoritmo == 'mcts':
        return AgenteMCTS(juego, time_lim=parametro, semilla=semilla)
    raise NameError(f'¡Algoritmo incorrecto! {algoritmo}')


def describir(algoritmo: str, nivel: str = 'medio', heuristica: str = 'h1'):
    """Texto corto con el algoritmo y su parámetro ('Alfa-beta h1 d=5')."""
    if algoritmo == 'aleatorio':
        return 'Aleatorio'
    parametro = PARAMETROS[algoritmo][nivel]
    if algoritmo == 'minimax':
        return f'Minimax d={parametro}'
    if algoritmo == 'alfabeta':
        return f'Alfa-beta {heuristica} d={parametro}'
    return f'MCTS N={parametro}'
