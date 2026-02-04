# Histogram_Raster_Enhancement
This algorithm applies radiometric enhancements to raster layers. It supports both single-band (grayscale) and multi-band (multispectral/RGB) images to improve visual interpretation and contrast
<h3>🛠️ Methods</h3>

Note for Multi-band images: Enhancements are calculated and applied independently to each band to maximize contrast per channel

<h4>1. Linear Stretch (Percentile)</h4>
<p>Expands the range of pixel values to utilize the full dynamic range (0-255) by excluding outliers.</p>

<h4>2. Equalization</h4>
<p>Redistributes pixel intensities so that they are as uniform as possible (histogram flattening).</p>

<h4>3. Gamma Correction</h4>
<p>Non-linear operation to adjust mid-tones brightness.</p>
<ul>
