"""
Tema visual de la interfaz: colores, tipografías y funciones para
escribir texto en pantalla.
"""
import os

import pygame

# ----------------------------------------------------------------------
# Tamaño de la ventana
# ----------------------------------------------------------------------
ANCHO = 1280
ALTO = 720
FPS = 60

# ----------------------------------------------------------------------
# Colores (R, G, B)
# ----------------------------------------------------------------------
FONDO = (15, 23, 42)
PANEL = (30, 41, 59)
PANEL_CLARO = (51, 65, 85)
BORDE = (71, 85, 105)
TEXTO = (226, 232, 240)
TEXTO_SUAVE = (148, 163, 184)
ACENTO = (56, 189, 248)
ACENTO_OSCURO = (3, 105, 161)
BLANCO = (255, 255, 255)
NEGRO = (0, 0, 0)

# Tablero y fichas
TABLERO = (37, 99, 235)
TABLERO_OSCURO = (30, 64, 175)
HUECO = (15, 23, 42)
ROJO = (239, 68, 68)
AMARILLO = (250, 204, 21)
COLOR_JUGADOR = {1: ROJO, 2: AMARILLO}
NOMBRE_COLOR = {1: 'rojas', 2: 'amarillas'}

# Estados de los nodos en la animación de la búsqueda
NODO_PENDIENTE = (100, 116, 139)    # Frontera: generado, sin explorar
NODO_ACTUAL = (245, 158, 11)        # Nodo que se está expandiendo
NODO_EVALUADO = (56, 189, 248)      # Nodo ya explorado, con su valor
NODO_PODADO = (239, 68, 68)         # Rama cortada por alfa-beta
NODO_MEJOR = (34, 197, 94)          # Mejor jugada / variante principal
VERDE = (34, 197, 94)
NARANJA = (245, 158, 11)

# ----------------------------------------------------------------------
# Tipografías
# ----------------------------------------------------------------------
_fuentes = {}


def _ruta_fuente(negrita):
    """Busca la fuente DejaVu Sans que viene con matplotlib. Si no la
    encuentra se usa la fuente por defecto de pygame."""
    try:
        import matplotlib
        nombre = 'DejaVuSans-Bold.ttf' if negrita else 'DejaVuSans.ttf'
        ruta = os.path.join(matplotlib.get_data_path(), 'fonts', 'ttf',
                            nombre)
        if os.path.exists(ruta):
            return ruta
    except ImportError:
        pass
    return None


def fuente(tam=14, negrita=False):
    """Devuelve (y guarda en memoria) la fuente del tamaño pedido."""
    llave = (tam, negrita)
    if llave not in _fuentes:
        ruta = _ruta_fuente(negrita)
        if ruta is None:
            _fuentes[llave] = pygame.font.Font(None, int(tam * 1.4))
        else:
            _fuentes[llave] = pygame.font.Font(ruta, tam)
    return _fuentes[llave]


def texto(sup, cadena, pos, tam=14, color=TEXTO, negrita=False,
          ancla='topleft'):
    """Escribe un texto en la superficie.

    Input:
        - sup, superficie de pygame
        - cadena, texto a escribir
        - pos, posición (x, y) del punto de anclaje
        - ancla, punto del texto que se ubica en pos: 'topleft', 'center',
          'midleft', 'midright', 'midtop', 'topright', ...
    Output:
        - rectángulo ocupado por el texto
    """
    imagen = fuente(tam, negrita).render(str(cadena), True, color)
    rect = imagen.get_rect(**{ancla: pos})
    sup.blit(imagen, rect)
    return rect


def ancho_texto(cadena, tam=14, negrita=False):
    """Ancho en píxeles que ocupa un texto."""
    return fuente(tam, negrita).size(str(cadena))[0]


def texto_ajustado(sup, cadena, rect, tam=13, color=TEXTO, interlinea=4):
    """Escribe un texto largo partiéndolo en líneas que quepan en rect.
    Devuelve la coordenada y donde terminó de escribir."""
    f = fuente(tam)
    y = rect.y
    for parrafo in str(cadena).split('\n'):
        linea = ''
        for palabra in parrafo.split(' '):
            prueba = palabra if linea == '' else linea + ' ' + palabra
            if f.size(prueba)[0] <= rect.width:
                linea = prueba
            else:
                sup.blit(f.render(linea, True, color), (rect.x, y))
                y += f.get_height() + interlinea
                linea = palabra
        sup.blit(f.render(linea, True, color), (rect.x, y))
        y += f.get_height() + interlinea
    return y


def panel(sup, rect, titulo=None, color=PANEL):
    """Dibuja un panel con esquinas redondeadas y un título opcional."""
    pygame.draw.rect(sup, color, rect, border_radius=10)
    if titulo is not None:
        texto(sup, titulo, (rect.x + 12, rect.y + 9), 13, TEXTO_SUAVE,
              negrita=True)


def formato_numero(valor):
    """Escribe un entero con separador de miles (1.234.567)."""
    return f'{int(round(valor)):,}'.replace(',', '.')


def formato_tiempo(segundos):
    """Escribe un tiempo en milisegundos si es corto o en segundos."""
    if segundos < 0.1:
        return f'{segundos * 1000:.1f} ms'
    return f'{segundos:.2f} s'


def formato_valor(valor):
    """Escribe el valor de un nodo: enteros para utilidades reales y tres
    decimales para estimaciones de la heurística."""
    if valor is None:
        return '-'
    if valor == float('inf'):
        return '+∞'
    if valor == float('-inf'):
        return '-∞'
    if float(valor).is_integer():
        return f'{int(valor):+d}' if valor != 0 else '0'
    return f'{valor:+.3f}'
