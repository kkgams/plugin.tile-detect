package tilemap

// TileMap represents the root map structure.
// It contains layers of tiles and metadata for map-wide properties.
type TileMap struct {
	Layers []TileLayer       `json:"layers"`          // Array of tile layers
	Props  map[string]string `json:"props,omitempty"` // Map metadata (tilesets, dimensions, version, etc.)
}

// TileLayer represents a single layer of tiles.
// Each layer has a width, flat data array, and metadata for layer-specific properties.
type TileLayer struct {
	Width int               `json:"width"`           // Width in tiles
	Data  []uint32          `json:"data"`            // Flat array of tile indices (0 = empty, 1+ = tile ID)
	Props map[string]string `json:"props,omitempty"` // Layer metadata (name, tileset info, collision, etc.)
}

// Height returns the calculated height of the layer based on data length and width.
func (l *TileLayer) Height() int {
	if l.Width == 0 {
		return 0
	}
	return len(l.Data) / l.Width
}

// NewTileMap creates a new empty tile map.
func NewTileMap() *TileMap {
	return &TileMap{
		Layers: make([]TileLayer, 0),
		Props:  make(map[string]string),
	}
}

// NewTileLayer creates a new tile layer with the given width and height.
func NewTileLayer(width, height int) *TileLayer {
	return &TileLayer{
		Width: width,
		Data:  make([]uint32, width*height),
		Props: make(map[string]string),
	}
}
