"""
Solucionador exacto para posiciones con pocas casillas vacías.

Sirve como REFERENCIA para la métrica "¿la jugada es óptima?": calcula
el valor minimax verdadero de cada jugada explorando el árbol hasta los
estados terminales (sin límite de profundidad ni heurística).

Es el mismo alfa-beta del proyecto con dos cambios:
    * formulación negamax: como el juego es de suma cero, el valor de un
      estado para el jugador en turno es el máximo del NEGATIVO del valor
      de sus sucesores (así no hace falta separar MAX y MIN),
    * tabla de transposición: un diccionario que recuerda los estados ya
      resueltos, porque a un mismo tablero se llega por varios caminos.

Solo es práctico cuando quedan pocas casillas vacías (finales de
partida); con el tablero vacío el árbol es demasiado grande.
"""
import numpy as np

from conecta4.agentes import ORDEN_CENTRO

# Tipos de entrada en la tabla de transposición
EXACTO = 0          # El valor guardado es el valor minimax verdadero
COTA_INFERIOR = 1   # El valor verdadero es mayor o igual al guardado
COTA_SUPERIOR = 2   # El valor verdadero es menor o igual al guardado

# Con más casillas vacías que estas no se intenta resolver
MAX_VACIAS = 18
# Si la búsqueda exacta supera esta cantidad de nodos, se abandona
LIMITE_NODOS = 400000


class LimiteSuperado(Exception):
    """La posición es demasiado costosa de resolver exactamente."""


class SolverExacto:
    """Calcula valores minimax exactos con alfa-beta y memoria."""

    def __init__(self, juego, max_vacias: int = MAX_VACIAS,
                 limite_nodos: int = LIMITE_NODOS):
        self.juego = juego
        self.max_vacias = max_vacias
        self.limite_nodos = limite_nodos
        self.tabla = {}
        self.nodos = 0

    def se_puede_resolver(self, estado) -> bool:
        """True si la posición tiene pocas casillas vacías."""
        vacias = np.count_nonzero(estado == 0)
        return vacias <= self.max_vacias

    def valor(self, estado, alfa=-np.inf, beta=np.inf):
        """Valor minimax exacto del estado para el jugador en turno."""
        self.nodos += 1
        if self.nodos > self.limite_nodos:
            raise LimiteSuperado()
        jugador = self.juego.player(estado)
        if self.juego.es_terminal(estado):
            return self.juego.utilidad(estado, jugador)
        alfa_inicial = alfa
        llave = estado.tobytes()
        if llave in self.tabla:
            tipo, guardado = self.tabla[llave]
            if tipo == EXACTO:
                return guardado
            if tipo == COTA_INFERIOR:
                alfa = max(alfa, guardado)
            else:
                beta = min(beta, guardado)
            if alfa >= beta:
                return guardado
        v = -np.inf
        acciones = self.juego.acciones(estado)
        for a in [c for c in ORDEN_CENTRO if c in acciones]:
            hijo = self.juego.resultado(estado, a)
            v = max(v, -self.valor(hijo, -beta, -alfa))
            alfa = max(alfa, v)
            if alfa >= beta:
                break
        if v <= alfa_inicial:
            self.tabla[llave] = (COTA_SUPERIOR, v)
        elif v >= beta:
            self.tabla[llave] = (COTA_INFERIOR, v)
        else:
            self.tabla[llave] = (EXACTO, v)
        return v

    def valores_acciones(self, estado) -> dict:
        """Valor exacto de cada jugada para el jugador en turno.

        Output: diccionario {columna: valor}. Un valor positivo significa
                que con esa jugada el jugador gana con juego perfecto,
                0 que empata y negativo que pierde.
        """
        self.nodos = 0
        valores = {}
        for a in self.juego.acciones(estado):
            hijo = self.juego.resultado(estado, a)
            valores[a] = -self.valor(hijo)
        return valores

    def jugadas_optimas(self, estado) -> list:
        """Lista de las jugadas con el mejor valor exacto."""
        valores = self.valores_acciones(estado)
        mejor = max(valores.values())
        return [a for a, v in valores.items() if v == mejor]

    def es_optima(self, estado, accion):
        """True/False si la jugada es óptima; None si la posición es
        demasiado grande para resolverla exactamente."""
        if not self.se_puede_resolver(estado):
            return None
        try:
            return accion in self.jugadas_optimas(estado)
        except LimiteSuperado:
            return None
