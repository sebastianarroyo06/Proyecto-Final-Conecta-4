"""Pruebas del entorno Conecta4 (definición formal del juego)."""
import random

import numpy as np

from conecta4.juego import Conecta4, VENTANAS

juego = Conecta4()

# Tablero lleno sin cuatro en línea (empate)
EMPATE = np.array([[1, 1, 2, 2, 1, 1, 2],
                   [2, 2, 1, 1, 2, 2, 1],
                   [1, 1, 2, 2, 1, 1, 2],
                   [2, 2, 1, 1, 2, 2, 1],
                   [1, 1, 2, 2, 1, 1, 2],
                   [2, 2, 1, 1, 2, 2, 1]], dtype=np.int8)


def test_hay_69_ventanas():
    assert VENTANAS.shape == (69, 4)


def test_estado_inicial_vacio():
    s = juego.estado_inicial
    assert s.shape == (6, 7)
    assert np.count_nonzero(s) == 0
    assert juego.player(s) == 1
    assert juego.acciones(s) == [0, 1, 2, 3, 4, 5, 6]
    assert not juego.es_terminal(s)
    assert juego.utilidad(s, 1) is None


def test_resultado_la_ficha_cae_y_cambia_el_turno():
    s = juego.estado_inicial
    s1 = juego.resultado(s, 3)
    assert s1[5, 3] == 1            # Cae a la fila inferior
    assert np.count_nonzero(s) == 0  # No modifica el estado original
    assert juego.player(s1) == 2
    s2 = juego.resultado(s1, 3)
    assert s2[4, 3] == 2            # Queda encima de la anterior
    assert juego.player(s2) == 1


def test_columna_llena_no_es_accion():
    s = juego.desde_jugadas([0, 0, 0, 0, 0, 0])
    assert 0 not in juego.acciones(s)
    assert len(juego.acciones(s)) == 6


def test_gana_vertical():
    s = juego.desde_jugadas([3, 4, 3, 4, 3, 4, 3])
    assert juego.es_terminal(s)
    assert juego.ganador(s) == 1
    assert juego.acciones(s) == []
    # 7 fichas en el tablero: utilidad 43 - 7 = 36
    assert juego.utilidad(s, 1) == 36
    assert juego.utilidad(s, 2) == -36
    assert len(juego.linea_ganadora(s)) == 4


def test_gana_horizontal_el_jugador_2():
    s = juego.desde_jugadas([0, 1, 0, 2, 0, 3, 6, 4])
    assert juego.ganador(s) == 2
    assert juego.utilidad(s, 2) == 43 - 8
    assert juego.utilidad(s, 1) == -(43 - 8)


def test_gana_diagonal():
    # Diagonal del jugador 1 que sube hacia la derecha
    s = juego.desde_jugadas([0, 1, 1, 2, 2, 3, 2, 3, 3, 6, 3])
    assert juego.ganador(s) == 1
    # Diagonal del jugador 1 que sube hacia la izquierda
    s = juego.desde_jugadas([6, 5, 5, 4, 4, 3, 4, 3, 3, 0, 3])
    assert juego.ganador(s) == 1


def test_empate_con_tablero_lleno():
    assert juego.ganador(EMPATE) == 0
    assert juego.es_terminal(EMPATE)
    assert juego.utilidad(EMPATE, 1) == 0
    assert juego.utilidad(EMPATE, 2) == 0
    assert juego.es_legal(EMPATE)[0]


def test_utilidad_es_de_suma_cero():
    rng = random.Random(0)
    for _ in range(30):
        s = juego.estado_inicial
        while not juego.es_terminal(s):
            s = juego.resultado(s, rng.choice(juego.acciones(s)))
        assert juego.utilidad(s, 1) == -juego.utilidad(s, 2)


def test_es_legal_detecta_posiciones_invalidas():
    flotando = np.zeros((6, 7), dtype=np.int8)
    flotando[2, 3] = 1
    assert not juego.es_legal(flotando)[0]
    turnos = np.zeros((6, 7), dtype=np.int8)
    turnos[5, 0] = 2
    assert not juego.es_legal(turnos)[0]
    assert juego.es_legal(juego.desde_jugadas([3, 3, 2]))[0]


def test_jugadas_aleatorias_reproducibles():
    a = juego.jugadas_aleatorias(12, random.Random(5))
    b = juego.jugadas_aleatorias(12, random.Random(5))
    assert a == b
    s = juego.desde_jugadas(a)
    assert np.count_nonzero(s) == 12
    assert not juego.es_terminal(s)
    assert juego.es_legal(s)[0]
