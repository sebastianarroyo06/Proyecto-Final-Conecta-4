"""
Controles (widgets) de la interfaz: botones, selectores, deslizadores,
casillas de verificación, tablas y gráficas de barras.

Cada control tiene dos métodos:
    manejar_evento(evento) -> procesa clics y movimiento del ratón
    dibujar(sup)           -> se dibuja en la superficie
"""
import math

import pygame

from gui import tema


def dibujar_icono(sup, nombre, rect, color):
    """Dibuja los íconos de los controles de reproducción con polígonos.

    nombre: 'play', 'pausa', 'paso_adelante', 'paso_atras',
            'jugada_adelante', 'jugada_atras', 'inicio', 'fin'
    """
    cx, cy = rect.center
    t = min(rect.width, rect.height) * 0.26     # Medio tamaño del ícono

    def triangulo(x, direccion, escala=1.0):
        a = t * escala
        if direccion > 0:
            puntos = [(x - a * 0.8, cy - a), (x - a * 0.8, cy + a),
                      (x + a * 0.8, cy)]
        else:
            puntos = [(x + a * 0.8, cy - a), (x + a * 0.8, cy + a),
                      (x - a * 0.8, cy)]
        pygame.draw.polygon(sup, color, puntos)

    def barra(x, ancho=0.32):
        pygame.draw.rect(sup, color,
                         (x - t * ancho / 2, cy - t, t * ancho, 2 * t))

    if nombre == 'play':
        triangulo(cx + t * 0.15, 1, 1.15)
    elif nombre == 'pausa':
        barra(cx - t * 0.45, 0.5)
        barra(cx + t * 0.45, 0.5)
    elif nombre == 'paso_adelante':
        triangulo(cx - t * 0.25, 1)
        barra(cx + t * 0.85)
    elif nombre == 'paso_atras':
        triangulo(cx + t * 0.25, -1)
        barra(cx - t * 0.85)
    elif nombre == 'jugada_adelante':
        triangulo(cx - t * 0.7, 1, 0.9)
        triangulo(cx + t * 0.7, 1, 0.9)
    elif nombre == 'jugada_atras':
        triangulo(cx + t * 0.7, -1, 0.9)
        triangulo(cx - t * 0.7, -1, 0.9)
    elif nombre == 'inicio':
        barra(cx - t * 1.25)
        triangulo(cx - t * 0.35, -1, 0.9)
        triangulo(cx + t * 0.95, -1, 0.9)
    elif nombre == 'fin':
        triangulo(cx - t * 0.95, 1, 0.9)
        triangulo(cx + t * 0.35, 1, 0.9)
        barra(cx + t * 1.25)


class Boton:
    """Botón con texto o con ícono."""

    def __init__(self, rect, etiqueta='', accion=None, icono=None,
                 primario=False, tam=13):
        self.rect = pygame.Rect(rect)
        self.etiqueta = etiqueta
        self.accion = accion
        self.icono = icono
        self.primario = primario
        self.tam = tam
        self.habilitado = True
        self.visible = True
        self.activo = False         # Se dibuja resaltado (p.ej. pestaña)
        self._encima = False

    def manejar_evento(self, evento):
        if not (self.visible and self.habilitado):
            return False
        if evento.type == pygame.MOUSEMOTION:
            self._encima = self.rect.collidepoint(evento.pos)
        elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            if self.rect.collidepoint(evento.pos):
                if self.accion is not None:
                    self.accion()
                return True
        return False

    def dibujar(self, sup):
        if not self.visible:
            return
        if not self.habilitado:
            fondo, color = tema.PANEL, tema.BORDE
        elif self.primario or self.activo:
            fondo = tema.ACENTO if self._encima else tema.ACENTO_OSCURO
            color = tema.BLANCO
        else:
            fondo = tema.BORDE if self._encima else tema.PANEL_CLARO
            color = tema.TEXTO
        pygame.draw.rect(sup, fondo, self.rect, border_radius=7)
        if self.icono is not None:
            dibujar_icono(sup, self.icono, self.rect, color)
        else:
            tema.texto(sup, self.etiqueta, self.rect.center, self.tam,
                       color, ancla='center')


