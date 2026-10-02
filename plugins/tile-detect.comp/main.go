//go:generate go tool wit-bindgen-go generate --world tile-detect-plugin --out internal ./gams:tile-detect@1.0.0.wasm

package main

import (
	"bytes"
	"fmt"
	"image"
	"image/png"
	"math"
	"sort"

	"github.com/kkgams/sdk/go/qoi"
	"github.com/kkgams/sdk/go/tilemap"
	tilewit "github.com/kkgams/tile-detect/internal/gams/tile-detect/tile-detect"
	"go.bytecodealliance.org/cm"
)

func init() {
	tilewit.Exports.DetectSize = func(sourceData cm.List[uint8], minSize uint32, maxSize uint32) cm.Result[tilewit.DetectSizeOutputShape, tilewit.DetectSizeOutput, string] {
		if sourceData.Len() == 0 {
			return cm.Err[cm.Result[tilewit.DetectSizeOutputShape, tilewit.DetectSizeOutput, string]]("source-data is required")
		}
		if minSize == 0 {
			minSize = 8
		}
		if maxSize == 0 {
			maxSize = 64
		}
		img, err := loadImageBytes(sourceData.Slice())
		if err != nil {
			return cm.Err[cm.Result[tilewit.DetectSizeOutputShape, tilewit.DetectSizeOutput, string]]("failed to load image: " + err.Error())
		}
		tileW, tileH, confidence := detectTileSize(img, int(minSize), int(maxSize))
		return cm.OK[cm.Result[tilewit.DetectSizeOutputShape, tilewit.DetectSizeOutput, string]](tilewit.DetectSizeOutput{
			TileW:      uint32(tileW),
			TileH:      uint32(tileH),
			Confidence: confidence,
		})
	}

	tilewit.Exports.Extract = func(config tilewit.ExtractConfig) cm.Result[tilewit.ExtractOutputShape, tilewit.ExtractOutput, string] {
		output, err := extract(config)
		if err != nil {
			return cm.Err[cm.Result[tilewit.ExtractOutputShape, tilewit.ExtractOutput, string]](err.Error())
		}
		return cm.OK[cm.Result[tilewit.ExtractOutputShape, tilewit.ExtractOutput, string]](output)
	}

	tilewit.Exports.ExportTileset = func(config tilewit.ExportTilesetConfig) cm.Result[tilewit.ExportTilesetOutputShape, tilewit.ExportTilesetOutput, string] {
		output, err := exportTileset(config)
		if err != nil {
			return cm.Err[cm.Result[tilewit.ExportTilesetOutputShape, tilewit.ExportTilesetOutput, string]](err.Error())
		}
		return cm.OK[cm.Result[tilewit.ExportTilesetOutputShape, tilewit.ExportTilesetOutput, string]](output)
	}

	tilewit.Exports.ToTilemap = func(output tilewit.ExtractOutput) cm.Result[tilewit.TileMapShape, tilewit.TileMap, string] {
		return cm.OK[cm.Result[tilewit.TileMapShape, tilewit.TileMap, string]](toWITTileMap(output))
	}
}

func loadImageBytes(data []byte) (*image.NRGBA, error) {
	if len(data) == 0 {
		return nil, fmt.Errorf("source-data is required")
	}

	var img image.Image
	var err error
	if len(data) >= 4 && string(data[:4]) == "qoif" {
		img, err = qoi.Decode(bytes.NewReader(data))
	} else {
		img, err = png.Decode(bytes.NewReader(data))
	}
	if err != nil {
		return nil, err
	}

	if nrgba, ok := img.(*image.NRGBA); ok {
		return nrgba, nil
	}

	bounds := img.Bounds()
	nrgba := image.NewNRGBA(image.Rect(0, 0, bounds.Dx(), bounds.Dy()))
	for y := bounds.Min.Y; y < bounds.Max.Y; y++ {
		for x := bounds.Min.X; x < bounds.Max.X; x++ {
			nrgba.Set(x-bounds.Min.X, y-bounds.Min.Y, img.At(x, y))
		}
	}
	return nrgba, nil
}

