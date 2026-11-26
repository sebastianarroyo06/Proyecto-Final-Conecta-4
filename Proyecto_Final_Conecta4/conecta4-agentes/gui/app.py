"""
Aplicación principal: crea la ventana, las pestañas y el ciclo de juego.

El ciclo de pygame hace tres cosas en cada cuadro:
    1. leer los eventos (ratón, teclado) y pasarlos a la pantalla activa,
    2. actualizar la lógica (animaciones, resultados de los agentes),
    3. dibujar la pantalla.
"""
import os

import pygame

from conecta4.juego import Conecta4
from gui import tema
from gui.pantalla_ayuda import PantallaAyuda
from gui.pantalla_comparar import PantallaComparar
from gui.pantalla_editor import PantallaEditor
from gui.pantalla_jugar import PantallaJugar
from gui.widgets import Boton

PESTANAS = [('jugar', 'Jugar'), ('editor', 'Editor'),
            ('comparar', 'Comparar'), ('ayuda', 'Ayuda')]


class Aplicacion:
    """Ventana principal con las cuatro pestañas."""

    def __init__(self, semilla=0):
        # Solo se inician la ventana y las fuentes (no hace falta sonido)
        pygame.display.init()
        pygame.font.init()
        pygame.display.set_caption('Conecta 4 · Agentes de búsqueda '
                                   'adversaria')
        # SCALED ajusta la ventana a pantallas pequeñas y RESIZABLE permite
        # cambiarle el tamaño; el contenido siempre se dibuja en 1280x720
        try:
            self.pantalla = pygame.display.set_mode(
                (tema.ANCHO, tema.ALTO), pygame.SCALED | pygame.RESIZABLE)
        except pygame.error:
            self.pantalla = pygame.display.set_mode((tema.ANCHO, tema.ALTO))
        self.reloj = pygame.time.Clock()
        self.carpeta = os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)))
        self.juego = Conecta4()
        # Instancia compartida por todas las pestañas: secuencia de
        # jugadas que define el estado inicial del entorno
        self.instancia = []
        self.semilla = semilla
        self.activa = 'jugar'
        self.corriendo = True
        self.botones = []
        for i, (nombre, etiqueta) in enumerate(PESTANAS):
            boton = Boton((tema.ANCHO - 448 + i * 110, 10, 102, 32),
                          etiqueta, lambda n=nombre: self.ir_a(n))
            boton.nombre = nombre
            self.botones.append(boton)
        self.pantallas = {}
        self.pantallas['jugar'] = PantallaJugar(self)
        self.pantallas['editor'] = PantallaEditor(self)
        self.pantallas['comparar'] = PantallaComparar(self)
        self.pantallas['ayuda'] = PantallaAyuda(self)

    def ir_a(self, nombre):
        """Cambia de pestaña."""
        self.activa = nombre
        pantalla = self.pantallas[nombre]
        if hasattr(pantalla, 'al_entrar'):
            pantalla.al_entrar()

    def manejar_eventos(self):
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                self.corriendo = False
                return
            consumido = False
            for boton in self.botones:
                if boton.manejar_evento(evento):
                    consumido = True
            if not consumido:
                self.pantallas[self.activa].manejar_evento(evento)

    def actualizar(self, dt):
        self.pantallas[self.activa].actualizar(dt)

    def dibujar(self):
        sup = self.pantalla
        sup.fill(tema.FONDO)
        # Barra superior
        pygame.draw.circle(sup, tema.ROJO, (28, 26), 9)
        pygame.draw.circle(sup, tema.AMARILLO, (44, 26), 9)
        tema.texto(sup, 'Conecta 4', (62, 26), 18, tema.TEXTO, True,
                   'midleft')
        tema.texto(sup, 'Agentes de búsqueda adversaria: minimax, '
                   'alfa-beta y MCTS', (172, 27), 12, tema.TEXTO_SUAVE,
                   ancla='midleft')
        for boton in self.botones:
            boton.activo = boton.nombre == self.activa
            boton.dibujar(sup)
        self.pantallas[self.activa].dibujar(sup)
        pygame.display.flip()

    def cuadro(self, dt):
        """Ejecuta un cuadro completo: eventos, actualización y dibujo."""
        self.manejar_eventos()
        self.actualizar(dt)
        self.dibujar()

    def ejecutar(self):
        """Ciclo principal de la aplicación."""
        while self.corriendo:
            dt = self.reloj.tick(tema.FPS) / 1000.0
            self.cuadro(min(dt, 0.05))
        self.pantallas['jugar'].sesion.cancelar()
        pygame.quit()
