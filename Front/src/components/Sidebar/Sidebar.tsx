import { X, Search, MapPin, Building2, Trophy, Filter, Navigation, Shield, Banknote, Home, Building, Scale, Leaf } from 'lucide-react'
import { useMemo, useState, useEffect } from 'react'
import { KPI_CATEGORIES, KPICategory, Address, fetchQuartierAddresses } from '../../services/apiService'
import { RUES_PAR_ARRONDISSEMENT } from '../../data/mock-addresses'
import type { SelectedQuartier } from '../../App'
import parisData from '../../data/paris-quartiers.json'

interface SidebarProps {
  selectedQuartier: SelectedQuartier | null
  selectedArrondissement: number | null
  selectedCategories: KPICategory[]
  viewMode: 'quartier' | 'arrondissement'
  onQuartierSelect: (name: string) => void
  onArrondissementSelect: (arr: number) => void
  onCategoryToggle: (cat: KPICategory) => void
  onViewModeChange: (mode: 'quartier' | 'arrondissement') => void
  onAddressSelect: (addr: Address) => void
  onClose: () => void
}

const getCategoryIcon = (key: string) => {
  switch (key) {
    case 'confort': return <Leaf className="w-4 h-4" />
    case 'surete': return <Shield className="w-4 h-4" />
    case 'prix_m2': return <Banknote className="w-4 h-4" />
    case 'loyers': return <Home className="w-4 h-4" />
    case 'logements_sociaux': return <Building className="w-4 h-4" />
    case 'comparaison': return <Scale className="w-4 h-4" />
    default: return <Filter className="w-4 h-4" />
  }
}