func encodeImage(img *image.NRGBA) ([]byte, error) {
	var buf bytes.Buffer
	if err := qoi.Encode(&buf, img); err != nil {
		return nil, err
	}
	return buf.Bytes(), nil
}

func hashTile(img *image.NRGBA, tileX, tileY, tileW, tileH, imgW, skipNth int) uint64 {
	var hash uint64 = 14695981039346656037
	startX := tileX * tileW
	startY := tileY * tileH
	step := skipNth
	if step < 1 {
		step = 1
	}
	for y := 0; y < tileH; y += step {
		for x := 0; x < tileW; x += step {
			idx := ((startY+y)*imgW + (startX + x)) * 4
			for c := 0; c < 4; c++ {
				hash ^= uint64(img.Pix[idx+c])
				hash *= 1099511628211
			}
		}
	}
	return hash
}

func tilesEqual(img *image.NRGBA, t1x, t1y, t2x, t2y, tileW, tileH, imgW, tolerance, skipNth int) bool {
	step := skipNth
	if step < 1 {
		step = 1
	}
	s1x, s1y := t1x*tileW, t1y*tileH
	s2x, s2y := t2x*tileW, t2y*tileH
	for y := 0; y < tileH; y += step {
		for x := 0; x < tileW; x += step {
			idx1 := ((s1y+y)*imgW + (s1x + x)) * 4
			idx2 := ((s2y+y)*imgW + (s2x + x)) * 4
			for c := 0; c < 4; c++ {
				diff := int(img.Pix[idx1+c]) - int(img.Pix[idx2+c])
				if diff < 0 {
					diff = -diff
				}
				if diff > tolerance {
					return false
				}
			}
		}
	}
	return true
}

func isTileEmpty(img *image.NRGBA, tileX, tileY, tileW, tileH, imgW int) bool {
	startX := tileX * tileW
	startY := tileY * tileH
	idx0 := (startY*imgW + startX) * 4
	r0, g0, b0, a0 := img.Pix[idx0], img.Pix[idx0+1], img.Pix[idx0+2], img.Pix[idx0+3]
	if a0 == 0 {
		allTransparent := true
		for y := 0; y < tileH && allTransparent; y++ {
			for x := 0; x < tileW && allTransparent; x++ {
				idx := ((startY+y)*imgW + (startX + x)) * 4
				if img.Pix[idx+3] > 0 {
					allTransparent = false
				}
			}
		}
		if allTransparent {
			return true
		}
	}
	for y := 0; y < tileH; y++ {
		for x := 0; x < tileW; x++ {
			idx := ((startY+y)*imgW + (startX + x)) * 4
			if img.Pix[idx] != r0 || img.Pix[idx+1] != g0 || img.Pix[idx+2] != b0 || img.Pix[idx+3] != a0 {
				return false
			}
		}
	}
	return true
}

func detectTileSize(img *image.NRGBA, minSize, maxSize int) (int, int, float64) {
	bounds := img.Bounds()
	imgW, imgH := bounds.Dx(), bounds.Dy()
	bestSize := 16
	bestScore := 0.0
	commonSizes := []int{8, 16, 24, 32, 48, 64}
	for _, size := range commonSizes {
		if size < minSize || size > maxSize || imgW%size != 0 || imgH%size != 0 {
			continue
		}
		score := scoreTileSize(img, size, size, imgW, imgH)
		if score > bestScore {
			bestScore = score
			bestSize = size
		}
	}
	for size := minSize; size <= maxSize; size++ {
		if imgW%size != 0 || imgH%size != 0 {
			continue
		}
		score := scoreTileSize(img, size, size, imgW, imgH) * 0.9
		if score > bestScore {
			bestScore = score
			bestSize = size
		}
	}
	return bestSize, bestSize, bestScore
}

