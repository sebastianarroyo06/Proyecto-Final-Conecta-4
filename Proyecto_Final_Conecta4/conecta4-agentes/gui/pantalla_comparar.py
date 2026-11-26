"""
Modo de comparación: ejecuta los algoritmos sobre LA MISMA instancia y
presenta las métricas en tablas y gráficas.

    Comparar una jugada -> todos los algoritmos deciden sobre el mismo
                           tablero; se comparan tiempo, nodos generados,
                           nodos expandidos, memoria y si la jugada es
                           óptima (según el solucionador exacto).
    Torneo              -> todos contra todos desde la misma instancia;
                           se comparan victorias, empates y derrotas.

Los cálculos corren en un hilo aparte y los resultados se pueden
exportar a un archivo CSV.
"""
import csv
import os
import threading
import time

import pygame

from conecta4.experimentos import (comparar_jugada, nombre_config,
                                   tabla_posiciones, torneo)
from conecta4.solver import LimiteSuperado, SolverExacto
from gui import tema
from gui.vista_tablero import dibujar_tablero_mini
from gui.widgets import (Boton, Casilla, Segmentado, dibujar_barras,
                         dibujar_tabla)

NIVELES = [('facil', 'Fácil'), ('medio', 'Medio'), ('dificil', 'Difícil')]
COLORES_CONFIG = [(56, 189, 248), (52, 211, 153), (251, 146, 60),
                  (192, 132, 252), (148, 163, 184)]


