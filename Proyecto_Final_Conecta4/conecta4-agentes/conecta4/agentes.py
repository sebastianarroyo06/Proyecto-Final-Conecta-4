"""
Agentes para el 4 en raya.

Las clases ``Agent``, ``Random`` y ``PlfromAlgo`` vienen del módulo
``agents.py`` del taller de Juegos del curso. Sobre esa base se
implementan los tres agentes del proyecto, todos basados en utilidad y
con un modelo del mundo (usan ``juego.resultado`` para simular jugadas):

    AgenteMinimax   -> minimax con profundidad limitada (no informado).
                       Adaptado del Ejercicio 1 del notebook de Juegos
                       (funciones minimax_search, max_value, min_value).
    AgenteAlfaBeta  -> alfa-beta con cutoff y función de evaluación,
                       H-Minimax (informado). Adaptado del método
                       ``_H_minimax_alfa_beta`` de ``ChessFinalist1``.
    AgenteMCTS      -> búsqueda en árboles Monte Carlo con UCB1 (UCT).
                       Adaptado del método ``program`` de
                       ``ChessFinalist2`` (selección, expansión,
                       simulación y backup).

En todos los agentes MAX es el jugador que está decidiendo (el que tiene
el turno en la raíz) y MIN es su rival.
"""
import random
from time import perf_counter

import numpy as np

from conecta4.datastruct import ArbolBusquedaJuego
from conecta4.heuristicas import HEURISTICAS, PESOS_H1, h1_ventanas
from conecta4.metricas import Metricas, Traza

# Orden en el que alfa-beta revisa las columnas: del centro a los bordes.
# Las jugadas centrales suelen ser las mejores, y revisar primero las
# mejores jugadas hace que la poda corte más ramas.
ORDEN_CENTRO = [3, 2, 4, 1, 5, 0, 6]


class BusquedaCancelada(Exception):
    """Se lanza cuando la interfaz pide detener una búsqueda en curso."""


# ======================================================================
# Clases base del curso (módulo agents.py del taller de Juegos)
# ======================================================================
class Agent:
    '''
    Defines the basic methods for the agent.
    '''

    def __init__(self):
        self.plan = []
        self.states = []
        self.actions = []
        self.rewards = [np.nan]
        self.dones = [False]
        self.turn = 0

    def make_decision(self):
        '''
        Agent makes a decision according to its model.
        '''
        # Chequeamos si ya el agente no tiene un plan (lista de acciones)
        if len(self.plan) == 0:
            # Usamos el programa para crear un plan
            self.program()
        try:
            # La acción a realizar es la primera del plan
            action = self.plan.pop(0)
        except IndexError:
            # ¡No hay plan!
            state = self.states[-1]
            raise Exception(f'¡Plan vacío! Revisar reglas en estado {state}')
        self.turn += 1
        return action

    def program(self):
        '''
        Debe ser modificada por cada subclase
        '''
        pass

    def reset(self):
        self.restart()

    def restart(self):
        '''
        Restarts the agent for a new trial.
        '''
        self.plan = []
        self.states = []
        self.actions = []
        self.rewards = [np.nan]
        self.dones = [False]
        self.turn = 0


class Random(Agent):
    '''Agente que deambula aleatoriamente.'''

    def __init__(self, choices: list):
        super().__init__()
        self.choices = choices

    def program(self):
        # Creamos un plan con una acción aleatoria
        accion = random.choice(self.choices)
        self.plan.append(accion)


class PlfromAlgo(Agent):
    '''
    Agente creado a partir de algoritmo (p.ej., minimax, alpha-search, etc.)
    '''

    def __init__(self, algorithm: any):
        super().__init__()
        self.algorithm = algorithm
        self.debug = False

    def program(self):
        state = self.states[-1]
        # El agente toma una acción de acuerdo al algoritmo
        action = self.algorithm(state)
        self.plan.append(action)


