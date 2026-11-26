"""
Editor y generador de instancias.

El usuario define el estado inicial del entorno de tres maneras:
    * jugando fichas a mano (clic en una columna),
    * generando una posición aleatoria con una cantidad de fichas y una
      semilla (reproducible),
    * cargando una de las instancias de ejemplo.

La instancia se guarda como la SECUENCIA de jugadas que la produce. Como
cada jugada es legal, la posición siempre es alcanzable en una partida
real (respeta la gravedad y los turnos).
"""
import random

import pygame

from gui import tema
from gui.vista_tablero import VistaTablero
from gui.widgets import Boton, Deslizador

# Instancias de ejemplo: (nombre, secuencia de jugadas, descripción)
EJEMPLOS = [
    ('Tablero vacío', [],
     'Inicio estándar de la partida.'),
    ('Gana en 1', [3, 0, 3, 0, 3, 1],
     'El jugador 1 gana si juega en la columna 3.'),
    ('Bloqueo obligado', [3, 0, 3, 0, 6, 0],
     'El jugador 1 debe tapar la columna 0 o pierde.'),
    ('Doble amenaza', [3, 3, 2, 2],
     'El jugador 1 gana en 2 jugadas con la columna 1 o la 4.'),
    ('Medio juego', [3, 3, 3, 2, 3, 3, 2, 2, 2, 5, 2, 5],
     'Posición de 12 fichas tomada de una partida entre agentes, sin '
     'amenazas inmediatas.'),
    ('Final de partida',
     [2, 4, 3, 1, 2, 4, 3, 4, 4, 3, 3, 2, 2, 3, 3, 5, 2, 6, 4, 6, 2, 6,
      6, 4, 6],
     '25 fichas, juega el jugador 2: solo la columna 6 gana con juego '
     'perfecto. Permite verificar la optimalidad.'),
]


