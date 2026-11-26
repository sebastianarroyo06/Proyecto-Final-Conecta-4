"""Pantalla de ayuda: cómo usar la aplicación y qué significa cada cosa."""
import pygame

from gui import tema

SECCIONES = [
    ('El juego',
     '4 en raya clásico: tablero de 7 columnas x 6 filas. Los jugadores '
     'alternan turnos soltando una ficha en una columna; la ficha cae a '
     'la casilla libre más baja. Gana quien alinee cuatro fichas en '
     'horizontal, vertical o diagonal. Si el tablero se llena hay empate.'
     '\nEl jugador 1 (rojas) empieza. Las columnas se numeran de 0 a 6.'),
    ('Algoritmos',
     'Minimax (no informado): recorre el árbol de juego hasta una '
     'profundidad límite d usando solo la utilidad de los estados '
     'terminales.\n'
     'Alfa-beta (informado): minimax con poda y una función de '
     'evaluación en el límite de profundidad. h1 cuenta amenazas en las '
     '69 ventanas; h2 valora el control de las casillas centrales.\n'
     'MCTS: simula N partidas aleatorias por jugada y elige la columna '
     'más visitada (selección UCB1).'),
    ('Dificultad',
     'Fácil / Medio / Difícil cambian cuánto busca cada algoritmo:\n'
     'Minimax: d = 2 / 4 / 6.   Alfa-beta: d = 2 / 5 / 8.\n'
     'MCTS: N = 200 / 1000 / 5000 simulaciones.'),
    ('Pestaña Jugar',
     'Elige el modo y los jugadores y pulsa Iniciar. Controles: Inicio y '
     'Final saltan a los extremos de la partida; Jugada avanza o '
     'retrocede una jugada completa; Paso avanza o retrocede un paso de '
     'la búsqueda. El deslizador cambia la velocidad de la animación.\n'
     'En Humano vs Agente, haz clic en una columna para jugar.'),
    ('Animación de la búsqueda',
     'El árbol muestra los primeros niveles de la búsqueda. Cada nodo es '
     'un tablero y su número es la columna jugada.\n'
     'Gris: frontera (generado, sin explorar). Naranja: en expansión. '
     'Azul: evaluado, con su valor. Rojo con X: podado por alfa-beta. '
     'Verde: mejor línea encontrada.\n'
     'Sobre cada columna del tablero aparece el valor de esa jugada, y '
     'las fichas transparentes numeradas son la línea que se analiza.'),
    ('Estado interno y métricas',
     'Nodo generado: tablero creado al simular una jugada. Nodo '
     'expandido: nodo al que se le generaron sus sucesores. Frontera '
     'visible: nodos generados que faltan por explorar. α y β: mejor '
     'valor garantizado para MAX y para MIN. Memoria: máximo de nodos '
     'guardados al mismo tiempo (pila de la búsqueda o árbol de MCTS).\n'
     '¿Óptima?: compara la jugada con un solucionador exacto; solo se '
     'puede con pocas casillas vacías (si no, "n. d.").'),
    ('Pestaña Editor',
     'Define el estado inicial: juega fichas a mano, genera una posición '
     'aleatoria con una semilla o carga un ejemplo. Luego úsalo para '
     'jugar o para comparar.'),
    ('Pestaña Comparar',
     'Ejecuta los algoritmos sobre la misma instancia. "Comparar una '
     'jugada" muestra las métricas de una decisión; "Torneo" enfrenta a '
     'todos contra todos. Los resultados se exportan a CSV.'),
]


class PantallaAyuda:
    """Pantalla con las instrucciones de uso."""

    def __init__(self, app):
        self.app = app

    def al_entrar(self):
        pass

    def manejar_evento(self, evento):
        pass

    def actualizar(self, dt):
        pass

    def dibujar(self, sup):
        rect = pygame.Rect(12, 56, 1256, 652)
        tema.panel(sup, rect, 'AYUDA')
        columnas = [pygame.Rect(36, 92, 580, 600),
                    pygame.Rect(660, 92, 580, 600)]
        mitad = len(SECCIONES) // 2
        for zona, secciones in zip(columnas,
                                   (SECCIONES[:mitad], SECCIONES[mitad:])):
            y = zona.y
            for titulo, cuerpo in secciones:
                tema.texto(sup, titulo, (zona.x, y), 14, tema.ACENTO, True)
                y = tema.texto_ajustado(
                    sup, cuerpo, pygame.Rect(zona.x, y + 24, zona.width, 200),
                    12, tema.TEXTO, interlinea=5)
                y += 14