# ======================================================================
# Base común de los agentes del proyecto
# ======================================================================
class AgenteBusqueda(Agent):
    '''
    Base de los agentes de búsqueda adversaria del proyecto.

    Agrega a ``Agent`` lo que comparten los tres algoritmos:
        - el juego (modelo del mundo) y el jugador MAX,
        - las métricas de cada decisión,
        - la traza paso a paso que anima la interfaz gráfica,
        - el criterio de corte ``_is_cutoff`` y la evaluación ``_evaluar``.
    '''
    nombre = 'Agente'

    def __init__(self, game, max_lim: int = 4, heuristica: str = 'nula',
                 semilla: int = None, prof_traza: int = 3):
        super().__init__()
        self.game = game
        # Profundidad límite: número de jugadas que se miran hacia adelante
        self.max_lim = max_lim
        # Nombre de la función de evaluación: 'h1', 'h2' o 'nula'
        self.heuristica = heuristica
        # Generador aleatorio propio para que los experimentos sean
        # reproducibles (misma semilla -> mismas decisiones)
        self.rng = random.Random(semilla)
        self.prof_traza = prof_traza
        self.guardar_traza = True
        self.cancelar = False
        self.jugador = None         # Jugador MAX (se fija en cada decisión)
        self.metricas = None
        self.traza = None
        self.cotas_acciones = {}

    def program(self):
        state = self.states[-1]
        # El agente toma una acción de acuerdo a su algoritmo de búsqueda
        action = self.decidir(state)
        self.plan.append(action)

    def decidir(self, estado):
        '''
        Elige la jugada para el estado dado y registra las métricas.
        Input: estado, que es una np.array (6x7) no terminal
        Output: columna elegida (entero entre 0 y 6)
        '''
        self.cancelar = False
        self.jugador = self.game.player(estado)
        self.metricas = Metricas(algoritmo=self.descripcion())
        self.traza = Traza(self.nombre, estado, self.jugador,
                           self.prof_traza)
        self.cotas_acciones = {}
        arranca = perf_counter()                 # Inicializa cronómetro
        valor, accion = self._buscar(estado)     # Ejecuta el algoritmo
        para = perf_counter()                    # Detiene cronómetro
        self.metricas.tiempo = para - arranca
        self.metricas.valor = float(valor)
        self.metricas.accion = int(accion)
        return accion

    def _buscar(self, estado):
        '''Lo implementa cada algoritmo. Devuelve (valor, accion).'''
        raise NotImplementedError

    def descripcion(self):
        '''Nombre del agente con sus parámetros.'''
        return self.nombre

    # ------------------------------------------------------------------
    # Corte y evaluación (igual que en el taller de Juegos)
    # ------------------------------------------------------------------
    def _is_cutoff(self, estado, d):
        '''Criterio de detención: el juego terminó o se llegó a la
        profundidad límite.'''
        if self.game.es_terminal(estado):
            return True
        elif d >= self.max_lim:
            return True
        else:
            return False

    def _evaluar(self, estado):
        '''Valor de un estado en el que se detiene la búsqueda.

        Si el estado es terminal se usa la utilidad real del juego; si
        no, se estima con la función de evaluación (heurística).'''
        if self.game.es_terminal(estado):
            return self.game.utilidad(estado, self.jugador)
        funcion = HEURISTICAS[self.heuristica]
        return funcion(estado, self.jugador)

    # ------------------------------------------------------------------
    # Contadores y traza
    # ------------------------------------------------------------------
    def _visitar(self, d):
        '''Actualiza la profundidad máxima y la memoria (tamaño de la pila
        de la búsqueda en profundidad: los d + 1 nodos del camino).'''
        if self.cancelar:
            raise BusquedaCancelada()
        if d > self.metricas.profundidad_max:
            self.metricas.profundidad_max = d
            self.metricas.memoria_max = d + 1

    def _registrar(self, tipo, camino, **datos):
        '''Guarda un evento en la traza si el nodo está en los niveles
        que se muestran en la interfaz.'''
        if self.guardar_traza and len(camino) <= self.prof_traza:
            self.traza.registrar(tipo, camino, self.metricas, **datos)

    def _hoja(self, estado, camino):
        '''Evalúa un nodo en el que se detiene la búsqueda (hoja).'''
        if self.game.es_terminal(estado):
            self.metricas.terminales += 1
            clase = 'terminal'
        else:
            self.metricas.evaluaciones += 1
            clase = 'corte'
        valor = self._evaluar(estado)
        self._registrar('hoja', camino, valor=valor, clase=clase, cota=None)
        return valor

    def _entra(self, camino, acciones, alfa, beta, es_max):
        '''Registra que se empieza a expandir un nodo.'''
        self.metricas.nodos_expandidos += 1
        if len(camino) < self.prof_traza:
            self._registrar('entra', camino, acciones=list(acciones),
                            alfa=alfa, beta=beta, es_max=es_max)

    def _sale(self, camino, valor, accion, cota=None):
        '''Registra que se terminó de explorar un nodo. Los nodos del
        último nivel visible se guardan resumidos como una hoja.'''
        if len(camino) < self.prof_traza:
            self._registrar('sale', camino, valor=valor, mejor=accion,
                            cota=cota)
        else:
            self._registrar('hoja', camino, valor=valor, clase='resumen',
                            cota=cota)


