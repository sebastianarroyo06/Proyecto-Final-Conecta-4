"""
Entorno del juego 4 en raya (Conecta 4) clásico: 7 columnas x 6 filas.

La clase ``Conecta4`` sigue la definición formal de un juego competitivo
vista en el taller de Juegos del curso (clase ``Triqui`` del módulo
``juegos.py``), es decir, tiene exactamente los mismos componentes:

    * estado_inicial   -> tablero desde el que empieza el juego
    * player(s)        -> jugador al que le corresponde el turno
    * acciones(s)      -> jugadas legales en el estado s
    * resultado(s, a)  -> estado que resulta de jugar a en s
    * es_terminal(s)   -> True si el juego terminó en s
    * utilidad(s, j)   -> utilidad del estado terminal s para el jugador j

Representación del estado
-------------------------
Un estado es una matriz de numpy de 6 filas x 7 columnas con valores:

    0 = casilla vacía
    1 = ficha del jugador 1 (rojas, empieza la partida)
    2 = ficha del jugador 2 (amarillas)

La fila 0 es la fila SUPERIOR del tablero y la fila 5 es la INFERIOR,
de modo que las fichas "caen" hacia índices de fila más grandes.
El jugador en turno no se guarda aparte: se deduce de la paridad del
número de fichas (si hay un número par de fichas juega el jugador 1).
"""
import numpy as np

# ----------------------------------------------------------------------
# Constantes del juego
# ----------------------------------------------------------------------
FILAS = 6
COLUMNAS = 7
EN_LINEA = 4
VACIA = 0
JUGADOR_1 = 1
JUGADOR_2 = 2


def generar_ventanas(filas=FILAS, columnas=COLUMNAS, en_linea=EN_LINEA):
    """Genera todas las líneas ganadoras (ventanas) del tablero.

    Una ventana es un grupo de 4 casillas consecutivas en horizontal,
    vertical o diagonal. Cada casilla se identifica con su índice plano
    ``fila * columnas + columna`` para poder indexar el tablero aplanado.

    Output:
        - np.array de forma (69, 4) con los índices planos de cada ventana
          (24 horizontales + 21 verticales + 12 + 12 diagonales).
    """
    ventanas = []
    # Direcciones (cambio de fila, cambio de columna)
    direcciones = [(0, 1),   # horizontal
                   (1, 0),   # vertical
                   (1, 1),   # diagonal que baja hacia la derecha
                   (1, -1)]  # diagonal que baja hacia la izquierda
    for df, dc in direcciones:
        for f in range(filas):
            for c in range(columnas):
                # Casilla donde terminaría la ventana que empieza en (f, c)
                f_fin = f + (en_linea - 1) * df
                c_fin = c + (en_linea - 1) * dc
                if 0 <= f_fin < filas and 0 <= c_fin < columnas:
                    ventana = [(f + k * df) * columnas + (c + k * dc)
                               for k in range(en_linea)]
                    ventanas.append(ventana)
    return np.array(ventanas)


# Matriz 69 x 4 con todas las líneas ganadoras. Se calcula una sola vez
# y la usan tanto el entorno (para saber si alguien ganó) como la
# heurística h1 (ventanas de amenaza).
VENTANAS = generar_ventanas()