class Segmentado:
    """Selector de una opción entre varias, dibujadas como segmentos."""

    def __init__(self, rect, opciones, valor, al_cambiar=None, tam=12):
        """
        Input:
            - opciones, lista de parejas (valor, etiqueta)
            - valor, valor seleccionado al inicio
            - al_cambiar, función que recibe el nuevo valor
        """
        self.rect = pygame.Rect(rect)
        self.opciones = opciones
        self.valor = valor
        self.al_cambiar = al_cambiar
        self.tam = tam
        self.habilitado = True
        self.visible = True
        self._encima = None

    def _rect_opcion(self, i):
        ancho = self.rect.width / len(self.opciones)
        return pygame.Rect(self.rect.x + round(i * ancho), self.rect.y,
                           round(ancho), self.rect.height)

    def manejar_evento(self, evento):
        if not (self.visible and self.habilitado):
            return False
        if evento.type == pygame.MOUSEMOTION:
            self._encima = None
            for i in range(len(self.opciones)):
                if self._rect_opcion(i).collidepoint(evento.pos):
                    self._encima = i
        elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            for i, (valor, _) in enumerate(self.opciones):
                if self._rect_opcion(i).collidepoint(evento.pos):
                    if valor != self.valor:
                        self.valor = valor
                        if self.al_cambiar is not None:
                            self.al_cambiar(valor)
                    return True
        return False

    def dibujar(self, sup):
        if not self.visible:
            return
        pygame.draw.rect(sup, tema.PANEL_CLARO, self.rect, border_radius=7)
        for i, (valor, etiqueta) in enumerate(self.opciones):
            r = self._rect_opcion(i)
            seleccionado = valor == self.valor
            if seleccionado and self.habilitado:
                pygame.draw.rect(sup, tema.ACENTO_OSCURO, r, border_radius=7)
            elif self._encima == i and self.habilitado:
                pygame.draw.rect(sup, tema.BORDE, r, border_radius=7)
            if not self.habilitado:
                color = tema.BORDE
            elif seleccionado:
                color = tema.BLANCO
            else:
                color = tema.TEXTO
            tema.texto(sup, etiqueta, r.center, self.tam, color,
                       ancla='center')


class Deslizador:
    """Barra deslizante para elegir un número."""

    def __init__(self, rect, minimo, maximo, valor, al_cambiar=None,
                 entero=True):
        self.rect = pygame.Rect(rect)
        self.minimo = minimo
        self.maximo = maximo
        self.valor = valor
        self.al_cambiar = al_cambiar
        self.entero = entero
        self.visible = True
        self._arrastrando = False

    def _fijar_desde_x(self, x):
        fraccion = (x - self.rect.x) / self.rect.width
        fraccion = min(1.0, max(0.0, fraccion))
        valor = self.minimo + fraccion * (self.maximo - self.minimo)
        if self.entero:
            valor = int(round(valor))
        if valor != self.valor:
            self.valor = valor
            if self.al_cambiar is not None:
                self.al_cambiar(valor)

    def manejar_evento(self, evento):
        if not self.visible:
            return False
        zona = self.rect.inflate(12, 16)
        if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            if zona.collidepoint(evento.pos):
                self._arrastrando = True
                self._fijar_desde_x(evento.pos[0])
                return True
        elif evento.type == pygame.MOUSEBUTTONUP and evento.button == 1:
            self._arrastrando = False
        elif evento.type == pygame.MOUSEMOTION and self._arrastrando:
            self._fijar_desde_x(evento.pos[0])
            return True
        return False

    def dibujar(self, sup):
        if not self.visible:
            return
        cy = self.rect.centery
        pygame.draw.line(sup, tema.BORDE, (self.rect.x, cy),
                         (self.rect.right, cy), 4)
        fraccion = (self.valor - self.minimo) / (self.maximo - self.minimo)
        x = self.rect.x + fraccion * self.rect.width
        pygame.draw.line(sup, tema.ACENTO, (self.rect.x, cy), (x, cy), 4)
        pygame.draw.circle(sup, tema.BLANCO, (int(x), cy), 8)


class Casilla:
    """Casilla de verificación con etiqueta."""

    def __init__(self, pos, etiqueta, valor=False, al_cambiar=None, tam=13):
        self.pos = pos
        self.etiqueta = etiqueta
        self.valor = valor
        self.al_cambiar = al_cambiar
        self.tam = tam
        self.visible = True
        ancho = 26 + tema.ancho_texto(etiqueta, tam)
        self.rect = pygame.Rect(pos[0], pos[1], ancho, 20)

    def manejar_evento(self, evento):
        if not self.visible:
            return False
        if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            if self.rect.collidepoint(evento.pos):
                self.valor = not self.valor
                if self.al_cambiar is not None:
                    self.al_cambiar(self.valor)
                return True
        return False

    def dibujar(self, sup):
        if not self.visible:
            return
        caja = pygame.Rect(self.pos[0], self.pos[1] + 1, 18, 18)
        if self.valor:
            pygame.draw.rect(sup, tema.ACENTO_OSCURO, caja, border_radius=4)
            puntos = [(caja.x + 4, caja.y + 9), (caja.x + 8, caja.y + 13),
                      (caja.x + 14, caja.y + 5)]
            pygame.draw.lines(sup, tema.BLANCO, False, puntos, 2)
        else:
            pygame.draw.rect(sup, tema.PANEL_CLARO, caja, border_radius=4)
            pygame.draw.rect(sup, tema.BORDE, caja, 1, border_radius=4)
        tema.texto(sup, self.etiqueta, (caja.right + 8, caja.centery),
                   self.tam, tema.TEXTO, ancla='midleft')