func scoreTileSize(img *image.NRGBA, tileW, tileH, imgW, imgH int) float64 {
	cols := imgW / tileW
	rows := imgH / tileH
	if cols < 2 || rows < 2 {
		return 0
	}
	hashes := make(map[uint64]int)
	total := 0
	for y := 0; y < rows; y++ {
		for x := 0; x < cols; x++ {
			hash := hashTile(img, x, y, tileW, tileH, imgW, 2)
			hashes[hash]++
			total++
		}
	}
	unique := len(hashes)
	if unique == total {
		return 0.1
	}
	duplicateRatio := 1.0 - float64(unique)/float64(total)
	gridBonus := 1.0
	if tileW == 8 || tileW == 16 || tileW == 32 {
		gridBonus = 1.2
	}
	return duplicateRatio * gridBonus
}

func extract(config tilewit.ExtractConfig) (tilewit.ExtractOutput, error) {
	if config.SourceData.Len() == 0 {
		return tilewit.ExtractOutput{}, fmt.Errorf("source-data is required")
	}
	if config.TileW == 0 || config.TileH == 0 {
		return tilewit.ExtractOutput{}, fmt.Errorf("tile-w and tile-h must be positive")
	}
	img, err := loadImageBytes(config.SourceData.Slice())
	if err != nil {
		return tilewit.ExtractOutput{}, fmt.Errorf("failed to load image: %w", err)
	}
	imgW, imgH := img.Bounds().Dx(), img.Bounds().Dy()
	tileW, tileH := int(config.TileW), int(config.TileH)
	cols := imgW / tileW
	rows := imgH / tileH
	if cols <= 0 || rows <= 0 {
		return tilewit.ExtractOutput{}, fmt.Errorf("image is smaller than tile size")
	}
	tolerance := int(config.Tolerance)
	skipNth := int(config.SkipNthPixel)
	if skipNth <= 0 {
		skipNth = 1
	}
	type uniqueTile struct {
		id    int
		hash  uint64
		tileX int
		tileY int
	}
	var uniqueTiles []uniqueTile
	hashToID := make(map[uint64]int)
	tilemapData := make([]uint32, cols*rows)
	for ty := 0; ty < rows; ty++ {
		for tx := 0; tx < cols; tx++ {
			tileIdx := ty*cols + tx
			if isTileEmpty(img, tx, ty, tileW, tileH, imgW) {
				tilemapData[tileIdx] = 0
				continue
			}
			hash := hashTile(img, tx, ty, tileW, tileH, imgW, skipNth)
			if existingID, exists := hashToID[hash]; exists {
				if tolerance > 0 {
					found := false
					for _, ut := range uniqueTiles {
						if ut.hash == hash && tilesEqual(img, tx, ty, ut.tileX, ut.tileY, tileW, tileH, imgW, tolerance, skipNth) {
							tilemapData[tileIdx] = uint32(ut.id)
							found = true
							break
						}
					}
					if !found {
						newID := len(uniqueTiles) + 1
						uniqueTiles = append(uniqueTiles, uniqueTile{newID, hash, tx, ty})
						tilemapData[tileIdx] = uint32(newID)
					}
				} else {
					tilemapData[tileIdx] = uint32(existingID)
				}
			} else {
				newID := len(uniqueTiles) + 1
				uniqueTiles = append(uniqueTiles, uniqueTile{newID, hash, tx, ty})
				hashToID[hash] = newID
				tilemapData[tileIdx] = uint32(newID)
			}
		}
	}
	tilebank := make([]tilewit.TileBankEntry, 0, len(uniqueTiles))
	for _, ut := range uniqueTiles {
		tilebank = append(tilebank, tilewit.TileBankEntry{
			ID:          uint32(ut.id),
			SourceIndex: uint32(ut.tileY*cols + ut.tileX),
			Hash:        ut.hash,
		})
	}
	return tilewit.ExtractOutput{
		Tilebank: cm.ToList(tilebank),
		Tilemap: tilewit.TilemapData{
			Width:  uint32(cols),
			Height: uint32(rows),
			TileW:  config.TileW,
			TileH:  config.TileH,
			Data:   cm.ToList(tilemapData),
		},
	}, nil
}

