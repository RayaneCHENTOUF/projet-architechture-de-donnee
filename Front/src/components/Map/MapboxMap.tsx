import { useCallback, useMemo, useState, useEffect, useRef } from 'react'
import Map, { Source, Layer, MapLayerMouseEvent, Marker, MapRef } from 'react-map-gl'
import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import type { Address } from '../../services/apiService.ts'
import { fetchArrondissementsGeoJSON, fetchQuartiersGeoJSON } from '../../services/apiService.ts'

interface MapboxMapProps {
  selectedArrondissement: string | null
  setSelectedArrondissement: (id: string | null) => void
  selectedAddress: Address | null
  choroplethScores: Record<string, number>
  choroplethLabel: string
  onArrondissementClick?: (arrNum: number) => void
  mapLayerMode: 'arrondissement' | 'quartier'
}

type QuartierFeature = {
  properties?: Record<string, unknown> | null
  geometry: { type: string }
}

function getQuartierName(feature: QuartierFeature): string | null {
  const properties = feature.properties ?? undefined
  const value = properties?.l_qu ?? properties?.nom_quartier
  return typeof value === 'string' && value.trim() ? value : null
}

function getQuartierCodeInsee(feature: QuartierFeature): string | null {
  const properties = feature.properties ?? undefined
  const value = properties?.c_quinsee ?? properties?.code_insee_quartier
  if (typeof value === 'string' && value.trim()) return value
  if (typeof value === 'number' && Number.isFinite(value)) return String(value)
  return null
}

function hasPolygonGeometry(features: Array<{ geometry: { type: string } }> | null): boolean {
  return !!features?.some(f => f.geometry.type === 'Polygon' || f.geometry.type === 'MultiPolygon')
}

function buildSelectedFilter(selectedName: string) {
  return [
    'any',
    ['==', ['get', 'l_qu'], selectedName],
    ['==', ['get', 'nom_quartier'], selectedName],
  ] as const
}

function scoreToColor(score: number): string {
  const s = Math.max(0, Math.min(100, score))
  if (s < 33) {
    const t = s / 33
    return `rgb(220,${Math.round(60 + 140 * t)},${Math.round(60 * (1 - t))})`
  } else if (s < 66) {
    const t = (s - 33) / 33
    return `rgb(${Math.round(220 - 150 * t)},${Math.round(200 + 30 * t)},${Math.round(40 + 60 * t)})`
  } else {
    const t = (s - 66) / 34
    return `rgb(${Math.round(70 - 30 * t)},${Math.round(230 - 40 * t)},${Math.round(100 + 80 * t)})`
  }
}

