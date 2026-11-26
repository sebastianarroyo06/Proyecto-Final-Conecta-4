"""
Métricas y traza de la búsqueda.

    * ``Metricas`` guarda los números con los que se comparan los
      algoritmos (tiempo, nodos generados, nodos expandidos, memoria...).
    * ``Traza`` guarda, paso a paso, lo que hizo el algoritmo en los
      primeros niveles del árbol. La interfaz gráfica reproduce esa
      traza para animar el proceso de búsqueda (avanzar, pausar y
      retroceder).
"""
from dataclasses import dataclass, field, asdict


@dataclass
class Metricas:
    """Métricas de UNA decisión (una jugada) de un agente.

    Definiciones usadas en todo el proyecto:
        - nodo generado: estado creado con ``juego.resultado(s, a)``.
        - nodo expandido: nodo al que se le generaron sus sucesores.
        - memoria_max: cantidad máxima de nodos guardados al mismo tiempo.
          En minimax y alfa-beta es el tamaño de la pila de la búsqueda
          en profundidad; en MCTS es el tamaño del árbol construido.
    """
    algoritmo: str = ''
    tiempo: float = 0.0             # Segundos que tardó la decisión
    nodos_generados: int = 0
    nodos_expandidos: int = 0
    memoria_max: int = 0
    profundidad_max: int = 0        # Nivel más profundo alcanzado
    podas: int = 0                  # Cortes alfa-beta realizados
    evaluaciones: int = 0           # Hojas no terminales evaluadas
    terminales: int = 0             # Estados terminales alcanzados
    simulaciones: int = 0           # Partidas simuladas (solo MCTS)
    valor: float = 0.0              # Valor de la jugada elegida
    accion: int = -1                # Columna elegida
    valores_acciones: dict = field(default_factory=dict)

    def como_dict(self):
        """Devuelve las métricas como diccionario (para tablas y CSV)."""
        datos = asdict(self)
        datos.pop('valores_acciones')
        return datos


class Traza:
    """Registro paso a paso de la búsqueda de una jugada.

    Cada evento es un diccionario con, al menos:
        - 'tipo': qué pasó ('entra', 'hoja', 'sale', 'poda', 'iteracion')
        - 'camino': tupla de columnas desde la raíz hasta el nodo
        - 'gen', 'exp', 'podas': contadores en ese instante

    Solo se registran los nodos hasta ``prof_traza`` niveles debajo de la
    raíz, para que la traza sea corta aunque la búsqueda sea profunda.
    Los contadores, en cambio, sí cuentan TODOS los nodos.
    """

    def __init__(self, algoritmo, estado_raiz, jugador, prof_traza=3):
        self.algoritmo = algoritmo
        self.estado_raiz = estado_raiz
        self.jugador = jugador          # Jugador MAX (el que decide)
        self.prof_traza = prof_traza
        self.eventos = []

    def registrar(self, tipo, camino, metricas, **datos):
        """Agrega un evento a la traza junto con los contadores actuales."""
        evento = {
            'tipo': tipo,
            'camino': tuple(camino),
            'gen': metricas.nodos_generados,
            'exp': metricas.nodos_expandidos,
            'podas': metricas.podas,
            'prof': metricas.profundidad_max,
        }
        evento.update(datos)
        self.eventos.append(evento)

    def __len__(self):
        return len(self.eventos)
