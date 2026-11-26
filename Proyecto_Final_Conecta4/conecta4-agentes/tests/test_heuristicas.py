"""Pruebas de las funciones de evaluación h1 y h2."""
import random

import numpy as np

from conecta4.heuristicas import (TABLA_POSICIONAL, caracteristicas_h1,
                                  h1_ventanas, h2_posicional)
from conecta4.juego import Conecta4

juego = Conecta4()


def test_tabla_posicional_clasica():
    assert TABLA_POSICIONAL[0, 0] == 3       # Esquina
    assert TABLA_POSICIONAL[5, 6] == 3
    assert TABLA_POSICIONAL[2, 3] == 13      # Centro
    assert TABLA_POSICIONAL[3, 3] == 13
    assert TABLA_POSICIONAL.sum() == 69 * 4  # 276


def test_h2_prefiere_el_centro():
    centro = juego.desde_jugadas([3])
    borde = juego.desde_jugadas([0])
    assert h2_posicional(centro, 1) > h2_posicional(borde, 1)


def test_h2_es_antisimetrica():
    s = juego.desde_jugadas([3, 2, 3, 4, 1])
    assert np.isclose(h2_posicional(s, 1), -h2_posicional(s, 2))


def test_h1_cuenta_amenazas():
    # El jugador 1 tiene tres fichas seguidas en la fila inferior
    s = juego.desde_jugadas([2, 2, 3, 3, 4, 6])
    n3_propias, n2_propias, n3_rival, n2_rival = caracteristicas_h1(s, 1)
    assert n3_propias == 2      # Ventanas (1,2,3,4) y (2,3,4,5)
    assert h1_ventanas(s, 1) > 0
    assert h1_ventanas(s, 2) < 0


def test_heuristicas_estan_entre_menos_uno_y_uno():
    rng = random.Random(1)
    for _ in range(100):
        num_fichas = rng.randint(1, 30)
        s = juego.desde_jugadas(juego.jugadas_aleatorias(num_fichas, rng))
        for jugador in (1, 2):
            assert -1 < h1_ventanas(s, jugador) < 1
            assert -1 < h2_posicional(s, jugador) < 1
