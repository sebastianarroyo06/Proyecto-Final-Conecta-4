"""
Pantalla principal: partida entre agentes (o contra un humano) con la
animación de la solución y del proceso de búsqueda.

Zonas de la pantalla:
    izquierda -> configuración de los jugadores (algoritmo, dificultad,
                 heurística) y opciones
    centro    -> tablero, controles de reproducción y lista de jugadas
    derecha   -> árbol de búsqueda animado, estado interno del algoritmo
                 y métricas de la partida
"""
import pygame

from conecta4.config import NOMBRES_NIVELES, PARAMETROS
from gui import tema
from gui.sesion import SesionPartida
from gui.vista_busqueda import (ReproductorTraza, dibujar_arbol,
                                dibujar_estado_interno, fantasmas_de)
from gui.vista_tablero import VistaTablero
from gui.widgets import (Boton, Casilla, Deslizador, Segmentado,
                         dibujar_tabla)

TIPOS = [('humano', 'Humano'), ('minimax', 'Minimax'),
         ('alfabeta', 'Alfa-beta'), ('mcts', 'MCTS')]
NIVELES = [('facil', 'Fácil'), ('medio', 'Medio'), ('dificil', 'Difícil')]
HEURISTICAS = [('h1', 'h1 amenazas'), ('h2', 'h2 posicional')]

# Duración aproximada (en eventos) de una traza "normal"; se usa para que
# la animación de una jugada dure lo mismo sin importar su longitud.
EVENTOS_BASE = 450