class AgenteAleatorio(AgenteBusqueda):
    '''Agente que juega en una columna al azar. Sirve como línea base
    para los experimentos.'''
    nombre = 'Aleatorio'

    def _buscar(self, estado):
        acciones = self.game.acciones(estado)
        return 0, self.rng.choice(acciones)


# ======================================================================
# Algoritmo 1: minimax con profundidad limitada (no informado)
# ======================================================================
class AgenteMinimax(AgenteBusqueda):
    '''
    Minimax con profundidad limitada.

    Recorre en profundidad el árbol de juego. Solo usa la utilidad de los
    estados terminales: si llega a la profundidad límite sin que el juego
    termine devuelve 0, es decir, no usa conocimiento del juego.
    '''
    nombre = 'Minimax'

    def __init__(self, game, max_lim: int = 4, semilla: int = None,
                 prof_traza: int = 3):
        super().__init__(game, max_lim=max_lim, heuristica='nula',
                         semilla=semilla, prof_traza=prof_traza)

    def descripcion(self):
        return f'Minimax (d={self.max_lim})'

    def _buscar(self, estado):
        return self._minimax_search(estado)

    def _minimax_search(self, estado):
        # En la raíz siempre juega MAX (el agente que decide)
        valor, accion = self._max_value(estado, 0, ())
        return valor, accion

    def _max_value(self, estado, d, camino):
        self._visitar(d)
        if self._is_cutoff(estado, d):
            return self._hoja(estado, camino), None
        acciones = self.game.acciones(estado)
        self._entra(camino, acciones, -np.inf, np.inf, True)
        v = -np.inf
        mejores = []
        for a in acciones:
            hijo = self.game.resultado(estado, a)
            self.metricas.nodos_generados += 1
            v2, a2 = self._min_value(hijo, d + 1, camino + (a,))
            if d == 0:
                self.metricas.valores_acciones[a] = v2
            if v2 > v:
                v = v2
                mejores = [a]
            elif v2 == v:
                mejores.append(a)
        # En la raíz, si varias jugadas tienen el mismo valor se elige una
        # al azar; así el agente no juega siempre en la misma columna.
        accion = self.rng.choice(mejores) if d == 0 else mejores[0]
        self._sale(camino, v, accion)
        return v, accion

    def _min_value(self, estado, d, camino):
        self._visitar(d)
        if self._is_cutoff(estado, d):
            return self._hoja(estado, camino), None
        acciones = self.game.acciones(estado)
        self._entra(camino, acciones, -np.inf, np.inf, False)
        v = np.inf
        accion = None
        for a in acciones:
            hijo = self.game.resultado(estado, a)
            self.metricas.nodos_generados += 1
            v2, a2 = self._max_value(hijo, d + 1, camino + (a,))
            if v2 < v:
                v = v2
                accion = a
        self._sale(camino, v, accion)
        return v, accion


