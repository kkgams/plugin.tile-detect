package tilemap

// ExtendLayers creates new layers with padding on all sides.
// Padded areas are filled with 0 (empty tiles).
// Original data is offset by (padLeft, padTop).
func ExtendLayers(layers []TileLayer, padLeft, padTop, padRight, padBottom int) []TileLayer {
	if len(layers) == 0 {
		return layers
	}

	extended := make([]TileLayer, len(layers))

	for i, layer := range layers {
		originalWidth := layer.Width
		originalHeight := layer.Height()

		newWidth := originalWidth + padLeft + padRight
		newHeight := originalHeight + padTop + padBottom

		// Create new layer with extended dimensions
		newData := make([]uint32, newWidth*newHeight)

		// Copy original data to the center (offset by padding)
		for y := 0; y < originalHeight; y++ {
			for x := 0; x < originalWidth; x++ {
				srcIdx := y*originalWidth + x
				dstIdx := (y+padTop)*newWidth + (x + padLeft)
				newData[dstIdx] = layer.Data[srcIdx]
			}
		}

		// Copy layer properties
		newProps := make(map[string]string)
		for k, v := range layer.Props {
			newProps[k] = v
		}

		extended[i] = TileLayer{
			Width: newWidth,
			Data:  newData,
			Props: newProps,
		}
	}

	return extended
}

// CropLayers removes padding from layers, returning them to specified size.
// Extracts a rectangular region starting at (cropLeft, cropTop) with dimensions (newWidth, newHeight).
func CropLayers(layers []TileLayer, cropLeft, cropTop, newWidth, newHeight int) []TileLayer {
	if len(layers) == 0 {
		return layers
	}

	cropped := make([]TileLayer, len(layers))

	for i, layer := range layers {
		extendedWidth := layer.Width
		extendedHeight := layer.Height()

		// Validate crop region
		if cropLeft < 0 || cropTop < 0 {
			// Return empty layer if invalid crop parameters
			cropped[i] = TileLayer{
				Width: newWidth,
				Data:  make([]uint32, newWidth*newHeight),
				Props: layer.Props,
			}
			continue
		}

		if cropLeft+newWidth > extendedWidth || cropTop+newHeight > extendedHeight {
			// Return empty layer if crop region exceeds bounds
			cropped[i] = TileLayer{
				Width: newWidth,
				Data:  make([]uint32, newWidth*newHeight),
				Props: layer.Props,
			}
			continue
		}

		// Create new layer with cropped dimensions
		newData := make([]uint32, newWidth*newHeight)

		// Copy cropped region
		for y := 0; y < newHeight; y++ {
			for x := 0; x < newWidth; x++ {
				srcIdx := (y+cropTop)*extendedWidth + (x + cropLeft)
				dstIdx := y*newWidth + x
				newData[dstIdx] = layer.Data[srcIdx]
			}
		}

		// Copy layer properties
		newProps := make(map[string]string)
		for k, v := range layer.Props {
			newProps[k] = v
		}

		cropped[i] = TileLayer{
			Width: newWidth,
			Data:  newData,
			Props: newProps,
		}
	}

	return cropped
}