class PantallaJugar:
    """Pantalla de juego y animación."""

    def __init__(self, app):
        self.app = app
        self.juego = app.juego
        self.vista = VistaTablero(294, 150, 60)
        self.config = {
            1: {'tipo': 'alfabeta', 'nivel': 'medio', 'heuristica': 'h1'},
            2: {'tipo': 'mcts', 'nivel': 'medio', 'heuristica': 'h1'},
        }
        self.reproduciendo = False
        self.animar = True
        self.mostrar_linea = True
        self.velocidad = 120            # Eventos por segundo
        self.rep = None                 # Reproductor de la traza visible
        self.indice = 0                 # Evento actual de la traza
        self._registro = None           # Jugada cuya traza se muestra
        self._cayendo = None            # Jugada cuya ficha está cayendo
        self._acumulado = 0.0
        self._espera = 0.0
        self._columna_raton = None
        self._crear_controles()
        self.nueva_partida()

    # ------------------------------------------------------------------
    # Controles
    # ------------------------------------------------------------------
    def _crear_controles(self):
        x, ancho = 24, 228
        self.seg_modo = Segmentado(
            (x, 106, ancho, 28),
            [('ava', 'Agente vs Agente'), ('hva', 'Humano vs Agente')],
            'ava', self._cambiar_modo, tam=11)
        self.controles_jugador = {}
        for jugador, y in ((1, 172), (2, 318)):
            self.controles_jugador[jugador] = {
                'y': y,
                'tipo': Segmentado((x, y, ancho, 26), TIPOS,
                                   self.config[jugador]['tipo'],
                                   lambda v, j=jugador: self._cambiar(
                                       j, 'tipo', v), tam=10),
                'nivel': Segmentado((x, y + 32, ancho, 26), NIVELES,
                                    self.config[jugador]['nivel'],
                                    lambda v, j=jugador: self._cambiar(
                                        j, 'nivel', v), tam=11),
                'heuristica': Segmentado((x, y + 64, ancho, 26), HEURISTICAS,
                                         self.config[jugador]['heuristica'],
                                         lambda v, j=jugador: self._cambiar(
                                             j, 'heuristica', v), tam=11),
            }
        self.casilla_animar = Casilla((x, 466), 'Animar la búsqueda', True,
                                      self._fijar_animar)
        self.casilla_linea = Casilla((x, 492), 'Mostrar línea analizada',
                                     True, self._fijar_linea)
        self.boton_nueva = Boton((x, 530, ancho, 34), 'Nueva partida',
                                 self.nueva_partida, primario=True)
        self.boton_editor = Boton((x, 572, ancho, 30), 'Editar instancia…',
                                  lambda: self.app.ir_a('editor'))
        # Controles de reproducción
        nombres = [('inicio', self.ir_inicio, 'Inicio'),
                   ('jugada_atras', self.jugada_atras, 'Jugada'),
                   ('paso_atras', self.paso_atras, 'Paso'),
                   ('play', self.alternar_reproduccion, 'Iniciar'),
                   ('paso_adelante', self.paso_adelante, 'Paso'),
                   ('jugada_adelante', self.jugada_adelante, 'Jugada'),
                   ('fin', self.ir_final, 'Final')]
        self.botones_repro = []
        x0 = 326
        for i, (icono, accion, etiqueta) in enumerate(nombres):
            boton = Boton((x0 + i * 52, 536, 44, 34), '', accion, icono=icono,
                          primario=(icono == 'play'))
            boton.pie = etiqueta
            self.botones_repro.append(boton)
        self.boton_play = self.botones_repro[3]
        self.deslizador = Deslizador((386, 610, 250, 12), 10, 600,
                                     self.velocidad, self._fijar_velocidad)

    def _todos_los_controles(self):
        controles = [self.seg_modo, self.casilla_animar, self.casilla_linea,
                     self.boton_nueva, self.boton_editor, self.deslizador]
        for jugador in (1, 2):
            c = self.controles_jugador[jugador]
            controles += [c['tipo'], c['nivel'], c['heuristica']]
        return controles + self.botones_repro

    def _fijar_animar(self, valor):
        self.animar = valor

    def _fijar_linea(self, valor):
        self.mostrar_linea = valor

    def _fijar_velocidad(self, valor):
        self.velocidad = valor

    def _cambiar_modo(self, modo):
        """Agente vs Agente: los dos son agentes. Humano vs Agente: el
        jugador 1 pasa a ser humano."""
        if modo == 'hva':
            self.config[1]['tipo'] = 'humano'
            if self.config[2]['tipo'] == 'humano':
                self.config[2]['tipo'] = 'alfabeta'
        else:
            for jugador in (1, 2):
                if self.config[jugador]['tipo'] == 'humano':
                    self.config[jugador]['tipo'] = 'alfabeta'
        self._sincronizar_controles()
        self._config_cambiada()

    def _cambiar(self, jugador, llave, valor):
        self.config[jugador][llave] = valor
        self._sincronizar_controles()
        self._config_cambiada()

    def _sincronizar_controles(self):
        """Pone los controles de acuerdo con la configuración actual."""
        for jugador in (1, 2):
            c = self.controles_jugador[jugador]
            tipo = self.config[jugador]['tipo']
            c['tipo'].valor = tipo
            c['nivel'].valor = self.config[jugador]['nivel']
            c['heuristica'].valor = self.config[jugador]['heuristica']
            c['nivel'].habilitado = tipo != 'humano'
            c['heuristica'].habilitado = tipo == 'alfabeta'
        humanos = [j for j in (1, 2) if self.config[j]['tipo'] == 'humano']
        self.seg_modo.valor = 'ava' if not humanos else 'hva'

    def _config_cambiada(self):
        """Al cambiar un jugador se conserva lo jugado y se descarta lo
        que el agente anterior había calculado para el futuro."""
        copia = {j: dict(self.config[j]) for j in (1, 2)}
        self.sesion.cambiar_config(copia)
        if self._registro is not None and \
                self._registro not in self.sesion.historial:
            self._fijar_registro(self.sesion.ultimo(), al_final=True)

    # ------------------------------------------------------------------
    # Partida
    # ------------------------------------------------------------------
    def nueva_partida(self):
        """Empieza una partida desde la instancia definida en el editor."""
        if hasattr(self, 'sesion'):
            self.sesion.cancelar()
        estado_inicial = self.juego.desde_jugadas(self.app.instancia)
        copia = {j: dict(self.config[j]) for j in (1, 2)}
        self.sesion = SesionPartida(self.juego, estado_inicial, copia,
                                    semilla=self.app.semilla)
        self.vista.caida = None
        self._cayendo = None
        self._fijar_registro(None)
        self._sincronizar_controles()
        # Si hay un humano la partida corre sola; entre agentes espera a
        # que el usuario pulse Iniciar.
        self.reproduciendo = any(self.sesion.es_humano(j) for j in (1, 2))

    def _fijar_registro(self, registro, al_final=False):
        """Elige la jugada cuya búsqueda se muestra en el panel derecho."""
        self._registro = registro
        if registro is not None and registro.traza is not None:
            self.rep = ReproductorTraza(registro.traza)
            self.indice = self.rep.total if al_final else 0
        else:
            self.rep = None
            self.indice = 0
        self._acumulado = 0.0

    def _total_eventos(self):
        return self.rep.total if self.rep is not None else 0

    def _pendiente(self):
        """Devuelve la jugada pendiente y se asegura de que el panel de
        búsqueda esté mostrando esa jugada (el hilo del agente puede
        haberla terminado de calcular entre dos cuadros)."""
        pendiente = self.sesion.pendiente()
        if pendiente is not None and pendiente is not self._registro:
            self._fijar_registro(pendiente)
        return pendiente

    def _aplicar(self, registro):
        """Aplica la jugada en el tablero con la animación de caída."""
        columna = registro.accion
        fila = int((registro.estado_antes[:, columna] == 0).sum()) - 1
        self.vista.iniciar_caida(columna, fila, registro.jugador)
        self._cayendo = registro
        self.indice = self._total_eventos()
        self.sesion.aplicar_pendiente()
        self._espera = 0.25

    # ------------------------------------------------------------------
    # Controles de reproducción
    # ------------------------------------------------------------------
    def alternar_reproduccion(self):
        self.reproduciendo = not self.reproduciendo

    def paso_adelante(self):
        """Avanza un paso de la búsqueda; si la búsqueda ya terminó,
        aplica la jugada."""
        self.reproduciendo = False
        pendiente = self._pendiente()
        if pendiente is None or self.vista.caida is not None:
            return
        if self.indice < self._total_eventos():
            self.indice += 1
        else:
            self._aplicar(pendiente)

    def paso_atras(self):
        """Retrocede un paso de la búsqueda; si está al inicio de la
        búsqueda, deshace la jugada anterior."""
        self.reproduciendo = False
        if self.vista.caida is not None:
            return
        if self._pendiente() is not None and self.indice > 0:
            self.indice -= 1
        elif self.sesion.cursor > 0:
            self.sesion.retroceder()
            self._fijar_registro(self.sesion.pendiente(), al_final=True)

    def jugada_adelante(self):
        """Salta al final de la búsqueda y aplica la jugada."""
        self.reproduciendo = False
        pendiente = self._pendiente()
        if pendiente is not None and self.vista.caida is None:
            self._aplicar(pendiente)

    def jugada_atras(self):
        """Vuelve al inicio de la jugada actual o de la anterior."""
        self.reproduciendo = False
        if self.vista.caida is not None:
            return
        if self._pendiente() is not None and self.indice > 0:
            self.indice = 0
        elif self.sesion.cursor > 0:
            self.sesion.retroceder()
            self._fijar_registro(self.sesion.pendiente(), al_final=False)

    def ir_inicio(self):
        """Vuelve al estado inicial de la partida."""
        self.reproduciendo = False
        self.vista.caida = None
        self._cayendo = None
        self.sesion.ir_a(0)
        self._fijar_registro(self.sesion.pendiente(), al_final=False)

    def ir_final(self):
        """Salta a la última jugada calculada."""
        self.reproduciendo = False
        self.vista.caida = None
        self._cayendo = None
        self.sesion.ir_a(len(self.sesion.historial))
        self._fijar_registro(self.sesion.ultimo(), al_final=True)

    # ------------------------------------------------------------------
    # Eventos
    # ------------------------------------------------------------------
    def manejar_evento(self, evento):
        for control in self._todos_los_controles():
            if control.manejar_evento(evento):
                return
        if evento.type == pygame.MOUSEMOTION:
            self._columna_raton = self.vista.columna_en(evento.pos)
        elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            columna = self.vista.columna_en(evento.pos)
            if columna is not None:
                self._clic_en_columna(columna)
        elif evento.type == pygame.KEYDOWN:
            if evento.key == pygame.K_SPACE:
                self.alternar_reproduccion()
            elif evento.key == pygame.K_RIGHT:
                self.paso_adelante()
            elif evento.key == pygame.K_LEFT:
                self.paso_atras()
            elif evento.key == pygame.K_n:
                self.nueva_partida()

    def _clic_en_columna(self, columna):
        """Jugada del humano."""
        if not self.sesion.es_turno_humano() or self.vista.caida is not None:
            return
        registro = self.sesion.jugar_humano(columna)
        if registro is not None:
            self._fijar_registro(registro)
            self._aplicar(registro)
            self.reproduciendo = True

    # ------------------------------------------------------------------
    # Actualización (se llama en cada cuadro)
    # ------------------------------------------------------------------
    def actualizar(self, dt):
        if self.vista.actualizar(dt):
            self._cayendo = None
        if self.vista.caida is not None:
            return
        sesion = self.sesion
        pendiente = self._pendiente()
        if pendiente is None:
            # No hay jugada calculada: se le pide al agente en turno
            if not sesion.terminado() and not sesion.es_turno_humano():
                sesion.solicitar_decision()
            elif sesion.terminado():
                self.reproduciendo = False
            return
        if not self.reproduciendo:
            return
        self._espera -= dt
        if self._espera > 0:
            return
        total = self._total_eventos()
        if self.animar and self.indice < total:
            # La velocidad se ajusta para que una traza larga (MCTS) dure
            # lo mismo que una corta
            factor = max(1.0, total / EVENTOS_BASE)
            self._acumulado += self.velocidad * factor * dt
            pasos = int(self._acumulado)
            self._acumulado -= pasos
            self.indice = min(total, self.indice + pasos)
            if self.indice >= total:
                self._espera = 0.5      # Pausa para ver el resultado
        else:
            self._aplicar(pendiente)

    # ------------------------------------------------------------------
    # Dibujo
    # ------------------------------------------------------------------
    def dibujar(self, sup):
        self._dibujar_configuracion(sup)
        self._dibujar_centro(sup)
        self._dibujar_derecha(sup)

    def _dibujar_configuracion(self, sup):
        rect = pygame.Rect(12, 56, 252, 652)
        tema.panel(sup, rect, 'CONFIGURACIÓN')
        tema.texto(sup, 'Modo de juego', (24, 86), 12, tema.TEXTO_SUAVE)
        self.seg_modo.dibujar(sup)
        for jugador in (1, 2):
            c = self.controles_jugador[jugador]
            y = c['y']
            pygame.draw.circle(sup, tema.COLOR_JUGADOR[jugador],
                               (31, y - 14), 7)
            orden = 'empieza' if jugador == 1 else 'segundo'
            tema.texto(sup, f'Jugador {jugador} ({orden})', (44, y - 14), 13,
                       tema.TEXTO, True, 'midleft')
            c['tipo'].dibujar(sup)
            c['nivel'].dibujar(sup)
            c['heuristica'].dibujar(sup)
            tema.texto(sup, self._detalle_jugador(jugador), (24, y + 96), 11,
                       tema.TEXTO_SUAVE)
        tema.texto(sup, 'Opciones', (24, 444), 12, tema.TEXTO_SUAVE)
        self.casilla_animar.dibujar(sup)
        self.casilla_linea.dibujar(sup)
        self.boton_nueva.dibujar(sup)
        self.boton_editor.dibujar(sup)
        fichas = len(self.app.instancia)
        if fichas == 0:
            instancia = 'Instancia: tablero vacío'
        else:
            instancia = f'Instancia: {fichas} fichas iniciales'
        tema.texto(sup, instancia, (24, 614), 11, tema.TEXTO_SUAVE)
        tema.texto_ajustado(
            sup, 'Atajos: Espacio = iniciar/pausar, flechas = paso a paso, '
            'N = nueva partida.', pygame.Rect(24, 640, 228, 60), 11,
            tema.TEXTO_SUAVE)

    def _detalle_jugador(self, jugador):
        c = self.config[jugador]
        if c['tipo'] == 'humano':
            return 'Juega una persona con el ratón.'
        parametro = PARAMETROS[c['tipo']][c['nivel']]
        nivel = NOMBRES_NIVELES[c['nivel']].lower()
        if c['tipo'] == 'mcts':
            return f'Nivel {nivel}: {parametro} simulaciones/jugada'
        return f'Nivel {nivel}: profundidad límite d = {parametro}'

    def _texto_estado(self):
        """Mensajes de estado que van encima del tablero."""
        sesion = self.sesion
        if sesion.error is not None:
            return 'Error en la búsqueda', sesion.error.splitlines()[-1]
        if sesion.terminado():
            ganador = self.juego.ganador(sesion.estado)
            fichas = int((sesion.estado != 0).sum())
            if ganador == 0:
                return 'Fin de la partida: empate', \
                    f'Tablero lleno ({fichas} fichas).'
            return (f'Fin de la partida: gana el jugador {ganador} '
                    f'({tema.NOMBRE_COLOR[ganador]})',
                    f'{sesion.descripcion(ganador)} · partida de '
                    f'{fichas} fichas')
        jugador = sesion.jugador_en_turno()
        titulo = (f'Turno del jugador {jugador} '
                  f'({tema.NOMBRE_COLOR[jugador]}): '
                  f'{sesion.descripcion(jugador)}')
        pendiente = sesion.pendiente()
        if sesion.es_turno_humano() and pendiente is None:
            return titulo, 'Tu turno: haz clic en una columna.'
        if pendiente is None:
            return titulo, 'Pensando…'
        total = self._total_eventos()
        if pendiente.es_humano:
            detalle = f'Jugada del humano: columna {pendiente.accion}.'
        elif self.indice < total:
            detalle = f'Búsqueda: paso {self.indice} de {total}.'
        else:
            detalle = (f'Búsqueda terminada: elige la columna '
                       f'{pendiente.accion}.')
        if not self.reproduciendo:
            if sesion.cursor == 0 and self.indice == 0:
                detalle = 'Pulsa Iniciar (o Espacio) para ver la búsqueda.'
            else:
                detalle += '  (en pausa)'
        return titulo, detalle

    def _etiquetas_columnas(self):
        """Valor de cada columna según lo que la búsqueda lleva hasta el
        paso actual. Devuelve (etiquetas, columna_elegida)."""
        if self.rep is None or self._registro is None:
            return None, None
        rep = self.rep
        etiquetas = {}
        for a in range(7):
            nodo = rep.nodos.get((a,))
            if nodo is None:
                continue
            if rep.es_mcts:
                etiquetas[a] = (str(nodo['n']), tema.TEXTO)
            elif 'valor' in nodo:
                cadena = tema.formato_valor(nodo['valor'])
                if nodo.get('cota') == '<=':
                    cadena = '≤' + cadena
                etiquetas[a] = (cadena, tema.TEXTO)
        elegida = None
        if rep.k >= rep.total:
            elegida = self._registro.accion
            if elegida in etiquetas:
                etiquetas[elegida] = (etiquetas[elegida][0], tema.BLANCO)
        return etiquetas, elegida

    def _dibujar_centro(self, sup):
        rect = pygame.Rect(276, 56, 456, 652)
        tema.panel(sup, rect)
        titulo, detalle = self._texto_estado()
        tema.texto(sup, titulo, (rect.centerx, 76), 14, tema.TEXTO, True,
                   'center')
        tema.texto(sup, detalle, (rect.centerx, 98), 12, tema.NARANJA,
                   ancla='center')
        sesion = self.sesion
        if self.rep is not None:
            self.rep.ir_a(self.indice)
        # Mientras la ficha cae se dibuja el tablero anterior a la jugada
        if self._cayendo is not None and self.vista.caida is not None:
            estado = self._cayendo.estado_antes
        else:
            estado = sesion.estado
        linea = self.juego.linea_ganadora(estado)
        ultima = None
        if sesion.ultimo() is not None and self.vista.caida is None:
            u = sesion.ultimo()
            fila = int((u.estado_antes[:, u.accion] == 0).sum()) - 1
            ultima = (fila, u.accion)
        fantasmas = None
        etiquetas, elegida = None, None
        if sesion.pendiente() is not None and self.vista.caida is None:
            etiquetas, elegida = self._etiquetas_columnas()
            if self.mostrar_linea:
                fantasmas = fantasmas_de(self.rep, self.juego)
        columna_resaltada = None
        if sesion.es_turno_humano() and self.vista.caida is None:
            columna_resaltada = self._columna_raton
        self.vista.dibujar(sup, estado, linea=linea, ultima=ultima,
                           fantasmas=fantasmas,
                           columna_resaltada=columna_resaltada,
                           jugador_turno=self.juego.player(estado),
                           etiquetas=etiquetas, columna_elegida=elegida)
        # Controles de reproducción
        self.boton_play.icono = 'pausa' if self.reproduciendo else 'play'
        self.boton_play.pie = 'Pausar' if self.reproduciendo else 'Iniciar'
        for boton in self.botones_repro:
            boton.dibujar(sup)
            tema.texto(sup, boton.pie, (boton.rect.centerx, 581), 10,
                       tema.TEXTO_SUAVE, ancla='center')
        tema.texto(sup, 'Velocidad', (294, 616), 12, tema.TEXTO_SUAVE,
                   ancla='midleft')
        self.deslizador.dibujar(sup)
        factor = max(1.0, self._total_eventos() / EVENTOS_BASE)
        tema.texto(sup, f'{int(self.velocidad * factor)} pasos/s',
                   (650, 616), 11, tema.TEXTO_SUAVE, ancla='midleft')
        self._dibujar_jugadas(sup)

    def _dibujar_jugadas(self, sup):
        """Secuencia de jugadas de la partida (la solución)."""
        sesion = self.sesion
        tema.texto(sup, 'Secuencia de jugadas (columna):', (294, 640), 11,
                   tema.TEXTO_SUAVE)
        if not sesion.historial:
            return
        # Solo se muestran las jugadas que ya se han visto en el tablero
        for i, registro in enumerate(sesion.historial[:sesion.maximo]):
            fila, columna = divmod(i, 21)
            x = 304 + columna * 20
            y = 668 + fila * 22
            aplicada = i < sesion.cursor
            color = tema.COLOR_JUGADOR[registro.jugador]
            if not aplicada:
                color = tuple(int(v * 0.35) for v in color)
            pygame.draw.circle(sup, color, (x, y), 9)
            tema.texto(sup, str(registro.accion), (x, y), 11, tema.FONDO,
                       True, 'center')
            if i == sesion.cursor - 1:
                pygame.draw.circle(sup, tema.BLANCO, (x, y), 10, 2)

    def _dibujar_derecha(self, sup):
        rect_arbol = pygame.Rect(744, 56, 524, 330)
        titulo = 'PROCESO DE BÚSQUEDA'
        if self._registro is not None and not self._registro.es_humano:
            titulo += (f' · JUGADOR {self._registro.jugador}: '
                       f'{self._registro.descripcion.upper()}')
        dibujar_arbol(sup, rect_arbol, self.rep, titulo)
        dibujar_estado_interno(sup, pygame.Rect(744, 394, 524, 144),
                               self.rep)
        self._dibujar_metricas(sup, pygame.Rect(744, 546, 524, 162))

    def _dibujar_metricas(self, sup, rect):
        tema.panel(sup, rect, 'MÉTRICAS DE LA PARTIDA')
        columnas = [('Jugador', 152, 'izq'), ('Jug.', 36, 'der'),
                    ('t última', 70, 'der'), ('t media', 70, 'der'),
                    ('Generados', 74, 'der'), ('Expand.', 60, 'der'),
                    ('Mem.', 42, 'der')]
        filas = []
        for jugador in (1, 2):
            nombre = (f'J{jugador} · {self.sesion.descripcion(jugador)}',
                      tema.COLOR_JUGADOR[jugador])
            r = self.sesion.resumen(jugador)
            if r is None:
                filas.append([nombre, '-', '-', '-', '-', '-', '-'])
            else:
                filas.append([
                    nombre, str(r['jugadas']),
                    tema.formato_tiempo(r['tiempo_ultimo']),
                    tema.formato_tiempo(r['tiempo_medio']),
                    tema.formato_numero(r['generados_ultimo']),
                    tema.formato_numero(r['expandidos_ultimo']),
                    tema.formato_numero(r['memoria_max'])])
        tabla = pygame.Rect(rect.x + 10, rect.y + 30, rect.width - 20, 72)
        y = dibujar_tabla(sup, tabla, columnas, filas, alto_fila=23, tam=11)
        # Detalle de la jugada cuya búsqueda se está mostrando
        registro = self._registro
        # El detalle solo se muestra cuando la búsqueda ya se vio completa
        visible = registro is not None and self.indice >= self._total_eventos()
        if visible and registro.metricas is not None:
            m = registro.metricas
            optima = {True: 'sí', False: 'no', None: 'n. d.'}[registro.optima]
            linea_1 = (f'Jugada mostrada: columna {m.accion} · valor '
                       f'{tema.formato_valor(m.valor)} · {m.podas} podas · '
                       f'{m.evaluaciones} hojas evaluadas')
            linea_2 = (f'{m.terminales} terminales · profundidad máx. '
                       f'{m.profundidad_max} · ¿óptima según el '
                       f'solucionador exacto?: {optima}')
            if m.simulaciones:
                linea_1 = (f'Jugada mostrada: columna {m.accion} · '
                           f'recompensa media {m.valor:.2f} · '
                           f'{m.simulaciones} simulaciones')
                linea_2 = (f'árbol de {m.memoria_max} nodos · profundidad '
                           f'{m.profundidad_max} · ¿óptima según el '
                           f'solucionador exacto?: {optima}')
            tema.texto(sup, linea_1, (rect.x + 12, y + 8), 11, tema.TEXTO)
            tema.texto(sup, linea_2, (rect.x + 12, y + 26), 11,
                       tema.TEXTO_SUAVE)
        elif visible and registro.es_humano:
            optima = {True: 'sí', False: 'no', None: 'n. d.'}[registro.optima]
            tema.texto(sup, f'Jugada del humano: columna {registro.accion}'
                       f' · ¿óptima?: {optima}', (rect.x + 12, y + 8), 11,
                       tema.TEXTO)
        else:
            tema.texto(sup, 'Generados/Expand.: nodos de la última jugada. '
                       'Mem.: máximo de nodos en memoria.',
                       (rect.x + 12, y + 8), 11, tema.TEXTO_SUAVE)
