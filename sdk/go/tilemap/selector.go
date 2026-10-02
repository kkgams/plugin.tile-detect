package tilemap

import (
	"strconv"
	"strings"
)

// FindLayer finds a layer in the tilemap using CSS-like selector syntax.
// Supports:
//   - Index selectors: "#0", "#1", "#2" (0-based layer index)
//   - Attribute selectors: "[key=\"value\"]", "[key]", "[key!=\"value\"]"
//   - Wildcard selector: "*" (first available layer)
//
// Returns the first matching layer or nil if no match found.
func FindLayer(tilemap *TileMap, selector string) *TileLayer {
	if tilemap == nil || len(tilemap.Layers) == 0 {
		return nil
	}

	selector = strings.TrimSpace(selector)

	switch {
	case selector == "*":
		// Wildcard: match first available layer
		return &tilemap.Layers[0]

	case strings.HasPrefix(selector, "#"):
		// Index selector: #0, #1, #2
		return findLayerByIndex(tilemap, selector)

	case strings.HasPrefix(selector, "[") && strings.HasSuffix(selector, "]"):
		// Attribute selector: [key="value"], [key], [key!="value"]
		attrExpr := selector[1 : len(selector)-1]
		return findLayerByAttribute(tilemap, attrExpr)

	default:
		// Invalid selector format
		return nil
	}
}

// FindLayers finds all layers in the tilemap matching the given selector.
// Returns empty slice if no matches found.
func FindLayers(tilemap *TileMap, selector string) []*TileLayer {
	if tilemap == nil || len(tilemap.Layers) == 0 {
		return nil
	}

	selector = strings.TrimSpace(selector)
	var matches []*TileLayer

	switch {
	case selector == "*":
		// Wildcard: match all layers
		for i := range tilemap.Layers {
			matches = append(matches, &tilemap.Layers[i])
		}

	case strings.HasPrefix(selector, "#"):
		// Index selector: single match only
		if layer := findLayerByIndex(tilemap, selector); layer != nil {
			matches = append(matches, layer)
		}

	case strings.HasPrefix(selector, "[") && strings.HasSuffix(selector, "]"):
		// Attribute selector: find all matching layers
		attrExpr := selector[1 : len(selector)-1]
		for i := range tilemap.Layers {
			if matchesAttribute(&tilemap.Layers[i], attrExpr) {
				matches = append(matches, &tilemap.Layers[i])
			}
		}
	}

	return matches
}

// findLayerByIndex finds a layer by numeric index (#0, #1, etc.)
func findLayerByIndex(tilemap *TileMap, selector string) *TileLayer {
	indexStr := selector[1:] // Remove '#' prefix
	if idx, err := strconv.Atoi(indexStr); err == nil {
		if idx >= 0 && idx < len(tilemap.Layers) {
			return &tilemap.Layers[idx]
		}
	}
	return nil
}

// findLayerByAttribute finds the first layer matching an attribute expression
func findLayerByAttribute(tilemap *TileMap, attrExpr string) *TileLayer {
	for i := range tilemap.Layers {
		if matchesAttribute(&tilemap.Layers[i], attrExpr) {
			return &tilemap.Layers[i]
		}
	}
	return nil
}

// matchesAttribute checks if a layer matches an attribute expression
func matchesAttribute(layer *TileLayer, attrExpr string) bool {
	if layer.Props == nil {
		return false
	}

	attrExpr = strings.TrimSpace(attrExpr)

	if strings.Contains(attrExpr, "!=") {
		// Negated attribute: [key!="value"]
		return matchesNegatedAttribute(layer, attrExpr)
	} else if strings.Contains(attrExpr, "=") {
		// Exact attribute: [key="value"]
		return matchesExactAttribute(layer, attrExpr)
	} else {
		// Key exists: [key]
		key := strings.TrimSpace(attrExpr)
		_, exists := layer.Props[key]
		return exists
	}
}

// matchesExactAttribute checks [key="value"] pattern
func matchesExactAttribute(layer *TileLayer, attrExpr string) bool {
	parts := strings.SplitN(attrExpr, "=", 2)
	if len(parts) != 2 {
		return false
	}

	key := strings.TrimSpace(parts[0])
	value := strings.TrimSpace(parts[1])

	// Remove quotes if present
	value = strings.Trim(value, `"'`)

	return layer.Props[key] == value
}

// matchesNegatedAttribute checks [key!="value"] pattern
func matchesNegatedAttribute(layer *TileLayer, attrExpr string) bool {
	parts := strings.SplitN(attrExpr, "!=", 2)
	if len(parts) != 2 {
		return false
	}

	key := strings.TrimSpace(parts[0])
	value := strings.TrimSpace(parts[1])

	// Remove quotes if present
	value = strings.Trim(value, `"'`)

	// If key doesn't exist, treat as not equal to any value
	layerValue, exists := layer.Props[key]
	if !exists {
		return true
	}

	return layerValue != value
}

// HasLayerWithSelector checks if tilemap has any layer matching the selector
func HasLayerWithSelector(tilemap *TileMap, selector string) bool {
	return FindLayer(tilemap, selector) != nil
}

// CountLayersWithSelector counts how many layers match the selector
func CountLayersWithSelector(tilemap *TileMap, selector string) int {
	return len(FindLayers(tilemap, selector))
}