# ======================================================================
# Algoritmo 2: alfa-beta con cutoff y función de evaluación (informado)
# ======================================================================
class AgenteAlfaBeta(AgenteBusqueda):
    '''
    Alfa-beta con cutoff y funciones de evaluación (H-Minimax).

    Es minimax con dos mejoras:
        - poda alfa-beta: deja de explorar las ramas que ya no pueden
          cambiar la decisión (poda "a lo ancho"),
        - cutoff con heurística: en la profundidad límite estima el valor
          del tablero con h1 o h2 (poda "a lo alto").
    '''
    nombre = 'Alfa-beta'

    def __init__(self, game, max_lim: int = 5, heuristica: str = 'h1',
                 pesos: list = None, semilla: int = None,
                 prof_traza: int = 3):
        super().__init__(game, max_lim=max_lim, heuristica=heuristica,
                         semilla=semilla, prof_traza=prof_traza)
        # Pesos define la relevancia de las características de h1.
        # En orden, las características son:
        #       - Ventanas con 3 fichas propias y 1 vacía
        #       - Ventanas con 2 fichas propias y 2 vacías
        #       - Ventanas con 3 fichas del rival y 1 vacía
        #       - Ventanas con 2 fichas del rival y 2 vacías
        self.pesos = list(PESOS_H1) if pesos is None else list(pesos)
        self._hubo_poda = False

    def descripcion(self):
        return f'Alfa-beta {self.heuristica} (d={self.max_lim})'

    def _evaluar(self, estado):
        if self.game.es_terminal(estado):
            return self.game.utilidad(estado, self.jugador)
        if self.heuristica == 'h1':
            return h1_ventanas(estado, self.jugador, self.pesos)
        return HEURISTICAS[self.heuristica](estado, self.jugador)

    def _buscar(self, estado):
        return self._H_minimax_alfa_beta(estado, 0, -np.inf, np.inf, ())

    def _ordenar(self, acciones):
        '''Ordena las columnas del centro hacia los bordes.'''
        return [a for a in ORDEN_CENTRO if a in acciones]

    def _H_minimax_alfa_beta(self, estado, d, alfa, beta, camino):
        self._visitar(d)
        if self._is_cutoff(estado, d):
            self._hubo_poda = False
            return self._hoja(estado, camino), None
        jugador = self.game.player(estado)
        acciones = self._ordenar(self.game.acciones(estado))
        accion = None
        if jugador == self.jugador:
            # Nodo MAX: busca el valor más alto
            self._entra(camino, acciones, alfa, beta, True)
            v = -np.inf
            for i, a in enumerate(acciones):
                hijo = self.game.resultado(estado, a)
                self.metricas.nodos_generados += 1
                v2, a2 = self._H_minimax_alfa_beta(hijo, d + 1, alfa, beta,
                                                   camino + (a,))
                if d == 0:
                    self.metricas.valores_acciones[a] = v2
                    if self._hubo_poda:
                        self.cotas_acciones[a] = '<='
                if v2 > v:
                    v = v2
                    accion = a
                    alfa = max(alfa, v)
                if v >= beta:
                    # Poda beta: MIN nunca dejará llegar a este nodo
                    self._podar(camino, acciones[i + 1:], alfa, beta)
                    self._sale(camino, v, accion, cota='>=')
                    self._hubo_poda = True
                    return v, accion
            self._sale(camino, v, accion)
            self._hubo_poda = False
            return v, accion
        else:
            # Nodo MIN: busca el valor más bajo
            self._entra(camino, acciones, alfa, beta, False)
            v = np.inf
            for i, a in enumerate(acciones):
                hijo = self.game.resultado(estado, a)
                self.metricas.nodos_generados += 1
                v2, a2 = self._H_minimax_alfa_beta(hijo, d + 1, alfa, beta,
                                                   camino + (a,))
                if v2 < v:
                    v = v2
                    accion = a
                    beta = min(beta, v)
                if v <= alfa:
                    # Poda alfa: MAX ya tiene una opción mejor en otra rama
                    self._podar(camino, acciones[i + 1:], alfa, beta)
                    self._sale(camino, v, accion, cota='<=')
                    self._hubo_poda = True
                    return v, accion
            self._sale(camino, v, accion)
            self._hubo_poda = False
            return v, accion

    def _podar(self, camino, acciones_podadas, alfa, beta):
        '''Cuenta el corte y registra las jugadas que no se exploraron.'''
        self.metricas.podas += 1
        if len(camino) < self.prof_traza:
            self._registrar('poda', camino, podadas=list(acciones_podadas),
                            alfa=alfa, beta=beta)


