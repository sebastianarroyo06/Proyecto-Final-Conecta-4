"""
Dibujo del tablero de 4 en raya: fichas, animación de caída, línea
ganadora, valores de cada columna y "fichas fantasma" que muestran la
línea de jugadas que el algoritmo está analizando.
"""
import pygame

from conecta4.juego import COLUMNAS, FILAS
from gui import tema


class VistaTablero:
    """Representación gráfica de un estado del entorno."""

    def __init__(self, x, y, celda=60):
        self.x = x
        self.y = y
        self.celda = celda
        self.radio = int(celda * 0.40)
        self.rect = pygame.Rect(x, y, COLUMNAS * celda, FILAS * celda)
        self._frente = self._crear_frente()
        self._discos = {}
        # Ficha que está cayendo: diccionario con columna, fila, jugador,
        # posición vertical actual y velocidad; None si no hay caída.
        self.caida = None

    # ------------------------------------------------------------------
    # Geometría
    # ------------------------------------------------------------------
    def centro(self, fila, columna):
        """Centro en pantalla de la casilla (fila, columna)."""
        return (self.x + columna * self.celda + self.celda // 2,
                self.y + fila * self.celda + self.celda // 2)

    def columna_en(self, pos, margen_superior=40):
        """Columna que corresponde a la posición del ratón, o None."""
        zona = pygame.Rect(self.rect.x, self.rect.y - margen_superior,
                           self.rect.width,
                           self.rect.height + margen_superior)
        if not zona.collidepoint(pos):
            return None
        columna = (pos[0] - self.x) // self.celda
        return int(min(max(columna, 0), COLUMNAS - 1))

    def _crear_frente(self):
        """Crea la cara frontal del tablero: un rectángulo azul con 42
        agujeros transparentes por los que se ven las fichas."""
        frente = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        pygame.draw.rect(frente, tema.TABLERO, frente.get_rect(),
                         border_radius=14)
        for f in range(FILAS):
            for c in range(COLUMNAS):
                cx = c * self.celda + self.celda // 2
                cy = f * self.celda + self.celda // 2
                pygame.draw.circle(frente, tema.TABLERO_OSCURO, (cx, cy),
                                   self.radio + 3)
                pygame.draw.circle(frente, (0, 0, 0, 0), (cx, cy),
                                   self.radio)
        return frente

    def _disco(self, color, alfa=255):
        """Imagen de una ficha (se guarda para no redibujarla)."""
        llave = (color, alfa)
        if llave not in self._discos:
            lado = 2 * self.radio + 2
            disco = pygame.Surface((lado, lado), pygame.SRCALPHA)
            centro = (lado // 2, lado // 2)
            oscuro = tuple(int(v * 0.72) for v in color)
            pygame.draw.circle(disco, oscuro + (alfa,), centro, self.radio)
            pygame.draw.circle(disco, color + (alfa,), centro,
                               self.radio - 4)
            self._discos[llave] = disco
        return self._discos[llave]

    # ------------------------------------------------------------------
    # Animación de caída
    # ------------------------------------------------------------------
    def iniciar_caida(self, columna, fila, jugador):
        """Empieza la animación de una ficha que cae hasta (fila, columna)."""
        self.caida = {'columna': columna, 'fila': fila, 'jugador': jugador,
                      'y': float(self.y - self.celda // 2),
                      'velocidad': 300.0}

    def actualizar(self, dt):
        """Avanza la caída. Devuelve True en el instante en que termina."""
        if self.caida is None:
            return False
        destino = self.centro(self.caida['fila'], self.caida['columna'])[1]
        self.caida['velocidad'] += 4200.0 * dt       # Gravedad
        self.caida['y'] += self.caida['velocidad'] * dt
        if self.caida['y'] >= destino:
            self.caida = None
            return True
        return False

    # ------------------------------------------------------------------
    # Dibujo
    # ------------------------------------------------------------------
    def dibujar(self, sup, estado, linea=None, ultima=None, fantasmas=None,
                columna_resaltada=None, jugador_turno=None,
                etiquetas=None, columna_elegida=None, numeros=True):
        """Dibuja el tablero.

        Input:
            - estado, matriz 6x7 del entorno
            - linea, casillas (fila, columna) del cuatro en línea
            - ultima, casilla (fila, columna) de la última jugada
            - fantasmas, lista de (fila, columna, jugador, orden) con las
              jugadas que el algoritmo está analizando
            - columna_resaltada, columna bajo el ratón (turno del humano)
            - jugador_turno, jugador al que le toca (color de la ficha
              que se muestra sobre la columna resaltada)
            - etiquetas, diccionario {columna: (texto, color)} que se
              escribe encima de cada columna (valor de cada jugada)
            - columna_elegida, columna de la jugada elegida por el agente
        """
        fondo = self.rect.inflate(0, 0)
        pygame.draw.rect(sup, tema.HUECO, fondo, border_radius=14)
        # Columna elegida por el agente
        if columna_elegida is not None:
            r = pygame.Rect(self.x + columna_elegida * self.celda,
                            self.y - 30, self.celda, 26)
            pygame.draw.rect(sup, (20, 83, 45), r, border_radius=6)
        # Fichas ya jugadas
        for f in range(FILAS):
            for c in range(COLUMNAS):
                valor = int(estado[f, c])
                if valor != 0:
                    disco = self._disco(tema.COLOR_JUGADOR[valor])
                    sup.blit(disco, disco.get_rect(center=self.centro(f, c)))
        # Fichas fantasma (línea analizada por la búsqueda)
        if fantasmas:
            for f, c, jugador, orden in fantasmas:
                disco = self._disco(tema.COLOR_JUGADOR[jugador], 105)
                centro = self.centro(f, c)
                sup.blit(disco, disco.get_rect(center=centro))
                tema.texto(sup, str(orden), centro, 15, tema.BLANCO, True,
                           'center')
        # Ficha que está cayendo (se dibuja detrás de la cara frontal)
        if self.caida is not None:
            disco = self._disco(tema.COLOR_JUGADOR[self.caida['jugador']])
            cx = self.centro(0, self.caida['columna'])[0]
            recorte = sup.get_clip()
            sup.set_clip(self.rect)
            sup.blit(disco, disco.get_rect(center=(cx, int(self.caida['y']))))
            sup.set_clip(recorte)
        # Cara frontal con agujeros
        sup.blit(self._frente, self.rect)
        # Marca de la última jugada
        if ultima is not None:
            pygame.draw.circle(sup, tema.BLANCO, self.centro(*ultima), 5)
        # Línea ganadora
        if linea:
            for f, c in linea:
                pygame.draw.circle(sup, tema.VERDE, self.centro(f, c),
                                   self.radio + 2, 5)
            pygame.draw.line(sup, tema.VERDE, self.centro(*linea[0]),
                             self.centro(*linea[-1]), 5)
        # Turno del humano: se muestra dónde caería la ficha en la columna
        # sobre la que está el ratón
        if columna_resaltada is not None and jugador_turno is not None:
            vacias = int((estado[:, columna_resaltada] == 0).sum())
            if vacias > 0:
                disco = self._disco(tema.COLOR_JUGADOR[jugador_turno], 130)
                centro = self.centro(vacias - 1, columna_resaltada)
                sup.blit(disco, disco.get_rect(center=centro))
                r = pygame.Rect(self.x + columna_resaltada * self.celda + 4,
                                self.y - 8, self.celda - 8, 5)
                pygame.draw.rect(sup, tema.COLOR_JUGADOR[jugador_turno], r,
                                 border_radius=2)
        # Valor de cada columna
        if etiquetas:
            for c, (cadena, color) in etiquetas.items():
                cx = self.centro(0, c)[0]
                tema.texto(sup, cadena, (cx, self.y - 17), 11, color,
                           ancla='center')
        # Números de columna
        if numeros:
            for c in range(COLUMNAS):
                cx = self.centro(0, c)[0]
                tema.texto(sup, str(c), (cx, self.rect.bottom + 11), 12,
                           tema.TEXTO_SUAVE, ancla='center')


def dibujar_tablero_mini(sup, x, y, estado, celda=20):
    """Dibuja un tablero pequeño sin animaciones (vista de la instancia)."""
    rect = pygame.Rect(x, y, COLUMNAS * celda, FILAS * celda)
    pygame.draw.rect(sup, tema.TABLERO, rect, border_radius=6)
    radio = int(celda * 0.38)
    for f in range(FILAS):
        for c in range(COLUMNAS):
            valor = int(estado[f, c])
            color = tema.HUECO if valor == 0 else tema.COLOR_JUGADOR[valor]
            centro = (x + c * celda + celda // 2, y + f * celda + celda // 2)
            pygame.draw.circle(sup, color, centro, radio)
    return rect