class Conecta4:
    """Juego 4 en raya clásico (7 columnas x 6 filas, reglas estándar)."""

    def __init__(self, estado_inicial=None):
        """
        Input:
            - estado_inicial (opcional), matriz 6x7 con una posición legal
              desde la cual empieza el juego (editor de instancias).
              Si no se da, se empieza con el tablero vacío.
        """
        self.filas = FILAS
        self.columnas = COLUMNAS
        if estado_inicial is None:
            self.estado_inicial = np.zeros((FILAS, COLUMNAS), dtype=np.int8)
        else:
            self.estado_inicial = np.array(estado_inicial, dtype=np.int8)
        # Memoria para no recalcular el ganador de un mismo tablero
        self._cache_ganador = {}

    # ------------------------------------------------------------------
    # Definición formal del juego (misma interfaz del taller de Juegos)
    # ------------------------------------------------------------------
    def player(self, estado):
        """Devuelve el jugador al que le corresponde el turno.

        Input: estado, que es una np.array (6x7)
        Output: 1 si juega el jugador 1 (rojas), 2 si juega el jugador 2
        """
        num_fichas = np.count_nonzero(estado)
        if num_fichas % 2 == 0:
            return JUGADOR_1
        return JUGADOR_2

    def acciones(self, estado):
        """Devuelve la lista de columnas en las que se puede jugar.

        Una columna es una acción válida si su casilla superior (fila 0)
        está vacía. En un estado terminal no hay acciones.

        Input: estado, que es una np.array (6x7)
        Output: lista de enteros entre 0 y 6
        """
        if self.es_terminal(estado):
            return []
        return [c for c in range(COLUMNAS) if estado[0, c] == VACIA]

    def resultado(self, estado, accion):
        """Devuelve el tablero que resulta de soltar una ficha del jugador
        en turno en la columna dada. La ficha cae a la fila libre más baja.

        Input: estado, que es una np.array (6x7)
               accion, entero entre 0 y 6 (columna)
        Output: estado, que es una np.array (6x7) nueva (no modifica s)
        """
        assert estado[0, accion] == VACIA, f'Columna {accion} llena.'
        s = estado.copy()
        # La fila libre más baja es (número de casillas vacías) - 1
        fila = np.count_nonzero(estado[:, accion] == VACIA) - 1
        s[fila, accion] = self.player(estado)
        return s

    def es_terminal(self, estado):
        """Devuelve True/False dependiendo de si el juego se acabó:
        alguien hizo cuatro en línea o el tablero está lleno.

        Input: estado, que es una np.array (6x7)
        Output: True/False
        """
        if self.ganador(estado) != 0:
            return True
        return np.count_nonzero(estado) == FILAS * COLUMNAS

    def utilidad(self, estado, jugador):
        """Devuelve la utilidad del estado terminal para el jugador dado.

        La utilidad premia ganar rápido y perder lo más tarde posible:

            +(43 - n)  si gana ``jugador``
            -(43 - n)  si pierde ``jugador``
             0         si hay empate

        donde n es el número de fichas en el tablero. Es un juego de suma
        cero: utilidad(s, 1) == -utilidad(s, 2).

        Input: estado, que es una np.array (6x7)
               jugador, 1 o 2
        Output: utilidad (entero), o None si el estado no es terminal
        """
        ganador = self.ganador(estado)
        num_fichas = int(np.count_nonzero(estado))
        if ganador == 0:
            if num_fichas == FILAS * COLUMNAS:
                return 0        # Empate: tablero lleno sin ganador
            return None         # El juego no ha terminado
        valor = FILAS * COLUMNAS + 1 - num_fichas
        if ganador == jugador:
            return valor
        return -valor

    # ------------------------------------------------------------------
    # Métodos auxiliares del entorno
    # ------------------------------------------------------------------
    def ganador(self, estado):
        """Devuelve 1 o 2 si ese jugador tiene cuatro en línea, 0 si nadie.

        Se revisan las 69 ventanas a la vez: ``valores`` es una matriz
        69 x 4 con el contenido de cada ventana; hay ganador si alguna
        fila de esa matriz tiene sus 4 casillas iguales a 1 (o a 2).
        """
        llave = estado.tobytes()
        if llave in self._cache_ganador:
            return self._cache_ganador[llave]
        valores = estado.ravel()[VENTANAS]
        ganador = 0
        for jugador in (JUGADOR_1, JUGADOR_2):
            if np.any(np.all(valores == jugador, axis=1)):
                ganador = jugador
                break
        if len(self._cache_ganador) > 500000:   # Evita que crezca sin límite
            self._cache_ganador.clear()
        self._cache_ganador[llave] = ganador
        return ganador

    def linea_ganadora(self, estado):
        """Devuelve la lista de casillas (fila, columna) del cuatro en
        línea, o una lista vacía si no hay ganador. La usa la interfaz
        gráfica para resaltar la línea."""
        valores = estado.ravel()[VENTANAS]
        for jugador in (JUGADOR_1, JUGADOR_2):
            completas = np.all(valores == jugador, axis=1)
            if np.any(completas):
                indices = VENTANAS[np.argmax(completas)]
                return [(int(i) // COLUMNAS, int(i) % COLUMNAS)
                        for i in indices]
        return []

    def otro_jugador(self, jugador):
        """Devuelve el rival del jugador dado."""
        return JUGADOR_2 if jugador == JUGADOR_1 else JUGADOR_1

    def give_result(self, estado):
        """Devuelve un mensaje con el resultado del juego."""
        if not self.es_terminal(estado):
            return 'El juego no ha terminado.'
        ganador = self.ganador(estado)
        if ganador == 0:
            return 'Juego terminado. ¡Empate!'
        return f'Juego terminado. ¡Gana el jugador {ganador}!'

    # ------------------------------------------------------------------
    # Generador / editor de instancias
    # ------------------------------------------------------------------
    def desde_jugadas(self, jugadas):
        """Construye un estado jugando una secuencia de columnas desde el
        tablero vacío. Como cada jugada es legal, el estado obtenido
        siempre es una posición alcanzable en una partida real.

        Input: jugadas, lista de columnas, p.ej. [3, 3, 2, 4]
        Output: estado, que es una np.array (6x7)
        """
        estado = np.zeros((FILAS, COLUMNAS), dtype=np.int8)
        for columna in jugadas:
            assert not self.es_terminal(estado), \
                'La secuencia continúa después de terminado el juego.'
            estado = self.resultado(estado, columna)
        return estado

    def jugadas_aleatorias(self, num_fichas, rng):
        """Genera una secuencia aleatoria de jugadas legales que NO termina
        el juego. Sirve para crear instancias de prueba reproducibles.

        Input: num_fichas, cantidad de fichas que tendrá el tablero
               rng, generador ``random.Random`` (con semilla)
        Output: lista de columnas
        """
        while True:
            estado = np.zeros((FILAS, COLUMNAS), dtype=np.int8)
            jugadas = []
            for _ in range(num_fichas):
                opciones = self.acciones(estado)
                if not opciones:
                    break
                columna = rng.choice(opciones)
                estado = self.resultado(estado, columna)
                jugadas.append(columna)
            if len(jugadas) == num_fichas and not self.es_terminal(estado):
                return jugadas

    def es_legal(self, estado):
        """Verifica que una matriz sea una posición válida del juego.

        Output: (True, '') si es válida; (False, motivo) en caso contrario
        """
        estado = np.array(estado)
        if estado.shape != (FILAS, COLUMNAS):
            return False, 'El tablero debe ser de 6 filas x 7 columnas.'
        if not np.isin(estado, (0, 1, 2)).all():
            return False, 'Solo se permiten los valores 0, 1 y 2.'
        # Gravedad: no puede haber una casilla vacía debajo de una ficha
        for c in range(COLUMNAS):
            columna = estado[:, c]
            ocupadas = np.nonzero(columna)[0]
            if len(ocupadas) > 0 and np.any(columna[ocupadas[0]:] == VACIA):
                return False, f'Hay fichas flotando en la columna {c}.'
        # Turnos: el jugador 1 tiene las mismas fichas que el 2 o una más
        n1 = np.count_nonzero(estado == JUGADOR_1)
        n2 = np.count_nonzero(estado == JUGADOR_2)
        if n1 - n2 not in (0, 1):
            return False, 'La cantidad de fichas no respeta los turnos.'
        # Solo puede haber ganado el último jugador que movió
        valores = estado.ravel()[VENTANAS]
        gana_1 = bool(np.any(np.all(valores == JUGADOR_1, axis=1)))
        gana_2 = bool(np.any(np.all(valores == JUGADOR_2, axis=1)))
        if gana_1 and gana_2:
            return False, 'Los dos jugadores tienen cuatro en línea.'
        if gana_1 and n1 != n2 + 1:
            return False, 'El jugador 1 ganó pero se siguió jugando.'
        if gana_2 and n1 != n2:
            return False, 'El jugador 2 ganó pero se siguió jugando.'
        return True, ''

    # ------------------------------------------------------------------
    # Visualización
    # ------------------------------------------------------------------
    def a_texto(self, estado):
        """Devuelve el tablero como texto ('.' vacía, 'X' jugador 1,
        'O' jugador 2) con los números de columna debajo."""
        simbolos = {0: '.', 1: 'X', 2: 'O'}
        filas = [' '.join(simbolos[int(v)] for v in fila) for fila in estado]
        filas.append(' '.join(str(c) for c in range(COLUMNAS)))
        return '\n'.join(filas)

    def render(self, estado, ax=None, titulo=None):
        """Dibuja el tablero correspondiente al estado con matplotlib
        (igual que el método render de la clase Triqui del curso).

        Input: estado, que es una np.array (6x7)
               ax (opcional), eje de matplotlib donde dibujar
               titulo (opcional), texto que se pone encima del tablero
        """
        import matplotlib.pyplot as plt
        import matplotlib.patches as patches

        mostrar = ax is None
        if ax is None:
            fig, ax = plt.subplots(figsize=(4.2, 3.6))
        # Borde del tablero
        ax.add_patch(patches.Rectangle((0, 0), COLUMNAS, FILAS,
                                       facecolor='#1d4ed8',
                                       edgecolor='black', linewidth=2))
        colores = {0: 'white', 1: '#ef4444', 2: '#facc15'}
        linea = self.linea_ganadora(estado)
        for f in range(FILAS):
            for c in range(COLUMNAS):
                # La fila 0 es la superior, por eso se invierte el eje y
                centro = (c + 0.5, FILAS - f - 0.5)
                borde = 'lime' if (f, c) in linea else 'black'
                ancho = 3 if (f, c) in linea else 1
                color = colores[int(estado[f, c])]
                ax.add_patch(patches.Circle(centro, 0.4, facecolor=color,
                                            edgecolor=borde, linewidth=ancho))
        for c in range(COLUMNAS):
            ax.text(c + 0.5, -0.35, str(c), ha='center', va='center')
        ax.set_xlim(-0.1, COLUMNAS + 0.1)
        ax.set_ylim(-0.7, FILAS + 0.1)
        ax.set_aspect('equal')
        ax.axis('off')
        if titulo is not None:
            ax.set_title(titulo, fontsize=10)
        if mostrar:
            plt.show()
