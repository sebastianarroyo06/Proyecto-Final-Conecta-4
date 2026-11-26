"""
Punto de entrada de la aplicación.

Ejecutar desde la carpeta del proyecto:

    python main.py
"""
from gui.app import Aplicacion


def main():
    aplicacion = Aplicacion()
    aplicacion.ejecutar()


if __name__ == '__main__':
    main()