# ----------------------------------------------------------------------
# Tablas y gráficas
# ----------------------------------------------------------------------
def dibujar_tabla(sup, rect, columnas, filas, alto_fila=24, tam=12,
                  resaltar=None):
    """Dibuja una tabla sencilla.

    Input:
        - rect, zona donde va la tabla
        - columnas, lista de (titulo, ancho, alineacion) con alineacion
          'izq' o 'der'
        - filas, lista de listas de textos (o parejas (texto, color))
        - resaltar, índice de la fila que se pinta resaltada
    Output:
        - coordenada y donde termina la tabla
    """
    x0, y = rect.x, rect.y
    # Encabezado
    pygame.draw.rect(sup, tema.PANEL_CLARO,
                     (x0, y, rect.width, alto_fila), border_radius=5)
    x = x0
    for titulo, ancho, alineacion in columnas:
        if alineacion == 'der':
            tema.texto(sup, titulo, (x + ancho - 8, y + alto_fila // 2),
                       tam, tema.TEXTO_SUAVE, True, 'midright')
        else:
            tema.texto(sup, titulo, (x + 8, y + alto_fila // 2), tam,
                       tema.TEXTO_SUAVE, True, 'midleft')
        x += ancho
    y += alto_fila
    # Filas
    for i, fila in enumerate(filas):
        if resaltar == i:
            pygame.draw.rect(sup, (30, 58, 95),
                             (x0, y, rect.width, alto_fila), border_radius=5)
        x = x0
        for (titulo, ancho, alineacion), celda in zip(columnas, fila):
            if isinstance(celda, tuple):
                contenido, color = celda
            else:
                contenido, color = celda, tema.TEXTO
            if alineacion == 'der':
                tema.texto(sup, contenido,
                           (x + ancho - 8, y + alto_fila // 2), tam, color,
                           ancla='midright')
            else:
                tema.texto(sup, contenido, (x + 8, y + alto_fila // 2),
                           tam, color, ancla='midleft')
            x += ancho
        y += alto_fila
        pygame.draw.line(sup, tema.PANEL_CLARO, (x0, y - 1),
                         (x0 + rect.width, y - 1))
    return y


def dibujar_barras(sup, rect, titulo, etiquetas, valores, colores=None,
                   logaritmica=False, formato=None):
    """Dibuja una gráfica de barras horizontales.

    Input:
        - etiquetas, nombre de cada barra
        - valores, número de cada barra
        - logaritmica, si la longitud de la barra usa escala logarítmica
          (útil cuando los valores difieren en varios órdenes de magnitud)
        - formato, función que convierte el valor en texto
    """
    tema.panel(sup, rect, titulo, tema.PANEL)
    if formato is None:
        formato = tema.formato_numero
    if not valores:
        return
    ancho_etiqueta = max(tema.ancho_texto(e, 11) for e in etiquetas) + 10
    ancho_valor = max(tema.ancho_texto(formato(v), 11) for v in valores) + 8
    x0 = rect.x + 12 + ancho_etiqueta
    ancho_max = rect.width - 24 - ancho_etiqueta - ancho_valor
    y = rect.y + 32
    alto = min(20, (rect.height - 40) / len(valores) - 4)

    def escala(v):
        if logaritmica:
            return math.log10(max(v, 0) + 1)
        return max(v, 0)

    maximo = max(escala(v) for v in valores) or 1
    for i, (etiqueta, valor) in enumerate(zip(etiquetas, valores)):
        color = tema.ACENTO if colores is None else colores[i]
        tema.texto(sup, etiqueta, (x0 - 8, y + alto / 2), 11,
                   tema.TEXTO_SUAVE, ancla='midright')
        largo = max(2, ancho_max * escala(valor) / maximo)
        pygame.draw.rect(sup, color, (x0, y, largo, alto), border_radius=3)
        tema.texto(sup, formato(valor), (x0 + largo + 6, y + alto / 2), 11,
                   tema.TEXTO, ancla='midleft')
        y += alto + 4
    if logaritmica:
        tema.texto(sup, 'escala log', (rect.right - 10, rect.y + 9), 10,
                   tema.TEXTO_SUAVE, ancla='topright')
