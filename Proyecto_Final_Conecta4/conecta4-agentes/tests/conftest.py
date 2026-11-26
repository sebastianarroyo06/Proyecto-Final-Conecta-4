"""Permite importar el paquete conecta4 al correr pytest desde la raíz."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
