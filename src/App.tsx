import { useState, useEffect } from 'react'
import MapboxMap from './components/Map/MapboxMap'
import Sidebar from './components/Sidebar/Sidebar'
import KPIDisplay from './components/KPI/KPIDisplay'
import ArrondissementRanking from './components/Ranking/ArrondissementRanking'
import {
  KPICategory,
  Quartier,
  QuartierKPIResponse,
  RankingResponse,
  fetchQuartierKPIs,
  fetchArrondissementRanking,
  searchAddress,
  lookupQuartier,
  fetchChoroplethScores,
  findQuartierByName,
  KPI_CATEGORIES,
  Address,
} from './services/apiService.ts'

export interface SelectedQuartier {
  code_insee: string
  nom_quartier: string
  arrondissement: number
  surface?: number
  perimetre?: number
  lat: number
  lon: number
}

type ViewMode = 'quartier' | 'arrondissement'

function App() {
  // ─── State ──────────────────────────────────────────────────────────
  const [selectedQuartier, setSelectedQuartier] = useState<SelectedQuartier | null>(null)
  const [selectedArrondissement, setSelectedArrondissement] = useState<number | null>(null)
  const [selectedCategories, setSelectedCategories] = useState<KPICategory[]>(['confort', 'surete', 'prix_m2'])
  const [viewMode, setViewMode] = useState<ViewMode>('quartier')
  const [mapLayerMode, setMapLayerMode] = useState<'arrondissement' | 'quartier'>('arrondissement')
  const [kpiData, setKpiData] = useState<QuartierKPIResponse | null>(null)
  const [kpiError, setKpiError] = useState(false)
  const [rankingData, setRankingData] = useState<RankingResponse | null>(null)
  const [selectedAddress, setSelectedAddress] = useState<Address | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [choroplethScores, setChoroplethScores] = useState<Record<string, number>>({})

  // ─── Choropleth scores (loaded from API, first selected category) ──
  const choroplethCategory = selectedCategories[0] || 'confort'
  const choroplethLabel = KPI_CATEGORIES.find((c: { key: KPICategory }) => c.key === choroplethCategory)?.label || 'Score'

  useEffect(() => {
    fetchChoroplethScores(choroplethCategory)
      .then(setChoroplethScores)
      .catch((err: unknown) => {
        console.error('Choropleth fetch error:', err)
        setChoroplethScores({})
      })
  }, [choroplethCategory])

  // ─── Fetch KPIs when quartier or categories change ─────────────────
  useEffect(() => {
    if (!selectedQuartier || selectedCategories.length === 0) {
      setKpiData(null)
      setKpiError(false)
      return
    }
    setIsLoading(true)
    setKpiError(false)
    fetchQuartierKPIs(selectedQuartier.code_insee, selectedCategories)
      .then((data: QuartierKPIResponse | null) => {
        if (data === null) {
          setKpiError(true)
        } else {
          setKpiData(data)
        }
      })
      .catch((err: unknown) => {
        console.error('KPI fetch error:', err)
        setKpiError(true)
      })
      .finally(() => setIsLoading(false))
  }, [selectedQuartier, selectedCategories])

  // ─── Fetch ranking when arrondissement or categories change ────────
  useEffect(() => {
    if (viewMode !== 'arrondissement' || selectedArrondissement === null || selectedCategories.length === 0) {
      setRankingData(null)
      return
    }
    setIsLoading(true)
    fetchArrondissementRanking(selectedArrondissement, selectedCategories)
      .then((data: RankingResponse) => setRankingData(data))
      .catch((err: unknown) => console.error('Ranking fetch error:', err))
      .finally(() => setIsLoading(false))
  }, [selectedArrondissement, selectedCategories, viewMode])

  // ─── Selection Handlers ────────────────────────────────────────────
  const handleQuartierSelect = (name: string | null) => {
    if (!name) return

    // Local search through our data
    searchAddress(name).then((results: Address[]) => {
      if (results.length > 0) {
        const result = results[0]
        
        if (result.type === 'Quartier') {
          findQuartierByName(result.rue).then((feature: Quartier | null) => {
            if (!feature) return

            setSelectedQuartier({
              code_insee: feature.code_insee,
              nom_quartier: feature.nom_quartier,
              arrondissement: feature.arrondissement,
              surface: feature.surface,
              perimetre: feature.perimetre,
              lat: feature.lat,
              lon: feature.lon,
            })
            setSelectedArrondissement(feature.arrondissement)
            setViewMode('quartier')
            setSelectedAddress(null)
          })
        } else {
          // Street selection
          setSelectedAddress(result)
          lookupQuartier(result.lat, result.lon).then((q: Quartier) => {
            setSelectedQuartier({
              code_insee: q.code_insee,
              nom_quartier: q.nom_quartier,
              arrondissement: q.arrondissement,
              surface: q.surface,
              perimetre: q.perimetre,
              lat: result.lat,
              lon: result.lon
            })
            setSelectedArrondissement(q.arrondissement)
            setViewMode('quartier')
          }).catch(console.error)
        }
      } else {
        // Fallback for direct clicks or exact matches
        findQuartierByName(name).then((feature: Quartier | null) => {
          if (!feature) return

          setSelectedQuartier({
            code_insee: feature.code_insee,
            nom_quartier: feature.nom_quartier,
            arrondissement: feature.arrondissement,
            surface: feature.surface,
            perimetre: feature.perimetre,
            lat: feature.lat,
            lon: feature.lon,
          })
          setSelectedArrondissement(feature.arrondissement)
          setViewMode('quartier')
          setSelectedAddress(null)
        })
      }
    })
  }

  const handleArrondissementSelect = (arrNum: number) => {
    setSelectedArrondissement(arrNum)
    setViewMode('arrondissement')
    setSelectedQuartier(null)
    setSelectedAddress(null)
  }

  const toggleCategory = (cat: KPICategory) => {
    setSelectedCategories(prev =>
      prev.includes(cat) ? prev.filter(c => c !== cat) : [...prev, cat]
    )
  }

  const handleAddressSelect = (addr: Address) => {
    setSelectedAddress(addr)
    // Use Turf point-in-polygon to find the correct quartier
    if (addr.lat && addr.lon) {
      lookupQuartier(addr.lat, addr.lon).then((q: Quartier) => {
        setSelectedQuartier({
          code_insee: q.code_insee,
          nom_quartier: q.nom_quartier,
          arrondissement: q.arrondissement,
          surface: q.surface,
          perimetre: q.perimetre,
          lat: addr.lat,
          lon: addr.lon,
        })
        setSelectedArrondissement(q.arrondissement)
        setViewMode('quartier')
      }).catch(console.error)
    }
  }

  return (
    <div className="relative w-screen h-screen overflow-hidden bg-slate-950 font-sans selection:bg-blue-500/30">
      {/* Background Map */}
      <div className="absolute inset-0 z-0">
        <MapboxMap
          selectedArrondissement={selectedQuartier?.nom_quartier || null}
          setSelectedArrondissement={handleQuartierSelect}
          selectedAddress={selectedAddress}
          choroplethScores={choroplethScores}
          choroplethLabel={choroplethLabel}
          onArrondissementClick={handleArrondissementSelect}
          mapLayerMode={mapLayerMode}
        />
      </div>

      {/* Map layer toggle — top-center */}
      <div className="absolute top-4 left-1/2 -translate-x-1/2 z-10 flex items-center gap-2 bg-slate-900/90 backdrop-blur-md border border-white/10 rounded-xl px-2 py-1 shadow-xl pointer-events-auto">
        <span className="text-[9px] font-bold text-slate-500 uppercase tracking-widest pl-1">Vue carte</span>
        <div className="flex items-center gap-1">
          {([
            { mode: 'arrondissement' as const, label: 'Arrondissements' },
            { mode: 'quartier' as const, label: 'Quartiers' },
          ]).map(({ mode, label }) => (
            <button
              key={mode}
              onClick={() => setMapLayerMode(mode)}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                mapLayerMode === mode
                  ? 'bg-white/10 text-white shadow-sm border border-white/20'
                  : 'text-slate-400 hover:text-white hover:bg-white/5 border border-transparent'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Sidebar — Left */}
      <div className="absolute top-4 left-4 bottom-4 w-[380px] z-10 flex flex-col pointer-events-auto">
        <Sidebar
          selectedQuartier={selectedQuartier}
          selectedArrondissement={selectedArrondissement}
          selectedCategories={selectedCategories}
          viewMode={viewMode}
          onQuartierSelect={handleQuartierSelect}
          onArrondissementSelect={handleArrondissementSelect}
          onCategoryToggle={toggleCategory}
          onViewModeChange={setViewMode}
          onAddressSelect={handleAddressSelect}
          onClose={() => {
            setSelectedQuartier(null)
            setSelectedArrondissement(null)
            setSelectedAddress(null)
            setKpiData(null)
            setRankingData(null)
          }}
        />
      </div>

      {/* Dashboard — Right Panel */}
      <div className="absolute top-4 right-4 bottom-4 w-[460px] z-20 flex flex-col pointer-events-none">
        <div className="pointer-events-auto h-full overflow-hidden flex flex-col">
          {viewMode === 'quartier' && selectedQuartier && (
            <KPIDisplay
              quartier={selectedQuartier}
              kpiData={kpiData}
              selectedCategories={selectedCategories}
              isLoading={isLoading}
              isError={kpiError}
              onClose={() => {
                setSelectedQuartier(null)
                setKpiData(null)
                setKpiError(false)
              }}
            />
          )}
          {viewMode === 'arrondissement' && selectedArrondissement !== null && (
            <ArrondissementRanking
              arrondissement={selectedArrondissement}
              rankingData={rankingData}
              selectedCategories={selectedCategories}
              isLoading={isLoading}
              onClose={() => {
                setSelectedArrondissement(null)
                setRankingData(null)
                setViewMode('quartier')
              }}
              onQuartierClick={handleQuartierSelect}
            />
          )}
        </div>
      </div>
    </div>
  )
}

export default App
