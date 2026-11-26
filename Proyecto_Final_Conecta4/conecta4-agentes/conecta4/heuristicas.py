"""
Funciones de evaluación (heurísticas) para el 4 en raya.

Se usan en el algoritmo alfa-beta con cutoff (H-Minimax): cuando la
búsqueda llega a la profundidad límite sin que el juego haya terminado,
la heurística ESTIMA qué tan bueno es el tablero para el jugador MAX.

Las dos heurísticas devuelven un valor en el intervalo (-1, 1). Así
nunca superan la utilidad de una victoria real (que vale por lo menos
+1) ni la de una derrota real (que vale a lo sumo -1): el agente nunca
prefiere una posición que "se ve bien" antes que ganar de verdad.

    h1 (ventanas de amenaza): mira las 69 ventanas de cuatro casillas y
        cuenta amenazas propias y del rival. Es una heurística táctica.
    h2 (control posicional): suma el valor de las casillas ocupadas,
        donde una casilla vale más cuantas más líneas ganadoras pasan
        por ella. Es una heurística estática.

Igual que en el agente ``ChessFinalist1`` del taller de Juegos, h1 se
calcula como una suma ponderada ``np.dot(pesos, valores)`` de varias
características del tablero.
"""
import numpy as np

from conecta4.juego import VENTANAS, FILAS, COLUMNAS

# ----------------------------------------------------------------------
# h1: ventanas de amenaza
# ----------------------------------------------------------------------
# Pesos de las características de h1, en este orden:
#   - ventanas con 3 fichas propias y 1 vacía    (amenaza propia)
#   - ventanas con 2 fichas propias y 2 vacías
#   - ventanas con 3 fichas del rival y 1 vacía  (amenaza del rival)
#   - ventanas con 2 fichas del rival y 2 vacías
# Una ventana con fichas de ambos jugadores ya no sirve a nadie: vale 0.
PESOS_H1 = [6, 3, -5, -2]

# Cota del valor absoluto de h1: 69 ventanas por el peso más grande.
NORMA_H1 = len(VENTANAS) * max(abs(p) for p in PESOS_H1)


def caracteristicas_h1(estado, jugador):
    """Cuenta las ventanas de cada tipo desde el punto de vista del jugador.

    Input: estado, que es una np.array (6x7)
           jugador, 1 o 2 (el jugador para quien se evalúa)
    Output: lista [n3_propias, n2_propias, n3_rival, n2_rival]
    """
    rival = 2 if jugador == 1 else 1
    valores = estado.ravel()[VENTANAS]              # matriz 69 x 4
    propias = np.sum(valores == jugador, axis=1)    # fichas propias/ventana
    rivales = np.sum(valores == rival, axis=1)      # fichas rivales/ventana
    n3_propias = int(np.count_nonzero((propias == 3) & (rivales == 0)))
    n2_propias = int(np.count_nonzero((propias == 2) & (rivales == 0)))
    n3_rival = int(np.count_nonzero((rivales == 3) & (propias == 0)))
    n2_rival = int(np.count_nonzero((rivales == 2) & (propias == 0)))
    return [n3_propias, n2_propias, n3_rival, n2_rival]


def h1_ventanas(estado, jugador, pesos=PESOS_H1):
    """Heurística h1 (ventanas de amenaza), normalizada a (-1, 1).

    Input: estado, que es una np.array (6x7)
           jugador, 1 o 2 (jugador MAX)
           pesos (opcional), relevancia de cada característica
    Output: evaluación del tablero, positiva si favorece al jugador
    """
    valores = caracteristicas_h1(estado, jugador)
    evaluacion = np.dot(pesos, valores)
    return float(evaluacion) / NORMA_H1


# ----------------------------------------------------------------------
# h2: control posicional
# ----------------------------------------------------------------------
def generar_tabla_posicional():
    """Cuenta cuántas de las 69 ventanas pasan por cada casilla.

    El resultado es la tabla clásica del 4 en raya: las esquinas valen 3
    y las dos casillas centrales valen 13.

    Output: np.array (6x7) de enteros
    """
    conteo = np.bincount(VENTANAS.ravel(), minlength=FILAS * COLUMNAS)
    return conteo.reshape(FILAS, COLUMNAS)


TABLA_POSICIONAL = generar_tabla_posicional()

# Cota del valor absoluto de h2: la suma de toda la tabla (276).
NORMA_H2 = int(TABLA_POSICIONAL.sum())


def h2_posicional(estado, jugador):
    """Heurística h2 (control posicional), normalizada a (-1, 1).

    Suma el valor de las casillas con fichas propias y resta el valor de
    las casillas con fichas del rival.

    Input: estado, que es una np.array (6x7)
           jugador, 1 o 2 (jugador MAX)
    Output: evaluación del tablero, positiva si favorece al jugador
    """
    rival = 2 if jugador == 1 else 1
    propias = TABLA_POSICIONAL[estado == jugador].sum()
    rivales = TABLA_POSICIONAL[estado == rival].sum()
    return float(propias - rivales) / NORMA_H2


def h_nula(estado, jugador):
    """Evaluación sin conocimiento del juego: todo tablero vale 0.
    Es la que usa minimax con profundidad limitada (no informado)."""
    return 0.0


# Diccionario para elegir la heurística por nombre
HEURISTICAS = {
    'h1': h1_ventanas,
    'h2': h2_posicional,
    'nula': h_nula,
}

NOMBRES_HEURISTICAS = {
    'h1': 'h1 (ventanas de amenaza)',
    'h2': 'h2 (control posicional)',
    'nula': 'sin heurística',
}