export default function MapboxMap({
  selectedArrondissement,
  setSelectedArrondissement,
  selectedAddress,
  choroplethScores,
  choroplethLabel,
  onArrondissementClick,
  mapLayerMode,
}: MapboxMapProps) {
  const mapRef = useRef<MapRef>(null)
  const [hoverInfo, setHoverInfo] = useState<{
    x: number; y: number; name: string; score: number | null; isArrondissement: boolean
  } | null>(null)
  const [data, setData] = useState<Awaited<ReturnType<typeof fetchQuartiersGeoJSON>> | null>(null)
  const [arrondissementsData, setArrondissementsData] = useState<Awaited<ReturnType<typeof fetchArrondissementsGeoJSON>> | null>(null)

  const selectedName = selectedArrondissement?.trim() || ''
  const isPolygonDataset = hasPolygonGeometry(data?.features ?? null)
  const hasArrondissementGeometry = hasPolygonGeometry(arrondissementsData?.features ?? null)
  const hasChoropleth = Object.keys(choroplethScores).length > 0

  const showArrondissements = mapLayerMode === 'arrondissement'
  const showQuartiers = mapLayerMode === 'quartier'

  useEffect(() => {
    Promise.all([fetchQuartiersGeoJSON(), fetchArrondissementsGeoJSON()])
      .then(([quartiers, arrondissements]) => {
        setData(quartiers)
        setArrondissementsData(arrondissements)
      })
      .catch(console.error)
  }, [])

  // Aggregate quartier choropleth scores → arrondissement-level average scores
  const arrondissementScores = useMemo(() => {
    if (!data || !hasChoropleth) return {}
    const sums: Record<string, { sum: number; count: number }> = {}
    for (const feature of data.features) {
      const props = feature.properties as unknown as Record<string, unknown> | null
      const arr = String(props?.c_ar ?? props?.arrondissement ?? '')
      const insee = String(props?.c_quinsee ?? props?.code_insee_quartier ?? '')
      const score = choroplethScores[insee]
      if (score !== undefined && arr) {
        if (!sums[arr]) sums[arr] = { sum: 0, count: 0 }
        sums[arr].sum += score
        sums[arr].count++
      }
    }
    const result: Record<string, number> = {}
    for (const [arr, { sum, count }] of Object.entries(sums)) {
      result[arr] = sum / count
    }
    return result
  }, [data, choroplethScores, hasChoropleth])

  const quartierFillExpression = useMemo(() => {
    if (!hasChoropleth) {
      return ['literal', '#334155'] as unknown as maplibregl.ExpressionSpecification
    }
    const expr: (string | number | string[])[] = ['match', ['to-string', ['get', 'c_quinsee']]]
    for (const [insee, score] of Object.entries(choroplethScores)) {
      expr.push(String(insee))
      expr.push(scoreToColor(score))
    }
    expr.push('#334155')
    return expr as unknown as maplibregl.ExpressionSpecification
  }, [choroplethScores, hasChoropleth])

  // Choropleth fill expression — arrondissement level (avg of quartier scores)
  const arrondissementFillExpression = useMemo(() => {
    if (Object.keys(arrondissementScores).length === 0) {
      return ['literal', '#1e293b'] as unknown as maplibregl.ExpressionSpecification
    }
    // Use integer keys to match the integer arrondissement values in the GeoJSON
    const expr: (string | number | string[])[] = ['match', ['get', 'arrondissement']]
    for (const [arr, score] of Object.entries(arrondissementScores)) {
      expr.push(parseInt(arr, 10))
      expr.push(scoreToColor(score))
    }
    expr.push('#334155')
    return expr as unknown as maplibregl.ExpressionSpecification
  }, [arrondissementScores])

  const onHover = useCallback((event: MapLayerMouseEvent) => {
    const { features, point: { x, y } } = event
    const hoveredFeature = features && features[0]
    if (!hoveredFeature) { setHoverInfo(null); return }

    const layerId = (hoveredFeature as unknown as { layer?: { id?: string } }).layer?.id ?? ''

    if (layerId === 'arrondissements-fill') {
      const props = hoveredFeature.properties as Record<string, unknown> | null
      const arrStr = String(props?.arrondissement ?? '')
      const arrNum = parseInt(arrStr, 10)
      const name = !isNaN(arrNum)
        ? `${arrNum}${arrNum === 1 ? 'er' : 'e'} arrondissement`
        : arrStr
      const score = arrondissementScores[String(arrNum)] ?? arrondissementScores[arrStr] ?? null
      setHoverInfo({ x, y, name, score, isArrondissement: true })
    } else {
      const name = getQuartierName(hoveredFeature as unknown as QuartierFeature)
      if (name) {
        const insee = getQuartierCodeInsee(hoveredFeature as unknown as QuartierFeature)
        const score = insee ? choroplethScores[insee] ?? null : null
        setHoverInfo({ x, y, name, score, isArrondissement: false })
      } else {
        setHoverInfo(null)
      }
    }
  }, [choroplethScores, arrondissementScores])

  const onClick = useCallback((event: MapLayerMouseEvent) => {
    const feature = event.features && event.features[0]
    if (!feature) { setSelectedArrondissement(null); return }

    const layerId = (feature as unknown as { layer?: { id?: string } }).layer?.id ?? ''

    if (layerId === 'arrondissements-fill') {
      const props = feature.properties as Record<string, unknown> | null
      const arrNum = parseInt(String(props?.arrondissement ?? ''), 10)
      if (!isNaN(arrNum) && onArrondissementClick) {
        onArrondissementClick(arrNum)
      }
    } else {
      const name = getQuartierName(feature as unknown as QuartierFeature)
      if (name) setSelectedArrondissement(name)
      else setSelectedArrondissement(null)
    }
  }, [setSelectedArrondissement, onArrondissementClick])

  useEffect(() => {
    if (selectedAddress && selectedAddress.lat && selectedAddress.lon && mapRef.current) {
      mapRef.current.flyTo({
        center: [selectedAddress.lon, selectedAddress.lat],
        zoom: 18,
        pitch: 60,
        bearing: 20,
        duration: 1800,
        essential: true
      })
    }
  }, [selectedAddress])

  const parisBounds = [
    [2.225, 48.815],
    [2.4698, 48.9015]
  ] as [[number, number], [number, number]]

  const interactiveLayerIds = [
    ...(showArrondissements ? ['arrondissements-fill'] : []),
    ...(showQuartiers && isPolygonDataset ? ['paris-fill'] : []),
    ...(showQuartiers && !isPolygonDataset ? ['paris-points'] : []),
  ]

  return (
    <div className="w-full h-full bg-slate-950">
      <Map
        ref={mapRef}
        mapLib={maplibregl as any}
        initialViewState={{
          longitude: 2.3488,
          latitude: 48.8534,
          zoom: 12,
          pitch: 45,
          bearing: 0
        }}
        maxBounds={parisBounds}
        minZoom={11}
        maxZoom={20}
        mapStyle="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"
        interactiveLayerIds={interactiveLayerIds}
        onMouseMove={onHover}
        onClick={onClick}
        cursor={hoverInfo ? 'pointer' : 'grab'}
      >
        <Layer
          id="3d-buildings"
          source="openmaptiles"
          source-layer="building"
          type="fill-extrusion"
          minzoom={14.5}
          paint={{
            'fill-extrusion-color': '#1e293b',
            'fill-extrusion-height': ['get', 'render_height'],
            'fill-extrusion-base': ['get', 'render_min_height'],
            'fill-extrusion-opacity': 0.6
          }}
        />

        {/* ── Arrondissement layer ────────────────────────────────────────── */}
        {arrondissementsData && hasArrondissementGeometry && (
          <Source id="arrondissements" type="geojson" data={arrondissementsData}>
            <Layer
              id="arrondissements-fill"
              type="fill"
              layout={{ visibility: showArrondissements ? 'visible' : 'none' }}
              paint={{
                'fill-color': arrondissementFillExpression,
                'fill-opacity': hasChoropleth ? 0.65 : 0.15,
              }}
            />
            <Layer
              id="arrondissements-borders"
              type="line"
              paint={{
                'line-color': '#94a3b8',
                'line-width': 2,
                'line-opacity': 0.9,
              }}
            />
            <Layer
              id="arrondissements-labels"
              type="symbol"
              layout={{
                'text-field': ['coalesce',
                  ['get', 'nom_arrondissement'],
                  ['get', 'nom_officiel_arrondissement'],
                  ['to-string', ['get', 'arrondissement']],
                ],
                'text-size': 11,
                'text-anchor': 'center',
              }}
              paint={{
                'text-color': '#cbd5e1',
                'text-halo-color': '#020617',
                'text-halo-width': 1.2,
              }}
            />
          </Source>
        )}

        {/* ── Quartier layer ──────────────────────────────────────────────── */}
        {data && isPolygonDataset && (
          <Source id="paris" type="geojson" data={data}>
            <Layer
              id="paris-fill"
              type="fill"
              layout={{ visibility: showQuartiers ? 'visible' : 'none' }}
              paint={{
                'fill-color': quartierFillExpression,
                'fill-opacity': hasChoropleth ? 0.65 : 0.4,
              }}
            />
            <Layer
              id="paris-selected"
              type="fill"
              layout={{ visibility: showQuartiers ? 'visible' : 'none' }}
              filter={buildSelectedFilter(selectedName) as any}
              paint={{
                'fill-color': '#3b82f6',
                'fill-opacity': 0.5,
              }}
            />
            <Layer
              id="paris-borders"
              type="line"
              layout={{ visibility: showQuartiers ? 'visible' : 'none' }}
              paint={{
                'line-color': hasChoropleth ? '#0f172a' : '#334155',
                'line-width': hasChoropleth ? 1 : 1.5,
                'line-opacity': 0.8,
              }}
            />
            <Layer
              id="paris-borders-selected"
              type="line"
              layout={{ visibility: showQuartiers ? 'visible' : 'none' }}
              filter={buildSelectedFilter(selectedName) as any}
              paint={{
                'line-color': '#60a5fa',
                'line-width': 2.5,
              }}
            />
          </Source>
        )}

        {data && !isPolygonDataset && (
          <Source id="paris-points-source" type="geojson" data={data}>
            <Layer
              id="paris-points"
              type="circle"
              layout={{ visibility: showQuartiers ? 'visible' : 'none' }}
              paint={{
                'circle-radius': 7,
                'circle-color': quartierFillExpression,
                'circle-stroke-color': '#0f172a',
                'circle-stroke-width': 1.5,
                'circle-opacity': 0.9,
              }}
            />
            <Layer
              id="paris-points-selected"
              type="circle"
              layout={{ visibility: showQuartiers ? 'visible' : 'none' }}
              filter={buildSelectedFilter(selectedName) as any}
              paint={{
                'circle-radius': 11,
                'circle-color': '#3b82f6',
                'circle-stroke-color': '#bfdbfe',
                'circle-stroke-width': 2,
                'circle-opacity': 0.95,
              }}
            />
            <Layer
              id="paris-points-labels"
              type="symbol"
              layout={{
                visibility: showQuartiers ? 'visible' : 'none',
                'text-field': ['get', 'nom_quartier'],
                'text-size': 11,
                'text-offset': [0, 1.25],
                'text-anchor': 'top',
              }}
              paint={{
                'text-color': '#e2e8f0',
                'text-halo-color': '#0f172a',
                'text-halo-width': 1.25,
              }}
            />
          </Source>
        )}

        {/* Address Marker */}
        {selectedAddress && selectedAddress.lat && selectedAddress.lon && (
          <Marker
            longitude={selectedAddress.lon}
            latitude={selectedAddress.lat}
            anchor="bottom"
          >
            <div className="relative flex flex-col items-center" style={{ filter: 'drop-shadow(0 4px 16px rgba(59,130,246,0.7))' }}>
              <div className="mb-2 bg-slate-900/95 backdrop-blur-sm border border-blue-500/40 text-white text-xs font-bold px-3 py-1.5 rounded-xl shadow-xl whitespace-nowrap max-w-[180px] truncate">
                {selectedAddress.numero} {selectedAddress.rue}
              </div>
              <svg width="28" height="36" viewBox="0 0 28 36" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M14 0C6.268 0 0 6.268 0 14C0 24.5 14 36 14 36C14 36 28 24.5 28 14C28 6.268 21.732 0 14 0Z" fill="#3b82f6"/>
                <circle cx="14" cy="14" r="6" fill="white"/>
              </svg>
              <div className="absolute bottom-0 w-8 h-8 rounded-full bg-blue-400/30 animate-ping" style={{ bottom: '2px' }} />
            </div>
          </Marker>
        )}

        {/* Hover tooltip */}
        {hoverInfo && (
          <div
            className="absolute z-10 bg-slate-900/95 backdrop-blur-sm border border-slate-600 px-4 py-2 text-sm font-semibold text-slate-100 rounded-xl shadow-2xl pointer-events-none transform -translate-x-1/2 -translate-y-full"
            style={{ left: hoverInfo.x, top: hoverInfo.y - 12 }}
          >
            <div className="text-white font-bold">{hoverInfo.name}</div>
            {hoverInfo.score !== null && (
              <div className="text-xs mt-0.5 flex items-center gap-2">
                <span className="text-slate-400">
                  {hoverInfo.isArrondissement ? `${choroplethLabel} (moy.)` : choroplethLabel}:
                </span>
                <span className="font-black" style={{ color: scoreToColor(hoverInfo.score) }}>
                  {Math.round(hoverInfo.score)}/100
                </span>
              </div>
            )}
          </div>
        )}
      </Map>

      {/* Choropleth Legend */}
      {hasChoropleth && (
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 z-20 bg-slate-900/90 backdrop-blur-md border border-white/10 rounded-2xl px-6 py-3 flex items-center gap-4 shadow-2xl pointer-events-none">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{choroplethLabel}</span>
          <div className="flex items-center gap-1">
            <span className="text-[9px] font-bold text-red-400">0</span>
            <div className="w-32 h-2.5 rounded-full" style={{
              background: 'linear-gradient(to right, rgb(220,60,60), rgb(220,200,0), rgb(70,230,100), rgb(40,190,180))'
            }} />
            <span className="text-[9px] font-bold text-teal-400">100</span>
          </div>
        </div>
      )}
    </div>
  )
}