class PantallaEditor:
    """Pantalla para definir el estado inicial del entorno."""

    def __init__(self, app):
        self.app = app
        self.juego = app.juego
        self.vista = VistaTablero(294, 150, 60)
        self.jugadas = list(app.instancia)
        self.num_fichas = 10
        self.semilla = 1
        self.mensaje = ''
        self._columna_raton = None
        self._crear_controles()

    def _crear_controles(self):
        x, ancho = 24, 228
        self.boton_deshacer = Boton((x, 206, ancho, 32),
                                    'Deshacer última jugada', self.deshacer)
        self.boton_vaciar = Boton((x, 246, ancho, 32), 'Vaciar tablero',
                                  self.vaciar)
        self.deslizador = Deslizador((x + 4, 350, ancho - 8, 12), 0, 36,
                                     self.num_fichas, self._fijar_fichas)
        self.boton_menos = Boton((x + 120, 376, 30, 28), '−',
                                 lambda: self._cambiar_semilla(-1), tam=16)
        self.boton_mas = Boton((x + 198, 376, 30, 28), '+',
                               lambda: self._cambiar_semilla(1), tam=16)
        self.boton_generar = Boton((x, 416, ancho, 34),
                                   'Generar posición aleatoria',
                                   self.generar, primario=True)
        self.botones_ejemplo = []
        for i, (nombre, jugadas, _) in enumerate(EJEMPLOS):
            boton = Boton((756, 92 + i * 56, 170, 30), nombre,
                          lambda j=jugadas: self.cargar(j))
            self.botones_ejemplo.append(boton)
        self.boton_jugar = Boton((756, 620, 244, 38),
                                 'Jugar desde esta posición',
                                 self.usar_en_jugar, primario=True)
        self.boton_comparar = Boton((1012, 620, 244, 38),
                                    'Comparar algoritmos aquí',
                                    self.usar_en_comparar)

    def _controles(self):
        return ([self.boton_deshacer, self.boton_vaciar, self.deslizador,
                 self.boton_menos, self.boton_mas, self.boton_generar,
                 self.boton_jugar, self.boton_comparar]
                + self.botones_ejemplo)

    # ------------------------------------------------------------------
    # Acciones del editor
    # ------------------------------------------------------------------
    def estado(self):
        return self.juego.desde_jugadas(self.jugadas)

    def deshacer(self):
        if self.jugadas:
            self.jugadas.pop()
            self.mensaje = ''

    def vaciar(self):
        self.jugadas = []
        self.mensaje = ''

    def cargar(self, jugadas):
        self.jugadas = list(jugadas)
        self.mensaje = ''

    def _fijar_fichas(self, valor):
        self.num_fichas = valor

    def _cambiar_semilla(self, cambio):
        self.semilla = max(0, self.semilla + cambio)

    def generar(self):
        """Genera una posición aleatoria reproducible (misma cantidad de
        fichas y misma semilla -> misma posición)."""
        rng = random.Random(self.semilla)
        self.jugadas = self.juego.jugadas_aleatorias(self.num_fichas, rng)
        self.mensaje = (f'Posición aleatoria de {self.num_fichas} fichas '
                        f'(semilla {self.semilla}).')

    def jugar_columna(self, columna):
        estado = self.estado()
        if self.juego.es_terminal(estado):
            self.mensaje = 'La posición ya es terminal: deshaz una jugada.'
            return
        if columna not in self.juego.acciones(estado):
            self.mensaje = f'La columna {columna} está llena.'
            return
        self.jugadas.append(columna)
        self.mensaje = ''

    def _instancia_valida(self):
        if self.juego.es_terminal(self.estado()):
            self.mensaje = ('La instancia no puede ser un estado terminal: '
                            'deshaz la última jugada.')
            return False
        return True

    def usar_en_jugar(self):
        if self._instancia_valida():
            self.app.instancia = list(self.jugadas)
            self.app.pantallas['jugar'].nueva_partida()
            self.app.ir_a('jugar')

    def usar_en_comparar(self):
        if self._instancia_valida():
            self.app.instancia = list(self.jugadas)
            self.app.ir_a('comparar')

    def al_entrar(self):
        """Se llama cuando el usuario abre esta pestaña."""
        self.jugadas = list(self.app.instancia)

    # ------------------------------------------------------------------
    # Eventos, actualización y dibujo
    # ------------------------------------------------------------------
    def manejar_evento(self, evento):
        for control in self._controles():
            if control.manejar_evento(evento):
                return
        if evento.type == pygame.MOUSEMOTION:
            self._columna_raton = self.vista.columna_en(evento.pos)
        elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            columna = self.vista.columna_en(evento.pos)
            if columna is not None:
                self.jugar_columna(columna)
        elif evento.type == pygame.KEYDOWN and evento.key == pygame.K_z:
            self.deshacer()

    def actualizar(self, dt):
        pass

    def dibujar(self, sup):
        estado = self.estado()
        terminal = self.juego.es_terminal(estado)
        # Panel izquierdo: herramientas
        rect = pygame.Rect(12, 56, 252, 652)
        tema.panel(sup, rect, 'EDITOR DE INSTANCIAS')
        tema.texto_ajustado(
            sup, 'Haz clic en una columna del tablero para soltar una '
            'ficha. Las fichas se alternan entre los dos jugadores, así la '
            'posición siempre es legal.', pygame.Rect(24, 86, 228, 110),
            12, tema.TEXTO)
        self.boton_deshacer.dibujar(sup)
        self.boton_vaciar.dibujar(sup)
        tema.texto(sup, 'GENERADOR ALEATORIO', (24, 302), 12,
                   tema.TEXTO_SUAVE, True)
        tema.texto(sup, f'Fichas en el tablero: {self.num_fichas}',
                   (24, 326), 12, tema.TEXTO)
        self.deslizador.dibujar(sup)
        tema.texto(sup, 'Semilla:', (24, 390), 12, tema.TEXTO,
                   ancla='midleft')
        self.boton_menos.dibujar(sup)
        tema.texto(sup, str(self.semilla), (198, 390), 13, tema.TEXTO, True,
                   'center')
        self.boton_mas.dibujar(sup)
        self.boton_generar.dibujar(sup)
        tema.texto_ajustado(
            sup, 'La dificultad de cada agente (fácil, medio o difícil) se '
            'elige en las pestañas Jugar y Comparar.',
            pygame.Rect(24, 470, 228, 80), 11, tema.TEXTO_SUAVE)
        # Centro: tablero
        centro = pygame.Rect(276, 56, 456, 652)
        tema.panel(sup, centro)
        jugador = self.juego.player(estado)
        if terminal:
            titulo = self.juego.give_result(estado)
        else:
            titulo = (f'Turno del jugador {jugador} '
                      f'({tema.NOMBRE_COLOR[jugador]})')
        tema.texto(sup, titulo, (centro.centerx, 76), 14, tema.TEXTO, True,
                   'center')
        tema.texto(sup, self.mensaje, (centro.centerx, 98), 12, tema.NARANJA,
                   ancla='center')
        columna = None if terminal else self._columna_raton
        self.vista.dibujar(sup, estado,
                           linea=self.juego.linea_ganadora(estado),
                           columna_resaltada=columna, jugador_turno=jugador)
        self._dibujar_descripcion(sup, estado, terminal)
        # Panel derecho: ejemplos y resumen
        derecha = pygame.Rect(744, 56, 524, 652)
        tema.panel(sup, derecha, 'INSTANCIAS DE EJEMPLO')
        for boton, (_, _, descripcion) in zip(self.botones_ejemplo, EJEMPLOS):
            boton.dibujar(sup)
            tema.texto_ajustado(sup, descripcion,
                                pygame.Rect(938, boton.rect.y, 318, 40), 11,
                                tema.TEXTO_SUAVE)
        tema.texto_ajustado(
            sup, 'Cuando la instancia esté lista, úsala como estado inicial '
            'de una partida o del modo de comparación.',
            pygame.Rect(756, 566, 500, 40), 12, tema.TEXTO)
        self.boton_jugar.dibujar(sup)
        self.boton_comparar.dibujar(sup)

    def _dibujar_descripcion(self, sup, estado, terminal):
        """Datos del estado: fichas, turno, secuencia y validez."""
        x, y = 294, 540
        fichas = len(self.jugadas)
        legal, motivo = self.juego.es_legal(estado)
        tema.texto(sup, f'Fichas: {fichas}   ·   Casillas vacías: '
                   f'{42 - fichas}', (x, y), 12, tema.TEXTO)
        secuencia = ' '.join(str(c) for c in self.jugadas) or '(vacía)'
        tema.texto(sup, 'Secuencia de jugadas:', (x, y + 24), 12,
                   tema.TEXTO_SUAVE)
        tema.texto_ajustado(sup, secuencia,
                            pygame.Rect(x, y + 44, 420, 60), 12, tema.TEXTO)
        if not legal:
            estado_txt, color = f'Posición inválida: {motivo}', tema.ROJO
        elif terminal:
            estado_txt, color = 'Estado terminal (no sirve como inicio)', \
                tema.NARANJA
        else:
            estado_txt, color = 'Posición legal y no terminal', tema.VERDE
        tema.texto(sup, estado_txt, (x, y + 110), 12, color, True)