export default function Sidebar({
  selectedQuartier,
  selectedArrondissement,
  selectedCategories,
  viewMode,
  onQuartierSelect,
  onArrondissementSelect,
  onCategoryToggle,
  onViewModeChange,
  onAddressSelect,
  onClose
}: SidebarProps) {
  const [activeTab, setActiveTab] = useState<'list' | 'arr'>('list')
  const [searchTerm, setSearchTerm] = useState('')
  const [addresses, setAddresses] = useState<Address[]>([])
  const [isLoadingAddresses, setIsLoadingAddresses] = useState(false)

  // ─── Fetch Addresses when quartier changes ────────────────────────
  useEffect(() => {
    if (selectedQuartier) {
      setIsLoadingAddresses(true)
      fetchQuartierAddresses(selectedQuartier.code_insee)
        .then(setAddresses)
        .catch(console.error)
        .finally(() => setIsLoadingAddresses(false))
    } else {
      setAddresses([])
    }
  }, [selectedQuartier])

  // ─── Quartiers List ────────────────────────────────────────────────
  const allQuartiers = useMemo(() => {
    const geoData = parisData as unknown as { features: { properties: { l_qu: string } }[] }
    const list = geoData.features.map(f => f.properties.l_qu)
    return list.sort((a, b) => a.localeCompare(b, 'fr'))
  }, [])

  // ─── Search Results (Quartiers + Streets) ──────────────────────────
  const [searchResults, setSearchResults] = useState<{ type: 'Quartier' | 'Rue'; name: string; full?: string; arr?: number }[]>([])

  useEffect(() => {
    const timer = setTimeout(() => {
      if (!searchTerm.trim()) {
        const geoData = parisData as unknown as { features: { properties: { l_qu: string; c_ar: number } }[] }
        setSearchResults(geoData.features.map(f => ({
          type: 'Quartier',
          name: f.properties.l_qu,
          arr: f.properties.c_ar
        })).sort((a, b) => a.name.localeCompare(b.name, 'fr')))
        return
      }

      const q = searchTerm.toLowerCase()
      const quartierMatches = allQuartiers
        .filter(name => name.toLowerCase().includes(q))
        .map(name => {
          const feature = (parisData as any).features.find((f: any) => f.properties.l_qu === name)
          return { 
            type: 'Quartier' as const, 
            name,
            arr: feature?.properties.c_ar
          }
        })

      // Search in streets
      const streetResults: { type: 'Rue'; name: string; full: string; arr: number }[] = []
      for (const [arr, rues] of Object.entries(RUES_PAR_ARRONDISSEMENT)) {
        const arrNum = parseInt(arr)
        rues.forEach(rue => {
          if (rue.toLowerCase().includes(q)) {
            streetResults.push({
              type: 'Rue',
              name: rue,
              full: `${rue}, 750${String(arrNum).padStart(2, '0')} Paris`,
              arr: arrNum
            })
          }
        })
      }

      setSearchResults([...quartierMatches, ...streetResults.slice(0, 20)])
    }, 300)

    return () => clearTimeout(timer)
  }, [searchTerm, allQuartiers])

  // ─── Arrondissements ──────────────────────────────────────────────
  const arrondissements = Array.from({ length: 20 }, (_, i) => i + 1)

  return (
    <div className="h-full w-full bg-slate-900/95 backdrop-blur-md border-r border-white/5 flex flex-col shadow-2xl overflow-hidden">
      {/* Header */}
      <div className="p-6 border-b border-white/5">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
            <div className="w-8 h-8 bg-slate-800 rounded flex items-center justify-center border border-white/10">
              <MapPin className="w-4 h-4 text-slate-300" />
            </div>
            URBAN <span className="text-slate-500">PARIS</span>
          </h1>
          {selectedQuartier && (
            <button 
              onClick={onClose}
              className="p-1.5 hover:bg-white/5 rounded-lg text-slate-500 hover:text-white transition-all"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Tabs */}
      {!selectedQuartier && (
        <div className="flex px-4 pt-4 gap-2">
          {([
            { id: 'list' as const, icon: Building2, label: 'Quartiers' },
            { id: 'arr' as const, icon: Trophy, label: 'Classement' },
          ]).map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-lg text-xs font-semibold transition-all border ${
                activeTab === tab.id
                  ? 'bg-white/10 border-white/20 text-white shadow-sm'
                  : 'bg-transparent border-transparent text-slate-500 hover:bg-white/5'
              }`}
            >
              <tab.icon className="w-3 h-3" />
              {tab.label}
            </button>
          ))}
        </div>
      )}

      {/* Category Filter */}
      <div className="p-4">
        <div className="bg-slate-800/40 border border-white/5 rounded-xl p-3">
          <div className="flex items-center gap-1.5 mb-3 px-1 text-[10px] font-bold text-slate-500 uppercase tracking-widest">
            <Filter className="w-3 h-3" /> Filtres KPI
          </div>
          <div className="grid grid-cols-3 gap-1.5">
            {KPI_CATEGORIES.map(cat => (
              <button
                key={cat.key}
                onClick={() => onCategoryToggle(cat.key)}
                className={`p-2 rounded-lg border transition-all flex flex-col items-center gap-1 group ${
                  selectedCategories.includes(cat.key)
                    ? 'bg-slate-700/50 border-white/20 text-white'
                    : 'bg-transparent border-transparent text-slate-500 hover:bg-white/5'
                }`}
              >
                {getCategoryIcon(cat.key)}
                <span className="text-[9px] font-semibold truncate w-full text-center">{cat.label}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-4 pb-6 space-y-4 custom-scrollbar">
        {selectedQuartier ? (
          <div className="space-y-6 fade-in">
            {/* Selected Quartier Info */}
            <div className="bg-slate-800/50 border border-white/10 rounded-2xl p-5">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-xl bg-slate-700 flex items-center justify-center text-white border border-white/10">
                  <MapPin className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-lg font-bold text-white leading-tight">{selectedQuartier.nom_quartier}</h2>
                  <p className="text-[10px] text-slate-400 font-semibold uppercase tracking-widest mt-0.5">
                    {selectedQuartier.arrondissement}e Arrondissement
                  </p>
                </div>
              </div>
              
              <div className="grid grid-cols-2 gap-2">
                <div className="bg-slate-900/50 p-2 rounded-lg border border-white/5">
                  <div className="text-[9px] font-bold text-slate-500 uppercase">Code INSEE</div>
                  <div className="text-sm font-bold text-slate-200">{selectedQuartier.code_insee}</div>
                </div>
                <div className="bg-slate-900/50 p-2 rounded-lg border border-white/5">
                  <div className="text-[9px] font-bold text-slate-500 uppercase">Surface</div>
                  <div className="text-sm font-bold text-slate-200">{selectedQuartier.surface > 0 ? Math.round(selectedQuartier.surface / 10000) : '--'} ha</div>
                </div>
              </div>
            </div>

            {/* Addresses List */}
            <div className="space-y-2">
              <h3 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest px-1">
                Adresses ({addresses.length})
              </h3>
              
              <div className="space-y-1">
                {isLoadingAddresses ? (
                  <div className="space-y-2">
                    {[1, 2, 3].map(i => (
                      <div key={i} className="h-12 bg-white/5 rounded-lg animate-pulse"></div>
                    ))}
                  </div>
                ) : addresses.length > 0 ? (
                  addresses.map((addr, idx) => (
                    <button
                      key={idx}
                      onClick={() => onAddressSelect(addr)}
                      className="w-full text-left p-3 rounded-xl bg-white/5 border border-white/5 hover:border-blue-500/30 hover:bg-blue-500/5 transition-all group flex items-center gap-3"
                    >
                      <div className="w-8 h-8 rounded-lg bg-slate-800 flex items-center justify-center text-[10px] font-bold text-slate-400 group-hover:bg-blue-900/30 group-hover:text-blue-400 transition-all border border-white/5">
                        {addr.numero || '•'}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-semibold text-slate-200 truncate group-hover:text-white">{addr.rue}</div>
                        <div className="flex items-center gap-2 mt-0.5">
                          <div className="text-[10px] text-slate-500 font-medium">{addr.code_postal} Paris</div>
                          {addr.type && (
                            <span className="text-[8px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 font-bold uppercase border border-white/5">
                              {addr.type}
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="flex flex-col items-end gap-1">
                         {addr.statut && (
                           <span className={`text-[8px] font-black uppercase tracking-tighter ${
                             addr.statut === 'Vente' ? 'text-blue-400' : 
                             addr.statut === 'Location' ? 'text-emerald-400' : 'text-amber-400'
                           }`}>
                             {addr.statut}
                           </span>
                         )}
                         <Navigation className="w-3.5 h-3.5 text-slate-600 group-hover:text-blue-400 transition-all" />
                      </div>
                    </button>
                  ))
                ) : (
                  <div className="text-center py-8 border border-dashed border-white/5 rounded-xl">
                    <p className="text-slate-500 text-xs font-medium">Aucune donnée adresse</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {activeTab === 'list' ? (
              <div className="space-y-4">
                <div className="relative group">
                  <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                  <input
                    type="text"
                    placeholder="Chercher un quartier..."
                    className="w-full bg-slate-800/50 border border-white/10 rounded-xl pl-10 pr-4 py-3 text-sm font-medium text-white focus:outline-none focus:border-white/20 transition-all"
                    value={searchTerm}
                    onChange={e => setSearchTerm(e.target.value)}
                  />
                </div>
                <div className="space-y-1">
                  {searchResults.length > 0 ? (
                    searchResults.map((result, idx) => (
                      <button
                        key={`${result.type}-${result.name}-${idx}`}
                        onClick={() => onQuartierSelect(result.name)}
                        className="w-full flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-white/5 transition-all text-left group"
                      >
                        <div className={`p-2 rounded-lg ${result.type === 'Quartier' ? 'bg-blue-500/10 text-blue-400' : 'bg-amber-500/10 text-amber-400'}`}>
                          {result.type === 'Quartier' ? <Building2 className="w-4 h-4" /> : <MapPin className="w-4 h-4" />}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-semibold text-slate-200 group-hover:text-white truncate">
                            {result.name}
                          </div>
                          {result.type === 'Rue' && (
                            <div className="text-[10px] text-slate-500 truncate">{result.full}</div>
                          )}
                        </div>
                      </button>
                    ))
                  ) : (
                    <div className="px-4 py-8 text-center">
                      <div className="text-slate-500 text-sm">Aucun résultat pour "{searchTerm}"</div>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="space-y-6 pt-2">
                <div className="bg-slate-800/50 p-5 rounded-2xl border border-white/10">
                  <h3 className="text-sm font-bold text-white mb-1 flex items-center gap-2">
                    <Trophy className="w-4 h-4 text-yellow-500" /> Analyse Comparée
                  </h3>
                  <p className="text-[11px] text-slate-500 font-medium">
                    Sélectionnez un arrondissement pour afficher le classement local des quartiers.
                  </p>
                </div>
                
                <div className="grid grid-cols-4 gap-2">
                  {arrondissements.map(arr => (
                    <button
                      key={arr}
                      onClick={() => onArrondissementSelect(arr)}
                      className={`aspect-square flex flex-col items-center justify-center rounded-xl border font-bold transition-all ${
                        selectedArrondissement === arr && viewMode === 'arrondissement'
                          ? 'bg-white/10 border-white/30 text-white shadow-lg'
                          : 'bg-white/5 border-white/5 text-slate-500 hover:bg-white/10 hover:text-white'
                      }`}
                    >
                      <span className="text-base">{arr}</span>
                      <span className="text-[8px] uppercase">arr.</span>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-white/5 text-center">
        <span className="text-[10px] font-bold text-slate-600 uppercase tracking-widest">Paris Urban Explorer 2026</span>
      </div>
    </div>
  )
}