# ======================================================================
# Algoritmo 3: Monte Carlo Tree Search con UCB1 (basado en simulación)
# ======================================================================
class AgenteMCTS(AgenteBusqueda):
    '''
    Búsqueda en árboles Monte Carlo (MCTS) con selección UCB1 (UCT).

    No usa función de evaluación: estima qué tan buena es una jugada
    simulando muchas partidas aleatorias hasta el final. Repite cuatro
    pasos: selección, expansión, simulación y retropropagación (backup).
    '''
    nombre = 'MCTS'

    def __init__(self, game, time_lim: int = 1000,
                 ucb_constant: float = np.sqrt(2), semilla: int = None,
                 prof_traza: int = 2):
        super().__init__(game, max_lim=0, heuristica='nula',
                         semilla=semilla, prof_traza=prof_traza)
        # Límite de la búsqueda: número de iteraciones (simulaciones)
        self.time_lim = time_lim
        # Constante de exploración de UCB1
        self.ucb_constant = ucb_constant
        self.visitas_acciones = {}
        self._largo_playout = 0

    def descripcion(self):
        return f'MCTS (N={self.time_lim})'

    def _buscar(self, estado):
        arbol = ArbolBusquedaJuego(estado,
                                   juego=self.game,
                                   rollout_policy=self.play_policy,
                                   ucb_constant=self.ucb_constant,
                                   rng=self.rng)
        time_out = 0
        while time_out < self.time_lim:
            if self.cancelar:
                raise BusquedaCancelada()
            # Selección
            nodo = arbol.seleccionar_ucb()
            # Expansión
            nodo_expandido = arbol.expandir(nodo)
            if nodo_expandido is not nodo:
                self.metricas.nodos_generados += 1
                self.metricas.nodos_expandidos += 1
            # Simulación
            resultado = self.simulate_game(nodo_expandido.estado)
            # Backup
            arbol.backup_value(nodo_expandido, resultado)
            time_out += 1
            # Métricas y traza de la iteración
            self.metricas.simulaciones = time_out
            self.metricas.memoria_max = arbol.num_nodos
            self.metricas.profundidad_max = arbol.prof_max
            if self.guardar_traza:
                self.traza.registrar('iteracion', nodo_expandido.camino(),
                                     self.metricas,
                                     seleccion=nodo.camino(),
                                     resultado=resultado[self.jugador],
                                     largo=self._largo_playout,
                                     nodos_arbol=arbol.num_nodos)
        accion = arbol.get_argmax_acciones()
        dict_acciones = arbol.dict_acciones
        self.visitas_acciones = {a: v.len_playout
                                 for a, v in dict_acciones.items()}
        self.metricas.valores_acciones = {
            a: (v.recompensa / v.len_playout if v.len_playout else 0)
            for a, v in dict_acciones.items()}
        valor = self.metricas.valores_acciones[accion]
        return valor, accion

    def play_policy(self, state):
        '''Política de simulación (rollout): jugada al azar.'''
        if self.game.es_terminal(state):
            return None
        return self.rng.choice(self.game.acciones(state))

    def simulate_game(self, state):
        '''Simula una partida aleatoria desde el estado dado hasta el final.

        Output: diccionario {1: r1, 2: r2} con la recompensa de cada
                jugador: 1 si gana, 0.5 si empata y 0 si pierde.
        '''
        s = state
        largo = 0
        while not self.game.es_terminal(s):
            accion = self.play_policy(s)
            s = self.game.resultado(s, accion)
            self.metricas.nodos_generados += 1
            largo += 1
        self._largo_playout = largo
        u = self.game.utilidad(s, 1)
        if u > 0:
            return {1: 1, 2: 0}
        elif u < 0:
            return {1: 0, 2: 1}
        else:
            return {1: 0.5, 2: 0.5}