class PantallaComparar:
    """Ventana de comparación de algoritmos."""

    def __init__(self, app):
        self.app = app
        self.juego = app.juego
        self.nivel = 'medio'
        self.rondas = 1
        self.tipo_resultado = None      # 'jugada' o 'torneo'
        self.filas = []                 # Resultados de comparar una jugada
        self.exactos = None             # Valores exactos de la instancia
        self.solver = SolverExacto(self.juego)
        self.partidas = []              # Resultados del torneo
        self.posiciones = []
        self.corriendo = False
        self.progreso = (0, 1)
        self.mensaje = ''
        self._cancelar = False
        self._crear_controles()

    def _crear_controles(self):
        x, ancho = 24, 228
        self.seg_nivel = Segmentado((x, 312, ancho, 28), NIVELES, self.nivel,
                                    self._fijar_nivel)
        self.casillas = [
            (Casilla((x, 376), 'Minimax', True), {'algoritmo': 'minimax'}),
            (Casilla((x, 402), 'Alfa-beta con h1', True),
             {'algoritmo': 'alfabeta', 'heuristica': 'h1'}),
            (Casilla((x, 428), 'Alfa-beta con h2', True),
             {'algoritmo': 'alfabeta', 'heuristica': 'h2'}),
            (Casilla((x, 454), 'MCTS', True), {'algoritmo': 'mcts'}),
        ]
        self.boton_jugada = Boton((x, 492, ancho, 34), 'Comparar una jugada',
                                  self.comparar_jugada, primario=True)
        self.seg_rondas = Segmentado((x + 108, 540, 120, 26),
                                     [(1, '1'), (2, '2'), (3, '3')],
                                     self.rondas, self._fijar_rondas)
        self.boton_torneo = Boton((x, 574, ancho, 34),
                                  'Torneo todos contra todos', self.torneo)
        self.boton_exportar = Boton((x, 620, 110, 30), 'Exportar CSV',
                                    self.exportar)
        self.boton_cancelar = Boton((x + 118, 620, 110, 30), 'Cancelar',
                                    self.cancelar)

    def _controles(self):
        return ([self.seg_nivel, self.boton_jugada, self.seg_rondas,
                 self.boton_torneo, self.boton_exportar, self.boton_cancelar]
                + [casilla for casilla, _ in self.casillas])

    def _fijar_nivel(self, valor):
        self.nivel = valor

    def _fijar_rondas(self, valor):
        self.rondas = valor

    def al_entrar(self):
        pass

    # ------------------------------------------------------------------
    # Ejecución de las comparaciones
    # ------------------------------------------------------------------
    def _configuraciones(self):
        """Configuraciones marcadas, con la dificultad elegida."""
        configs = []
        for casilla, base in self.casillas:
            if casilla.valor:
                config = dict(base)
                config['nivel'] = self.nivel
                configs.append(config)
        return configs

    def _estado(self):
        return self.juego.desde_jugadas(self.app.instancia)

    def _fijar_progreso(self, hechas, total):
        self.progreso = (hechas, total)

    def comparar_jugada(self):
        """Todos los algoritmos deciden sobre el mismo tablero."""
        configs = self._configuraciones()
        if self.corriendo or not configs:
            return
        estado = self._estado()
        self._iniciar(len(configs))

        def trabajo():
            try:
                self.filas = comparar_jugada(self.juego, estado, configs,
                                             semilla=self.app.semilla,
                                             solver=self.solver,
                                             progreso=self._fijar_progreso)
                self.exactos = None
                if self.solver.se_puede_resolver(estado):
                    try:
                        self.exactos = self.solver.valores_acciones(estado)
                    except LimiteSuperado:
                        self.exactos = None
                self.tipo_resultado = 'jugada'
                self.mensaje = 'Comparación terminada.'
            except Exception as error:      # Se muestra en pantalla
                self.mensaje = f'Error: {error}'
            self.corriendo = False

        threading.Thread(target=trabajo, daemon=True).start()

    def torneo(self):
        """Todos contra todos desde la instancia actual."""
        configs = self._configuraciones()
        if self.corriendo or len(configs) < 2:
            self.mensaje = 'Marca al menos dos algoritmos para el torneo.'
            return
        aperturas = [list(self.app.instancia)] * self.rondas
        self._iniciar(len(configs) * (len(configs) - 1) * self.rondas)

        def trabajo():
            try:
                self.partidas = torneo(self.juego, configs, aperturas,
                                       semilla=self.app.semilla,
                                       progreso=self._fijar_progreso,
                                       cancelar=lambda: self._cancelar)
                self.posiciones = tabla_posiciones(self.partidas)
                self.tipo_resultado = 'torneo'
                self.mensaje = ('Torneo cancelado.' if self._cancelar
                                else 'Torneo terminado.')
            except Exception as error:
                self.mensaje = f'Error: {error}'
            self.corriendo = False

        threading.Thread(target=trabajo, daemon=True).start()

    def _iniciar(self, total):
        self.corriendo = True
        self._cancelar = False
        self.progreso = (0, total)
        self.mensaje = 'Calculando…'

    def cancelar(self):
        if self.corriendo:
            self._cancelar = True
            self.mensaje = 'Cancelando al terminar la partida en curso…'

    def exportar(self):
        """Guarda los resultados visibles en un archivo CSV."""
        if self.tipo_resultado == 'jugada':
            datos, nombre = self.filas, 'comparacion_jugada'
        elif self.tipo_resultado == 'torneo':
            datos, nombre = self.partidas, 'torneo'
        else:
            self.mensaje = 'Todavía no hay resultados para exportar.'
            return
        carpeta = os.path.join(self.app.carpeta, 'resultados')
        os.makedirs(carpeta, exist_ok=True)
        ruta = os.path.join(carpeta,
                            f'{nombre}_{time.strftime("%Y%m%d_%H%M%S")}.csv')
        with open(ruta, 'w', newline='', encoding='utf-8') as archivo:
            escritor = csv.DictWriter(archivo, fieldnames=list(datos[0]))
            escritor.writeheader()
            escritor.writerows(datos)
        self.mensaje = f'Guardado en resultados/{os.path.basename(ruta)}'

    # ------------------------------------------------------------------
    # Eventos, actualización y dibujo
    # ------------------------------------------------------------------
    def manejar_evento(self, evento):
        for control in self._controles():
            if control.manejar_evento(evento):
                return

    def actualizar(self, dt):
        self.boton_jugada.habilitado = not self.corriendo
        self.boton_torneo.habilitado = not self.corriendo
        self.boton_cancelar.habilitado = self.corriendo
        self.boton_exportar.habilitado = (not self.corriendo
                                          and self.tipo_resultado is not None)

    def dibujar(self, sup):
        self._dibujar_panel(sup)
        rect = pygame.Rect(276, 56, 992, 652)
        if self.tipo_resultado == 'jugada':
            self._dibujar_jugada(sup, rect)
        elif self.tipo_resultado == 'torneo':
            self._dibujar_torneo(sup, rect)
        else:
            self._dibujar_ayuda(sup, rect)

    def _dibujar_panel(self, sup):
        rect = pygame.Rect(12, 56, 252, 652)
        tema.panel(sup, rect, 'COMPARACIÓN')
        estado = self._estado()
        tema.texto(sup, 'Instancia (misma para todos)', (24, 84), 12,
                   tema.TEXTO_SUAVE)
        dibujar_tablero_mini(sup, 47, 104, estado, celda=26)
        fichas = len(self.app.instancia)
        jugador = self.juego.player(estado)
        tema.texto(sup, f'{fichas} fichas · juega el jugador {jugador} '
                   f'({tema.NOMBRE_COLOR[jugador]})', (138, 274), 11,
                   tema.TEXTO_SUAVE, ancla='center')
        tema.texto(sup, 'Dificultad', (24, 294), 12, tema.TEXTO_SUAVE)
        self.seg_nivel.dibujar(sup)
        tema.texto(sup, 'Algoritmos', (24, 354), 12, tema.TEXTO_SUAVE)
        for casilla, _ in self.casillas:
            casilla.dibujar(sup)
        self.boton_jugada.dibujar(sup)
        tema.texto(sup, 'Rondas torneo:', (24, 553), 12, tema.TEXTO,
                   ancla='midleft')
        self.seg_rondas.dibujar(sup)
        self.boton_torneo.dibujar(sup)
        self.boton_exportar.dibujar(sup)
        self.boton_cancelar.dibujar(sup)
        # Barra de progreso y mensaje
        hechas, total = self.progreso
        barra = pygame.Rect(24, 662, 228, 8)
        pygame.draw.rect(sup, tema.PANEL_CLARO, barra, border_radius=4)
        if total > 0 and hechas > 0:
            lleno = pygame.Rect(24, 662, int(228 * hechas / total), 8)
            pygame.draw.rect(sup, tema.ACENTO, lleno, border_radius=4)
        tema.texto_ajustado(sup, self.mensaje,
                            pygame.Rect(24, 676, 228, 30), 11, tema.NARANJA)

    def _dibujar_ayuda(self, sup, rect):
        tema.panel(sup, rect, 'RESULTADOS')
        lineas = (
            'Este modo ejecuta los algoritmos sobre la misma instancia y '
            'compara sus métricas.\n\n'
            '1. La instancia es la posición definida en la pestaña Editor '
            '(por defecto, el tablero vacío).\n'
            '2. Elige la dificultad y marca los algoritmos que quieres '
            'comparar.\n'
            '3. "Comparar una jugada" hace que todos decidan sobre ese '
            'mismo tablero y muestra tiempo, nodos generados, nodos '
            'expandidos, memoria y si la jugada es óptima.\n'
            '4. "Torneo todos contra todos" enfrenta a cada pareja desde '
            'la instancia, una partida con cada uno empezando, y muestra '
            'victorias, empates y derrotas.\n'
            '5. "Exportar CSV" guarda la tabla en la carpeta resultados/.'
            '\n\nLa optimalidad se verifica con un solucionador exacto, '
            'que solo es posible en posiciones con pocas casillas vacías '
            '(por ejemplo la instancia "Final de partida"). En las demás '
            'aparece "n. d." (no disponible).')
        tema.texto_ajustado(sup, lineas, pygame.Rect(rect.x + 24,
                                                     rect.y + 44, 700, 500),
                            13, tema.TEXTO, interlinea=6)

    def _dibujar_jugada(self, sup, rect):
        tema.panel(sup, rect, 'RESULTADOS: UNA JUGADA SOBRE LA MISMA '
                   'INSTANCIA')
        columnas = [('Algoritmo', 190, 'izq'), ('Columna', 78, 'der'),
                    ('Valor', 86, 'der'), ('Tiempo', 100, 'der'),
                    ('Generados', 108, 'der'), ('Expandidos', 108, 'der'),
                    ('Memoria', 88, 'der'), ('Podas', 80, 'der'),
                    ('¿Óptima?', 110, 'der')]
        filas = []
        for i, f in enumerate(self.filas):
            optima = {True: ('sí', tema.VERDE), False: ('no', tema.ROJO),
                      None: ('n. d.', tema.TEXTO_SUAVE)}[f['optima']]
            filas.append([
                (f['configuracion'], COLORES_CONFIG[i % 5]),
                str(f['accion']), tema.formato_valor(round(f['valor'], 3)),
                tema.formato_tiempo(f['tiempo']),
                tema.formato_numero(f['nodos_generados']),
                tema.formato_numero(f['nodos_expandidos']),
                tema.formato_numero(f['memoria_max']),
                tema.formato_numero(f['podas']), optima])
        tabla = pygame.Rect(rect.x + 20, rect.y + 36, 948, 200)
        y = dibujar_tabla(sup, tabla, columnas, filas, alto_fila=28, tam=12)
        tema.texto(sup, 'Valor: utilidad o evaluación de la jugada elegida '
                   '(en MCTS, recompensa media entre 0 y 1). Memoria: '
                   'máximo de nodos guardados al mismo tiempo.',
                   (rect.x + 20, y + 8), 11, tema.TEXTO_SUAVE)
        tema.texto(sup, self._texto_exacto(), (rect.x + 20, y + 26), 11,
                   tema.TEXTO)
        y += 18
        etiquetas = [f['configuracion'] for f in self.filas]
        colores = [COLORES_CONFIG[i % 5] for i in range(len(self.filas))]
        ancho, alto = 464, 40 + 26 * len(self.filas)
        y0 = y + 34
        graficas = [
            ('TIEMPO DE EJECUCIÓN', 'tiempo', False, tema.formato_tiempo),
            ('NODOS GENERADOS', 'nodos_generados', True, None),
            ('NODOS EXPANDIDOS', 'nodos_expandidos', True, None),
            ('MEMORIA (NODOS EN MEMORIA)', 'memoria_max', True, None),
        ]
        for i, (titulo, llave, logaritmica, formato) in enumerate(graficas):
            fila, columna = divmod(i, 2)
            zona = pygame.Rect(rect.x + 20 + columna * (ancho + 20),
                               y0 + fila * (alto + 12), ancho, alto)
            dibujar_barras(sup, zona, titulo, etiquetas,
                           [f[llave] for f in self.filas], colores,
                           logaritmica, formato)

    def _texto_exacto(self):
        """Frase con el resultado del solucionador exacto."""
        if self.exactos is None:
            return ('Solucionador exacto: no disponible (la instancia tiene '
                    'demasiadas casillas vacías).')
        mejor = max(self.exactos.values())
        optimas = ', '.join(str(a) for a, v in sorted(self.exactos.items())
                            if v == mejor)
        if mejor > 0:
            resultado = 'el jugador en turno gana'
        elif mejor == 0:
            resultado = 'la partida es empate'
        else:
            resultado = 'el jugador en turno pierde'
        return (f'Solucionador exacto: con juego perfecto {resultado} '
                f'(valor {tema.formato_valor(mejor)}); columnas óptimas: '
                f'{optimas}.')

    def _dibujar_torneo(self, sup, rect):
        tema.panel(sup, rect, 'RESULTADOS: TORNEO TODOS CONTRA TODOS DESDE '
                   'LA MISMA INSTANCIA')
        columnas = [('Algoritmo', 190, 'izq'), ('Partidas', 84, 'der'),
                    ('Victorias', 90, 'der'), ('Empates', 84, 'der'),
                    ('Derrotas', 88, 'der'), ('Puntos', 76, 'der'),
                    ('t/jugada', 112, 'der'), ('Gen./jugada', 112, 'der'),
                    ('Memoria', 86, 'der')]
        nombres = [nombre_config(c) for c in self._configuraciones()]
        filas = []
        colores = []
        for f in self.posiciones:
            indice = nombres.index(f['configuracion']) \
                if f['configuracion'] in nombres else 4
            color = COLORES_CONFIG[indice % 5]
            colores.append(color)
            filas.append([
                (f['configuracion'], color), str(f['partidas']),
                str(f['victorias']), str(f['empates']), str(f['derrotas']),
                str(f['puntos']), tema.formato_tiempo(f['tiempo_medio']),
                tema.formato_numero(f['generados_medio']),
                tema.formato_numero(f['memoria_max'])])
        tabla = pygame.Rect(rect.x + 20, rect.y + 36, 922, 200)
        y = dibujar_tabla(sup, tabla, columnas, filas, alto_fila=28, tam=12)
        tema.texto(sup, 'Puntos: 3 por victoria y 1 por empate. Cada pareja '
                   'juega dos partidas por ronda, una con cada algoritmo '
                   'empezando.', (rect.x + 20, y + 8), 11, tema.TEXTO_SUAVE)
        etiquetas = [f['configuracion'] for f in self.posiciones]
        ancho, alto = 464, 40 + 26 * len(self.posiciones)
        y0 = y + 34
        graficas = [
            ('PUNTOS', 'puntos', False, None),
            ('TIEMPO MEDIO POR JUGADA', 'tiempo_medio', False,
             tema.formato_tiempo),
            ('NODOS GENERADOS POR JUGADA', 'generados_medio', True, None),
            ('LONGITUD MEDIA DE LA PARTIDA (FICHAS)', 'fichas_medio', False,
             lambda v: f'{v:.1f}'),
        ]
        for i, (titulo, llave, logaritmica, formato) in enumerate(graficas):
            fila, columna = divmod(i, 2)
            zona = pygame.Rect(rect.x + 20 + columna * (ancho + 20),
                               y0 + fila * (alto + 12), ancho, alto)
            dibujar_barras(sup, zona, titulo, etiquetas,
                           [f[llave] for f in self.posiciones], colores,
                           logaritmica, formato)
