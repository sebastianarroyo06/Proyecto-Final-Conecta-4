"""
Estructuras de datos para la búsqueda en árboles Monte Carlo (MCTS).

Adaptadas del módulo ``datastruct.py`` del taller de Juegos del curso
(clases ``valorNodo``, ``NodoBusquedaJuego`` y ``ArbolBusquedaJuego``).
Se conservan los mismos nombres de clases y métodos del curso:

    seleccionar_ucb()  -> selección
    expandir()         -> expansión
    backup_value()     -> retropropagación
    get_argmax_acciones() -> jugada final

Diferencias con la versión del curso (pensada para el final de ajedrez
rey y torre contra rey):
    * La selección baja por el árbol eligiendo en cada nivel el hijo con
      mayor UCB1 (algoritmo UCT estándar), en lugar de mantener una lista
      de hojas.
    * Cada nodo guarda la recompensa desde el punto de vista del jugador
      que hizo la jugada para llegar a él, porque en el 4 en raya los dos
      jugadores buscan ganar (en el taller a las negras les servía
      empatar).
"""
import numpy as np


class valorNodo:
    """Valor estadístico de un nodo: recompensa acumulada y número de
    simulaciones (playouts) que han pasado por el nodo."""

    def __init__(self, recompensa: float, len_playout: int):
        self.recompensa = recompensa
        self.len_playout = len_playout

    def __str__(self) -> str:
        return f'{self.recompensa}/{self.len_playout}'


class NodoBusquedaJuego:
    """Nodo del árbol de búsqueda Monte Carlo."""

    def __init__(self, estado, madre, accion, valor: valorNodo,
                 ucb_constant: float, jugador: int, acciones: list):
        self.estado = estado
        self.madre = madre
        self.accion = accion            # Jugada con la que se llegó aquí
        self.valor = valor
        self.ucb_constant = ucb_constant
        self.jugador = jugador          # Jugador que hizo esa jugada
        self.acciones_sin_probar = list(acciones)
        self.hijos = []

    def retro_propagar(self, resultado: dict):
        """Sube el resultado de una simulación hasta la raíz.

        Input: resultado, diccionario {1: r1, 2: r2} con la recompensa de
               cada jugador (1 gana, 0.5 empata, 0 pierde).
        """
        self.valor.recompensa += resultado[self.jugador]
        self.valor.len_playout += 1
        if self.madre is not None:
            self.madre.retro_propagar(resultado)

    def ucb(self, total: int) -> float:
        """Valor UCB1 del nodo.

            UCB1 = recompensa media + c * sqrt( ln(total) / visitas )

        El primer término favorece la explotación (jugadas que han dado
        buenos resultados) y el segundo la exploración (jugadas poco
        visitadas). ``total`` son las visitas del nodo madre.
        """
        if self.valor.len_playout == 0:
            return np.inf
        exploracion = np.sqrt(np.log(total) / self.valor.len_playout)
        return self.get_value() + self.ucb_constant * exploracion

    def get_value(self) -> float:
        """Recompensa media del nodo (entre 0 y 1)."""
        if self.valor.len_playout == 0:
            return 0
        return self.valor.recompensa / self.valor.len_playout

    def profundidad(self) -> int:
        if self.madre is None:
            return 0
        return 1 + self.madre.profundidad()

    def camino(self) -> tuple:
        """Tupla de jugadas desde la raíz hasta este nodo."""
        if self.madre is None:
            return ()
        return self.madre.camino() + (self.accion,)

    def esta_expandido(self) -> bool:
        """True si ya se crearon todos los hijos posibles del nodo."""
        return len(self.acciones_sin_probar) == 0

    def __str__(self):
        raiz = '--raiz--' if self.madre is None else ''
        cadena = 'Nodo ' + raiz + f'camino={self.camino()}\n'
        cadena += f'Profundidad: {self.profundidad()}\n'
        cadena += f'Valor (recompensa/simulaciones): {self.valor}\n'
        return cadena


class ArbolBusquedaJuego:
    """Árbol de búsqueda Monte Carlo con selección UCB1 (UCT)."""

    def __init__(self, state, juego, rollout_policy, ucb_constant: float,
                 rng):
        self.juego = juego
        self.rollout_policy = rollout_policy
        self.ucb_constant = ucb_constant
        self.rng = rng
        jugador_previo = juego.otro_jugador(juego.player(state))
        self.raiz = NodoBusquedaJuego(state, None, None, valorNodo(0, 0),
                                      ucb_constant, jugador_previo,
                                      juego.acciones(state))
        self.total = 0          # Simulaciones realizadas
        self.num_nodos = 1      # Nodos guardados en el árbol
        self.prof_max = 0       # Profundidad máxima del árbol

    @property
    def dict_acciones(self) -> dict:
        """Diccionario {accion: valorNodo} con las jugadas de la raíz."""
        return {hijo.accion: hijo.valor for hijo in self.raiz.hijos}

    def seleccionar_ucb(self) -> NodoBusquedaJuego:
        """Selección: baja desde la raíz eligiendo siempre el hijo con
        mayor UCB1, hasta llegar a un nodo al que le falten hijos por
        crear o a un estado terminal."""
        nodo = self.raiz
        while nodo.esta_expandido() and len(nodo.hijos) > 0:
            total = nodo.valor.len_playout
            nodo = max(nodo.hijos, key=lambda hijo: hijo.ucb(total))
        return nodo

    def expandir(self, nodo: NodoBusquedaJuego) -> NodoBusquedaJuego:
        """Expansión: crea UN hijo nuevo del nodo con una jugada todavía
        no probada, elegida al azar. Si el nodo es terminal no hay nada
        que expandir y se devuelve el mismo nodo."""
        if len(nodo.acciones_sin_probar) == 0:
            return nodo
        indice = self.rng.randrange(len(nodo.acciones_sin_probar))
        accion = nodo.acciones_sin_probar.pop(indice)
        jugador = self.juego.player(nodo.estado)
        estado = self.juego.resultado(nodo.estado, accion)
        hijo = NodoBusquedaJuego(estado=estado,
                                 madre=nodo,
                                 accion=accion,
                                 valor=valorNodo(0, 0),
                                 ucb_constant=self.ucb_constant,
                                 jugador=jugador,
                                 acciones=self.juego.acciones(estado))
        nodo.hijos.append(hijo)
        self.num_nodos += 1
        self.prof_max = max(self.prof_max, hijo.profundidad())
        return hijo

    def backup_value(self, nodo: NodoBusquedaJuego, resultado: dict):
        """Retropropagación: actualiza las estadísticas de todos los
        nodos del camino entre ``nodo`` y la raíz."""
        self.total += 1
        nodo.retro_propagar(resultado)

    def get_argmax_acciones(self):
        """Devuelve la jugada de la raíz con más simulaciones (la más
        robusta); si hay empate, la de mayor recompensa media."""
        assert len(self.raiz.hijos) > 0, 'Oops! No hay acciones para escoger'
        mejor = max(self.raiz.hijos,
                    key=lambda h: (h.valor.len_playout, h.get_value()))
        return mejor.accion
