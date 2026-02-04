import os
from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (QgsProcessing, 
                      QgsProcessingAlgorithm, 
                      QgsProcessingParameterRasterLayer,
                      QgsProcessingParameterEnum,
                      QgsProcessingParameterNumber,
                      QgsProcessingParameterRasterDestination,
                      QgsProcessingException)
from qgis.PyQt.QtGui import QIcon
import numpy as np
from osgeo import gdal

class SpectralRasterEnhancementAlgorithm(QgsProcessingAlgorithm):
    INPUT_RASTER = 'INPUT_RASTER'
    METHOD = 'METHOD'
    CUT_PERCENT = 'CUT_PERCENT' 
    GAMMA = 'GAMMA'             
    OUTPUT_RASTER = 'OUTPUT_RASTER'

    def tr(self, string):
        return QCoreApplication.translate('SpectralRasterEnhancement', string)

    def createInstance(self):
        return SpectralRasterEnhancementAlgorithm()

    def name(self):
        return 'spectralrasterenhancement'

    def displayName(self):
        return self.tr('Spectral Histogram Enhancement')

    def group(self):
        return self.tr('Spectral Raster Enhancement')

    def groupId(self):
        return 'spectralrasterenhancement'

    def shortHelpString(self) -> str:
        return self.tr("""
<h2>Spectral Raster Enhancement Tools</h2>
<p>This algorithm applies radiometric enhancements to raster layers. It supports both single-band (grayscale) and multi-band (multispectral/RGB) images.</p>

<h3>📁 Input</h3>
<ul>
  <li><b>Input Raster</b>: Select the raster layer. Works with any raster format supported by GDAL.</li>
</ul>

<h3>🛠️ Methods</h3>
<p><b>Note for Multi-band images:</b> Enhancements are calculated and applied independently to each band to maximize contrast per channel.</p>

<h4>1. Linear Stretch (Percentile)</h4>
<p>Expands the range of pixel values to utilize the full dynamic range (0-255).</p>
<ul>
  <li><b>Parameter - Cut Percentage (%)</b>: Determines how much of the extreme values (outliers) to ignore. Default: 2%.</li>
</ul>

<h4>2. Equalization</h4>
<p>Redistributes pixel intensities to flatten the histogram (CDF mapping).</p>
<ul>
  <li>Increases local contrast but may alter color balance in RGB composites.</li>
</ul>

<h4>3. Gamma Correction</h4>
<p>Non-linear operation to adjust mid-tones brightness.</p>
<ul>
  <li><b>Parameter - Gamma Value</b>: 
    <ul>
      <li>< 1.0: Brighter image.</li>
      <li>> 1.0: Darker image.</li>
    </ul>
  </li>
</ul>

<h3>💾 Output</h3>
<ul>
  <li><b>Enhanced Image</b>: A new GeoTIFF file (8-bit Byte) containing the enhanced data. Georeference and projection are preserved.</li>
</ul>
        """)

    def icon(self):
        plugin_dir = os.path.dirname(__file__)
        icon_path = os.path.join(plugin_dir, 'icon.png')
        return QIcon(icon_path)

    def initAlgorithm(self, config=None):
        self.methods = [self.tr('Linear Stretch (Percentile)'), 
                        self.tr('Equalization'), 
                        self.tr('Gamma Correction')]

        self.addParameter(
            QgsProcessingParameterRasterLayer(self.INPUT_RASTER, self.tr('Input Raster'))
        )
        self.addParameter(
            QgsProcessingParameterEnum(self.METHOD, self.tr('Method'), self.methods, defaultValue=0)
        )
        self.addParameter(
            QgsProcessingParameterNumber(self.CUT_PERCENT, self.tr('Cut Percentage (%)'), 
                                        type=QgsProcessingParameterNumber.Double, minValue=0.0, maxValue=50.0, defaultValue=2.0, optional=True)
        )
        self.addParameter(
            QgsProcessingParameterNumber(self.GAMMA, self.tr('Gamma Value'), 
                                        type=QgsProcessingParameterNumber.Double, minValue=0.1, maxValue=10.0, defaultValue=1.0, optional=True)
        )
        self.addParameter(
            QgsProcessingParameterRasterDestination(self.OUTPUT_RASTER, self.tr('Enhanced Image'))
        )

    def processAlgorithm(self, parameters, context, feedback):
        raster_layer = self.parameterAsRasterLayer(parameters, self.INPUT_RASTER, context)
        method_index = self.parameterAsInt(parameters, self.METHOD, context)
        cut_percent = self.parameterAsDouble(parameters, self.CUT_PERCENT, context)
        gamma = self.parameterAsDouble(parameters, self.GAMMA, context)
        output_path = self.parameterAsOutputLayer(parameters, self.OUTPUT_RASTER, context)

        if not raster_layer:
            raise QgsProcessingException(self.tr('Invalid layer'))

        raster_path = raster_layer.source()
        
        try:
            ds = gdal.Open(raster_path)
            band_count = ds.RasterCount
            
            if band_count == 0:
                raise QgsProcessingException("Raster has no bands")

            feedback.pushInfo(f"Processing {band_count} band(s) with method: {self.methods[method_index]}...")

            # Préparation du raster de sortie avec le même nombre de bandes
            driver = gdal.GetDriverByName('GTiff')
            cols, rows = ds.RasterXSize, ds.RasterYSize
            out_ds = driver.Create(output_path, cols, rows, band_count, gdal.GDT_Byte)
            out_ds.SetGeoTransform(ds.GetGeoTransform())
            out_ds.SetProjection(ds.GetProjection())

            # Boucle sur chaque bande
            for i in range(1, band_count + 1):
                if feedback.isCanceled():
                    break

                feedback.pushInfo(f"Processing Band {i}/{band_count}...")
                
                band = ds.GetRasterBand(i)
                data = band.ReadAsArray().astype(np.float64)
                
                nodata = band.GetNoDataValue()
                if nodata is not None:
                    mask = (data == nodata)
                else:
                    mask = np.zeros_like(data, dtype=bool)
                
                valid_data = data[~mask]
                
                if valid_data.size == 0:
                    feedback.pushWarning(f"Band {i} is empty or fully NoData. Skipping.")
                    continue

                output_data = np.zeros_like(data, dtype=np.uint8)

                if method_index == 0: # Linear Stretch
                    # Calcul des percentiles pour cette bande spécifique
                    p_min = np.percentile(valid_data, cut_percent)
                    p_max = np.percentile(valid_data, 100 - cut_percent)
                    
                    stretched = np.clip(valid_data, p_min, p_max)
                    stretched = ((stretched - p_min) / (p_max - p_min) * 255).astype(np.uint8)
                    output_data[~mask] = stretched

                elif method_index == 1: # Equalization
                    # Histogramme et CDF spécifiques à cette bande
                    hist, bins = np.histogram(valid_data.flatten(), bins=256, range=(valid_data.min(), valid_data.max()))
                    cdf = hist.cumsum()
                    cdf_min = cdf.min()
                    cdf_max = cdf.max()
                    
                    if cdf_max > cdf_min:
                        cdf = (cdf - cdf_min) * 255 / (cdf_max - cdf_min)
                    else:
                        cdf = np.zeros_like(cdf)
                    cdf = cdf.astype(np.uint8)
                    
                    bins_center = (bins[:-1] + bins[1:]) / 2
                    equalized = np.interp(valid_data.flatten(), bins_center, cdf).reshape(valid_data.shape).astype(np.uint8)
                    output_data[~mask] = equalized

                elif method_index == 2: # Gamma Correction
                    min_val = valid_data.min()
                    max_val = valid_data.max()
                    range_val = max_val - min_val
                    
                    if range_val == 0:
                        norm = np.zeros_like(valid_data)
                    else:
                        norm = (valid_data - min_val) / range_val
                    
                    gamma_corrected = np.power(norm, 1.0 / gamma)
                    output_data[~mask] = (gamma_corrected * 255).astype(np.uint8)

                output_data[mask] = 0

                # Écriture de la bande traitée
                out_band = out_ds.GetRasterBand(i)
                out_band.WriteArray(output_data)
                out_band.SetNoDataValue(0)
                # Libération de la mémoire pour la bande écrite
                out_band.FlushCache()
            
            # Fermeture propre des datasets
            out_ds = None
            ds = None
            feedback.pushInfo("✅ Complete")

        except Exception as e:
            feedback.reportError(f"Error: {str(e)}")
            import traceback
            feedback.pushInfo(traceback.format_exc())
            return {}

        return {self.OUTPUT_RASTER: output_path}