func exportTileset(config tilewit.ExportTilesetConfig) (tilewit.ExportTilesetOutput, error) {
	tilebank := config.Tilebank.Slice()
	if len(tilebank) == 0 {
		return tilewit.ExportTilesetOutput{}, fmt.Errorf("tilebank is empty")
	}
	if config.SourceData.Len() == 0 {
		return tilewit.ExportTilesetOutput{}, fmt.Errorf("source-data is required")
	}
	if config.SourceCols == 0 {
		return tilewit.ExportTilesetOutput{}, fmt.Errorf("source-cols must be positive")
	}
	if config.TileW == 0 || config.TileH == 0 {
		return tilewit.ExportTilesetOutput{}, fmt.Errorf("tile-w and tile-h must be positive")
	}
	sourceImg, err := loadImageBytes(config.SourceData.Slice())
	if err != nil {
		return tilewit.ExportTilesetOutput{}, fmt.Errorf("failed to load source image: %w", err)
	}
	sourceW := sourceImg.Bounds().Dx()
	numTiles := len(tilebank)
	cols := int(math.Ceil(math.Sqrt(float64(numTiles))))
	rows := int(math.Ceil(float64(numTiles) / float64(cols)))
	tileW, tileH := int(config.TileW), int(config.TileH)
	tilesetW := cols * tileW
	tilesetH := rows * tileH
	tileset := image.NewNRGBA(image.Rect(0, 0, tilesetW, tilesetH))
	sortedTilebank := append([]tilewit.TileBankEntry(nil), tilebank...)
	sort.Slice(sortedTilebank, func(i, j int) bool { return sortedTilebank[i].ID < sortedTilebank[j].ID })
	for _, tile := range sortedTilebank {
		srcTileX := int(tile.SourceIndex % config.SourceCols)
		srcTileY := int(tile.SourceIndex / config.SourceCols)
		srcStartX := srcTileX * tileW
		srcStartY := srcTileY * tileH
		tileIndex := int(tile.ID) - 1
		destX := (tileIndex % cols) * tileW
		destY := (tileIndex / cols) * tileH
		for y := 0; y < tileH; y++ {
			for x := 0; x < tileW; x++ {
				srcIdx := ((srcStartY+y)*sourceW + (srcStartX + x)) * 4
				dstIdx := ((destY+y)*tilesetW + (destX + x)) * 4
				copy(tileset.Pix[dstIdx:dstIdx+4], sourceImg.Pix[srcIdx:srcIdx+4])
			}
		}
	}
	data, err := encodeImage(tileset)
	if err != nil {
		return tilewit.ExportTilesetOutput{}, fmt.Errorf("failed to encode tileset: %w", err)
	}
	return tilewit.ExportTilesetOutput{
		Data:   cm.ToList(data),
		Width:  uint32(tilesetW),
		Height: uint32(tilesetH),
		Cols:   uint32(cols),
		Rows:   uint32(rows),
	}, nil
}

func toWITTileMap(output tilewit.ExtractOutput) tilewit.TileMap {
	tm := &tilemap.TileMap{
		Props: map[string]string{
			"tileWidth":  fmt.Sprintf("%d", output.Tilemap.TileW),
			"tileHeight": fmt.Sprintf("%d", output.Tilemap.TileH),
		},
		Layers: []tilemap.TileLayer{
			{
				Width: int(output.Tilemap.Width),
				Data:  append([]uint32(nil), output.Tilemap.Data.Slice()...),
				Props: map[string]string{"name": "extracted"},
			},
		},
	}
	layers := make([]tilewit.TileLayer, len(tm.Layers))
	for i, layer := range tm.Layers {
		layers[i] = tilewit.TileLayer{
			Width: uint32(layer.Width),
			Data:  cm.ToList(layer.Data),
			Props: toWITData(layer.Props),
		}
	}
	return tilewit.TileMap{Layers: cm.ToList(layers), Props: toWITData(tm.Props)}
}

func toWITData(data map[string]string) cm.List[tilewit.DataEntry] {
	entries := make([]tilewit.DataEntry, 0, len(data))
	keys := make([]string, 0, len(data))
	for key := range data {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	for _, key := range keys {
		entries = append(entries, tilewit.DataEntry{key, data[key]})
	}
	return cm.ToList(entries)
}

func main() {}
