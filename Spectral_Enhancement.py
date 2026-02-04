import os
from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
from qgis.core import (
    QgsProcessingProvider, 
    QgsApplication,
    QgsRasterLayer
)
from qgis import processing
from .SpectralEnhancementAlgorithm import SpectralRasterEnhancementAlgorithm

class SpectralRasterEnhancementProvider(QgsProcessingProvider):
    def loadAlgorithms(self, *args):
        self.addAlgorithm(SpectralRasterEnhancementAlgorithm())

    def id(self):
        return 'spectral_raster_enhancement_provider'

    def name(self):
        return 'Spectral Raster Enhancement'

    def icon(self):
        plugin_dir = os.path.dirname(__file__)
        icon_path = os.path.join(plugin_dir, 'icon.png')
        return QIcon(icon_path)

class SpectralRasterEnhancement:
    def __init__(self, iface):
        self.iface = iface
        self.provider = None
        self.action = None
        
    def initProcessing(self):
        self.provider = SpectralRasterEnhancementProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    def initGui(self):
        self.initProcessing()
        
        plugin_dir = os.path.dirname(__file__)
        icon_path = os.path.join(plugin_dir, 'icon.png')
        icon = QIcon(icon_path)
        
        # Changement du texte du menu
        self.action = QAction(icon, "Spectral Raster Enhancement", self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        
        self.iface.addPluginToRasterMenu("Spectral Raster Enhancement", self.action)
        self.iface.addRasterToolBarIcon(self.action)

    def unload(self):
        QgsApplication.processingRegistry().removeProvider(self.provider)
        self.iface.removePluginRasterMenu("Spectral Raster Enhancement", self.action)
        self.iface.removeRasterToolBarIcon(self.action)
        del self.action

    def run(self):
        active_layer = self.iface.activeLayer()
        initial_params = {}
        
        if active_layer and isinstance(active_layer, QgsRasterLayer):
            initial_params['INPUT_RASTER'] = active_layer
            
        # Mise à jour de l'ID de l'algorithme pour correspondre au nouveau nom
        processing.execAlgorithmDialog("spectral_raster_enhancement_provider:spectralrasterenhancement", initial_params)