package tilemap

import (
	"testing"
)

func TestFindLayer(t *testing.T) {
	// Create test tilemap with multiple layers
	tm := NewTileMap()

	// Layer 0: walls with collision metadata
	layer0 := NewTileLayer(3, 3)
	layer0.Props["name"] = "walls"
	layer0.Props["collision"] = "solid"
	layer0.Props["type"] = "foreground"
	tm.Layers = append(tm.Layers, *layer0)

	// Layer 1: background layer
	layer1 := NewTileLayer(3, 3)
	layer1.Props["name"] = "background"
	layer1.Props["type"] = "background"
	tm.Layers = append(tm.Layers, *layer1)

	// Layer 2: decorative layer
	layer2 := NewTileLayer(3, 3)
	layer2.Props["decorative"] = "true"
	layer2.Props["type"] = "decoration"
	tm.Layers = append(tm.Layers, *layer2)

	tests := []struct {
		name     string
		selector string
		wantIdx  int // Expected layer index, -1 for no match
	}{
		{"wildcard selector", "*", 0},
		{"index selector 0", "#0", 0},
		{"index selector 1", "#1", 1},
		{"index selector 2", "#2", 2},
		{"index selector out of bounds", "#5", -1},
		{"exact attribute match", `[name="walls"]`, 0},
		{"exact attribute match 2", `[name="background"]`, 1},
		{"attribute exists", `[decorative]`, 2},
		{"attribute exists 2", `[collision]`, 0},
		{"negated attribute", `[type!="background"]`, 0}, // Should match first non-background
		{"no match attribute", `[missing="value"]`, -1},
		{"no match negated", `[name!="nonexistent"]`, 0}, // Should match first layer
		{"invalid selector", "invalid", -1},
		{"empty selector", "", -1},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := FindLayer(tm, tt.selector)

			if tt.wantIdx == -1 {
				if result != nil {
					t.Errorf("FindLayer(%q) = layer, want nil", tt.selector)
				}
				return
			}

			if result == nil {
				t.Errorf("FindLayer(%q) = nil, want layer %d", tt.selector, tt.wantIdx)
				return
			}

			// Check if we got the expected layer by comparing pointer
			expectedLayer := &tm.Layers[tt.wantIdx]
			if result != expectedLayer {
				t.Errorf("FindLayer(%q) = wrong layer, want layer %d", tt.selector, tt.wantIdx)
			}
		})
	}
}

func TestFindLayers(t *testing.T) {
	// Create test tilemap
	tm := NewTileMap()

	// Add multiple layers with same type
	for i := 0; i < 3; i++ {
		layer := NewTileLayer(2, 2)
		layer.Props["type"] = "wall"
		if i == 1 {
			layer.Props["special"] = "true"
		}
		tm.Layers = append(tm.Layers, *layer)
	}

	// Add one different layer
	bgLayer := NewTileLayer(2, 2)
	bgLayer.Props["type"] = "background"
	tm.Layers = append(tm.Layers, *bgLayer)

	tests := []struct {
		name      string
		selector  string
		wantCount int
	}{
		{"wildcard all layers", "*", 4},
		{"type wall layers", `[type="wall"]`, 3},
		{"special attribute", `[special]`, 1},
		{"background type", `[type="background"]`, 1},
		{"nonexistent attribute", `[missing]`, 0},
		{"index selector", "#0", 1},
		{"negated type", `[type!="background"]`, 3},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := FindLayers(tm, tt.selector)
			if len(result) != tt.wantCount {
				t.Errorf("FindLayers(%q) = %d layers, want %d", tt.selector, len(result), tt.wantCount)
			}
		})
	}
}

func TestFindLayerEdgeCases(t *testing.T) {
	// Test with nil tilemap
	if result := FindLayer(nil, "#0"); result != nil {
		t.Error("FindLayer with nil tilemap should return nil")
	}

	// Test with empty tilemap
	emptyTm := NewTileMap()
	if result := FindLayer(emptyTm, "#0"); result != nil {
		t.Error("FindLayer with empty tilemap should return nil")
	}

	// Test with layer without metadata
	tm := NewTileMap()
	layer := NewTileLayer(2, 2)
	layer.Props = nil // Explicitly nil metadata
	tm.Layers = append(tm.Layers, *layer)

	if result := FindLayer(tm, "[name]"); result != nil {
		t.Error("FindLayer should not match layer without metadata")
	}

	if result := FindLayer(tm, "#0"); result == nil {
		t.Error("FindLayer should match by index even without metadata")
	}
}

func TestAttributeMatching(t *testing.T) {
	layer := NewTileLayer(2, 2)
	layer.Props["key1"] = "value1"
	layer.Props["key2"] = "value2"
	layer.Props["empty"] = ""

	tests := []struct {
		name     string
		attrExpr string
		want     bool
	}{
		{"exact match", `key1="value1"`, true},
		{"exact match with quotes", `key1="value1"`, true},
		{"exact match no quotes", `key1=value1`, true},
		{"exact match fail", `key1="wrong"`, false},
		{"key exists", `key1`, true},
		{"key missing", `missing`, false},
		{"negated match true", `key1!="wrong"`, true},
		{"negated match false", `key1!="value1"`, false},
		{"negated missing key", `missing!="anything"`, true},
		{"empty value exact", `empty=""`, true},
		{"empty value exists", `empty`, true},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := matchesAttribute(layer, tt.attrExpr)
			if result != tt.want {
				t.Errorf("matchesAttribute(%q) = %v, want %v", tt.attrExpr, result, tt.want)
			}
		})
	}
}

func TestHelperFunctions(t *testing.T) {
	tm := NewTileMap()
	layer := NewTileLayer(2, 2)
	layer.Props["type"] = "wall"
	tm.Layers = append(tm.Layers, *layer)

	// Test HasLayerWithSelector
	if !HasLayerWithSelector(tm, "[type=\"wall\"]") {
		t.Error("HasLayerWithSelector should return true for existing layer")
	}

	if HasLayerWithSelector(tm, "[missing]") {
		t.Error("HasLayerWithSelector should return false for non-existing layer")
	}

	// Test CountLayersWithSelector
	if count := CountLayersWithSelector(tm, "#0"); count != 1 {
		t.Errorf("CountLayersWithSelector(\"#0\") = %d, want 1", count)
	}

	if count := CountLayersWithSelector(tm, "[missing]"); count != 0 {
		t.Errorf("CountLayersWithSelector(\"[missing]\") = %d, want 0", count)
	}
}
