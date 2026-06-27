import { X, Trophy, ChevronRight, AlertCircle, Info, Shield, Banknote, Home, Building, Scale, Leaf } from 'lucide-react'
import { RankingResponse, KPICategory, KPI_CATEGORIES } from '../../services/apiService'

interface ArrondissementRankingProps {
  arrondissement: number
  rankingData: RankingResponse | null
  selectedCategories: KPICategory[]
  isLoading: boolean
  onClose: () => void
  onQuartierClick: (name: string) => void
}

const getCategoryMiniIcon = (key: string) => {
  switch (key) {
    case 'confort': return <Leaf className="w-3 h-3" />
    case 'surete': return <Shield className="w-3 h-3" />
    case 'prix_m2': return <Banknote className="w-3 h-3" />
    case 'loyers': return <Home className="w-3 h-3" />
    case 'logements_sociaux': return <Building className="w-3 h-3" />
    case 'comparaison': return <Scale className="w-3 h-3" />
    default: return null
  }
}

export default function ArrondissementRanking({
  arrondissement,
  rankingData,
  selectedCategories,
  isLoading,
  onClose,
  onQuartierClick
}: ArrondissementRankingProps) {
  
  return (
    <div className="flex-1 flex flex-col bg-slate-900 border border-white/5 rounded-2xl shadow-xl overflow-hidden animate-in fade-in duration-300">
      {/* Header */}
      <div className="p-6 border-b border-white/5">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest border border-white/10 px-2 py-0.5 rounded">
                Palmarès Local
              </span>
            </div>
            <h2 className="text-2xl font-bold text-white tracking-tight">{arrondissement}e Arrondissement</h2>
            <p className="text-[10px] text-slate-500 font-bold uppercase tracking-widest mt-1">Basé sur {selectedCategories.length} indicateurs</p>
          </div>
          <button 
            onClick={onClose}
            className="p-1.5 hover:bg-white/5 rounded-lg text-slate-500 hover:text-white transition-all"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Info Bar */}
      <div className="px-6 py-3 bg-white/5 flex items-center gap-3">
        <Info className="w-3.5 h-3.5 text-slate-500" />
        <p className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">
          Classement par score composite (0-100)
        </p>
      </div>

      {/* Arrondissement KPI Averages */}
      {!isLoading && rankingData && rankingData.ranking.length > 0 && (
        <div className="px-6 py-4 border-b border-white/5 bg-slate-800/20">
          <h3 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-3">
            Moyennes de l'Arrondissement
          </h3>
          <div className="grid grid-cols-3 gap-2">
            {selectedCategories.map(catKey => {
               const validScores = rankingData.ranking
                 .map(q => q.scores[catKey])
                 .filter(s => s !== null && s !== undefined) as number[];
               const avg = validScores.length > 0 
                 ? validScores.reduce((a,b)=>a+b, 0) / validScores.length 
                 : null;
               
               const label = KPI_CATEGORIES.find(c => c.key === catKey)?.label || catKey;
               
               return (
                 <div key={catKey} className="bg-slate-900/50 border border-white/5 p-2 rounded-xl flex flex-col items-center justify-center text-center">
                    <div className="flex items-center gap-1.5 text-slate-400 mb-1">
                      {getCategoryMiniIcon(catKey)}
                    </div>
                    <span className="text-[12px] font-black text-white">{avg !== null ? Math.round(avg) : '--'}</span>
                    <span className="text-[8px] font-bold text-slate-500 uppercase tracking-tighter mt-1 leading-tight">{label}</span>
                 </div>
               )
            })}
          </div>
        </div>
      )}

      {/* Ranking List */}
      <div className="flex-1 overflow-y-auto px-6 pb-6 custom-scrollbar mt-4">
        {isLoading ? (
          <div className="space-y-2 py-2">
            {[1, 2, 3, 4, 5].map(i => (
              <div key={i} className="h-16 bg-white/5 rounded-xl animate-pulse"></div>
            ))}
          </div>
        ) : rankingData && rankingData.ranking.length > 0 ? (
          <div className="space-y-1.5 py-2">
            {rankingData.ranking.map((q, idx) => {
              return (
                <button
                  key={q.code_insee}
                  onClick={() => onQuartierClick(q.nom_quartier)}
                  className="w-full text-left group relative bg-white/5 border border-transparent rounded-xl p-4 hover:bg-white/10 hover:border-white/10 transition-all"
                >
                  <div className="flex items-center gap-4">
                    {/* Rank Badge */}
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center font-bold text-sm ${
                      idx === 0 ? 'bg-slate-200 text-slate-900' :
                      idx === 1 ? 'bg-slate-400 text-slate-900' :
                      idx === 2 ? 'bg-slate-600 text-white' :
                      'bg-slate-800 text-slate-500'
                    }`}>
                      {idx + 1}
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between mb-1">
                        <h4 className="text-sm font-bold text-slate-200 truncate">{q.nom_quartier}</h4>
                        <div className="text-sm font-bold text-white">{Math.round(q.composite_score)}</div>
                      </div>
                      
                      {/* Micro Icons */}
                      <div className="flex gap-3">
                        {selectedCategories.slice(0, 3).map(catKey => (
                          <div key={catKey} className="flex items-center gap-1.5 opacity-40">
                            {getCategoryMiniIcon(catKey)}
                            <span className="text-[9px] font-bold text-slate-400">
                              {q.scores[catKey] ? Math.round(q.scores[catKey] as number) : '--'}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                    
                    <ChevronRight className="w-4 h-4 text-slate-700 group-hover:text-white transition-all" />
                  </div>
                </button>
              )
            })}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <AlertCircle className="w-8 h-8 text-slate-800 mb-2" />
            <p className="text-slate-600 text-xs font-medium">Aucun résultat disponible</p>
          </div>
        )}
      </div>

      {/* Footer Winner */}
      {rankingData && rankingData.ranking.length > 0 && (
        <div className="p-4 bg-white/5 border-t border-white/5 flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-slate-800 flex items-center justify-center border border-white/10">
            <Trophy className="w-4 h-4 text-slate-400" />
          </div>
          <div>
            <div className="text-[9px] font-bold text-slate-500 uppercase tracking-widest">N°1 du Classement</div>
            <div className="text-xs font-bold text-white">{rankingData.ranking[0].nom_quartier}</div>
          </div>
        </div>
      )}
    </div>
  )
}
