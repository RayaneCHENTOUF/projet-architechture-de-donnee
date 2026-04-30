import { X, Shield, Banknote, Home, Building, Scale, ArrowRight, Leaf, Info, TrendingUp } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import type { QuartierKPIResponse, KPICategory } from '../../services/apiService'
import { KPI_CATEGORIES } from '../../services/apiService'
import type { SelectedQuartier } from '../../App'

interface KPIDisplayProps {
  quartier: SelectedQuartier
  kpiData: QuartierKPIResponse | null
  selectedCategories: KPICategory[]
  isLoading: boolean
  isError: boolean
  onClose: () => void
}

// Mini sparkline for historical data
function MiniChart({ data, dataKey, color }: { data: { annee: number; value: number }[]; dataKey: string; color: string }) {
  if (!data || data.length < 2) return null
  return (
    <div className="mt-3 bg-slate-900/60 rounded-lg p-3 border border-white/5">
      <div className="flex items-center gap-1.5 mb-2">
        <TrendingUp className="w-3 h-3 text-slate-500" />
        <span className="text-[9px] font-bold text-slate-500 uppercase tracking-wider">Évolution {dataKey}</span>
      </div>
      <ResponsiveContainer width="100%" height={80}>
        <LineChart data={data}>
          <XAxis
            dataKey="annee"
            tick={{ fontSize: 9, fill: '#64748b' }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis hide domain={['dataMin - 5', 'dataMax + 5']} />
          <Tooltip
            contentStyle={{
              backgroundColor: '#0f172a',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: '8px',
              fontSize: '11px',
              color: '#e2e8f0'
            }}
            formatter={(v: number) => [Math.round(v * 100) / 100, dataKey]}
            labelFormatter={(l) => `Année ${l}`}
          />
          <Line
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={2}
            dot={{ r: 3, fill: color, strokeWidth: 0 }}
            activeDot={{ r: 5, fill: color }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

export default function KPIDisplay({
  quartier,
  kpiData,
  selectedCategories,
  isLoading,
  isError,
  onClose
}: KPIDisplayProps) {

  const getIcon = (cat: KPICategory) => {
    switch (cat) {
      case 'confort': return <Leaf className="w-5 h-5 text-emerald-400" />
      case 'surete': return <Shield className="w-5 h-5 text-blue-400" />
      case 'prix_m2': return <Banknote className="w-5 h-5 text-amber-400" />
      case 'loyers': return <Home className="w-5 h-5 text-purple-400" />
      case 'logements_sociaux': return <Building className="w-5 h-5 text-cyan-400" />
      case 'comparaison': return <Scale className="w-5 h-5 text-rose-400" />
      default: return <Info className="w-5 h-5 text-slate-400" />
    }
  }

  const getCategoryColor = (cat: KPICategory): string => {
    switch (cat) {
      case 'confort': return '#34d399'
      case 'surete': return '#60a5fa'
      case 'prix_m2': return '#fbbf24'
      case 'loyers': return '#a78bfa'
      case 'logements_sociaux': return '#22d3ee'
      case 'comparaison': return '#fb7185'
      default: return '#94a3b8'
    }
  }

  // Build historical chart data for a category
  const getHistoricalData = (catKey: KPICategory) => {
    if (!kpiData) return null

    switch (catKey) {
      case 'surete':
        return kpiData.kpis.surete_historique?.map(d => ({
          annee: d.annee,
          value: d.score_surete_quartier_moyen_100
        })) || null
      case 'prix_m2':
        return kpiData.kpis.prix_m2_historique?.map(d => ({
          annee: d.annee,
          value: d.prix_m2_median
        })) || null
      case 'loyers':
        return kpiData.kpis.loyers_historique?.map(d => ({
          annee: d.annee,
          value: d.loyer_reference_median
        })) || null
      case 'logements_sociaux':
        return kpiData.kpis.logements_sociaux_historique?.map(d => ({
          annee: d.annee,
          value: d.logements_finances_total
        })) || null
      case 'comparaison':
        return kpiData.kpis.comparaison_historique?.map(d => ({
          annee: d.annee,
          value: d.kpi_comparaison_achat_location
        })) || null
      default:
        return null
    }
  }

  const getHistoricalLabel = (catKey: KPICategory): string => {
    switch (catKey) {
      case 'surete': return 'Score Sûreté'
      case 'prix_m2': return 'Prix m²'
      case 'loyers': return 'Loyer Réf.'
      case 'logements_sociaux': return 'Logements'
      case 'comparaison': return 'Ratio'
      default: return 'Score'
    }
  }

  const handleRapportClick = () => {
    // Generate and download a text summary
    if (!kpiData || !quartier) return
    const lines = [
      `RAPPORT — ${quartier.nom_quartier} (${quartier.arrondissement}e arrondissement)`,
      `Code INSEE: ${quartier.code_insee}`,
      `═══════════════════════════════════════`,
      '',
    ]

    if (kpiData.kpis.confort) {
      lines.push(`🌱 Confort Urbain: ${Math.round(kpiData.kpis.confort.score_confort_urbain_100)}/100`)
      lines.push(`   Gares estimées: ${kpiData.kpis.confort.gares_estime}`)
      lines.push(`   Risque incidents: ${Math.round(kpiData.kpis.confort.risque_incidents_100)}%`)
      lines.push('')
    }
    if (kpiData.kpis.surete) {
      lines.push(`🛡️ Sûreté: ${Math.round(kpiData.kpis.surete.score_surete_quartier_moyen_100)}/100`)
      lines.push(`   Distance commissariat: ${kpiData.kpis.surete.dist_commissariat_km_moyenne} km`)
      lines.push('')
    }
    if (kpiData.kpis.prix_m2) {
      lines.push(`💶 Prix m²: ${Math.round(kpiData.kpis.prix_m2.prix_m2_median).toLocaleString()} €`)
      lines.push(`   Ventes estimées: ${kpiData.kpis.prix_m2.nb_ventes_estime}`)
      lines.push('')
    }
    if (kpiData.kpis.loyers) {
      lines.push(`🏠 Loyer réf.: ${kpiData.kpis.loyers.loyer_reference_median} €/m²`)
      lines.push('')
    }

    const blob = new Blob([lines.join('\n')], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `rapport_${quartier.nom_quartier.replace(/\s+/g, '_')}.txt`
    a.click()
    URL.revokeObjectURL(url)
  }

  // Calculate a dynamic composite score based on Paris-wide empirical boundaries
  const calculateIndiceGlobal = () => {
    if (!kpiData) return 0
    let totalScore = 0
    let count = 0
    
    selectedCategories.forEach(cat => {
      if (cat === 'confort' && kpiData.kpis.confort) {
        totalScore += kpiData.kpis.confort.score_confort_urbain_100
        count++
      } else if (cat === 'surete' && kpiData.kpis.surete) {
        totalScore += kpiData.kpis.surete.score_surete_quartier_moyen_100
        count++
      } else if (cat === 'prix_m2' && kpiData.kpis.prix_m2) {
        const val = kpiData.kpis.prix_m2.prix_m2_median
        // Paris boundaries: ~7000€ to ~16000€. Lower is better.
        let score = 100 - ((val - 7000) / (16000 - 7000) * 100)
        totalScore += Math.max(0, Math.min(100, score))
        count++
      } else if (cat === 'loyers' && kpiData.kpis.loyers) {
        const val = kpiData.kpis.loyers.loyer_reference_median
        // Paris boundaries: ~20€ to ~40€. Lower is better.
        let score = 100 - ((val - 20) / (40 - 20) * 100)
        totalScore += Math.max(0, Math.min(100, score))
        count++
      } else if (cat === 'logements_sociaux' && kpiData.kpis.logements_sociaux) {
        const val = kpiData.kpis.logements_sociaux.logements_finances_total
        // Boundaries: 0 to ~3000
        let score = (val / 3000) * 100
        totalScore += Math.max(0, Math.min(100, score))
        count++
      } else if (cat === 'comparaison' && kpiData.kpis.comparaison) {
        const val = kpiData.kpis.comparaison.kpi_comparaison_achat_location
        // Boundaries: ~15 to ~30
        let score = ((val - 15) / (30 - 15)) * 100
        totalScore += Math.max(0, Math.min(100, score))
        count++
      }
    })
    return count > 0 ? totalScore / count : 0
  }

  return (
    <div className="flex-1 flex flex-col bg-slate-900 border border-white/5 rounded-2xl shadow-xl overflow-hidden animate-in fade-in duration-300">
      {/* Header */}
      <div className="p-6 border-b border-white/5">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest border border-white/10 px-2 py-0.5 rounded">
                {quartier.arrondissement}e ARR.
              </span>
            </div>
            <h2 className="text-2xl font-bold text-white tracking-tight">{quartier.nom_quartier}</h2>
            <div className="text-[10px] text-slate-500 font-bold tracking-widest uppercase mt-1">Données Officielles • {quartier.code_insee}</div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 hover:bg-white/5 rounded-lg text-slate-500 hover:text-white transition-all"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-y-auto px-6 pb-6 custom-scrollbar">
        {isLoading ? (
          <div className="space-y-4 py-6">
            {[1, 2, 3].map(i => (
              <div key={i} className="h-28 bg-white/5 rounded-xl animate-pulse"></div>
            ))}
          </div>
        ) : isError ? (
          <div className="flex flex-col items-center justify-center py-24 text-center">
            <div className="w-12 h-12 bg-red-500/10 rounded-full flex items-center justify-center mb-3">
              <Info className="w-8 h-8 text-red-500" />
            </div>
            <p className="text-red-400 text-sm font-bold mb-1">API indisponible</p>
            <p className="text-slate-500 text-xs font-medium">Les données KPI ne sont pas accessibles.
            Vérifiez que le backend est en cours d'exécution.</p>
          </div>
        ) : kpiData ? (
          <div className="space-y-4 py-6">
            {selectedCategories.map(catKey => {
              const catInfo = KPI_CATEGORIES.find(c => c.key === catKey)
              const historicalData = getHistoricalData(catKey)
              const color = getCategoryColor(catKey)

              return (
                <div
                  key={catKey}
                  className="bg-slate-800/40 border border-white/5 rounded-xl p-5 hover:border-white/10 transition-all"
                >
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-lg bg-slate-800 flex items-center justify-center border border-white/5">
                        {getIcon(catKey)}
                      </div>
                      <div>
                        <h4 className="text-sm font-bold text-white">{catInfo?.label}</h4>
                        <p className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider">Mise à jour 2024</p>
                      </div>
                    </div>

                    {/* Score Value */}
                    {catKey === 'confort' && kpiData.kpis.confort && (
                      <div className="text-right">
                        <div className="text-2xl font-bold text-white">
                          {Math.round(kpiData.kpis.confort.score_confort_urbain_100)}
                          <span className="text-xs text-slate-500 ml-1">/100</span>
                        </div>
                      </div>
                    )}
                    {catKey === 'surete' && kpiData.kpis.surete && (
                      <div className="text-right">
                        <div className="text-2xl font-bold text-white">
                          {Math.round(kpiData.kpis.surete.score_surete_quartier_moyen_100)}
                          <span className="text-xs text-slate-500 ml-1">/100</span>
                        </div>
                      </div>
                    )}
                    {catKey === 'comparaison' && kpiData.kpis.comparaison && (
                      <div className="text-right">
                        <div className="text-2xl font-bold text-white">
                          {Math.round(kpiData.kpis.comparaison.kpi_comparaison_achat_location)}
                          <span className="text-xs text-slate-500 ml-1">/100</span>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Detail Grid */}
                  <div className="grid grid-cols-2 gap-3">
                    {catKey === 'confort' && kpiData.kpis.confort && (
                      <>
                        <div className="bg-slate-900/40 p-3 rounded-lg border border-white/5">
                          <div className="text-[9px] font-bold text-slate-500 uppercase mb-1">Points Gares</div>
                          <div className="text-base font-bold text-slate-200">{Math.round(kpiData.kpis.confort.gares_estime)}</div>
                        </div>
                        <div className="bg-slate-900/40 p-3 rounded-lg border border-white/5">
                          <div className="text-[9px] font-bold text-slate-500 uppercase mb-1">Niveau Risque</div>
                          <div className="text-base font-bold text-slate-200">{Math.round(kpiData.kpis.confort.risque_incidents_100)}%</div>
                        </div>
                      </>
                    )}
                    {catKey === 'surete' && kpiData.kpis.surete && (
                      <>
                        <div className="bg-slate-900/40 p-3 rounded-lg border border-white/5">
                          <div className="text-[9px] font-bold text-slate-500 uppercase mb-1">Dist. Commissariat</div>
                          <div className="text-base font-bold text-slate-200">{kpiData.kpis.surete.dist_commissariat_km_moyenne} km</div>
                        </div>
                        <div className="bg-slate-900/40 p-3 rounded-lg border border-white/5">
                          <div className="text-[9px] font-bold text-slate-500 uppercase mb-1">Caméras (Arr.)</div>
                          <div className="text-base font-bold text-slate-200">{kpiData.kpis.surete.nb_cameras_arrondissement}</div>
                        </div>
                      </>
                    )}
                    {catKey === 'prix_m2' && kpiData.kpis.prix_m2 && (
                      <>
                        <div className="bg-slate-900/40 p-3 rounded-lg border border-white/5">
                          <div className="text-[9px] font-bold text-slate-500 uppercase mb-1">Prix Médian</div>
                          <div className="text-base font-bold text-slate-200">{Math.round(kpiData.kpis.prix_m2.prix_m2_median).toLocaleString()} €</div>
                        </div>
                        <div className="bg-slate-900/40 p-3 rounded-lg border border-white/5">
                          <div className="text-[9px] font-bold text-slate-500 uppercase mb-1">Ventes/An</div>
                          <div className="text-base font-bold text-slate-200">{Math.round(kpiData.kpis.prix_m2.nb_ventes_estime)}</div>
                        </div>
                      </>
                    )}
                    {catKey === 'loyers' && kpiData.kpis.loyers && (
                      <>
                        <div className="bg-slate-900/40 p-3 rounded-lg border border-white/5">
                          <div className="text-[9px] font-bold text-slate-500 uppercase mb-1">Ref. Loyer</div>
                          <div className="text-base font-bold text-slate-200">{Math.round(kpiData.kpis.loyers.loyer_reference_median)} €/m²</div>
                        </div>
                        <div className="bg-slate-900/40 p-3 rounded-lg border border-white/5">
                          <div className="text-[9px] font-bold text-slate-500 uppercase mb-1">Taille Médiane</div>
                          <div className="text-base font-bold text-slate-200">{Math.round(kpiData.kpis.loyers.nombre_pieces_median)} p.</div>
                        </div>
                      </>
                    )}
                    {catKey === 'logements_sociaux' && kpiData.kpis.logements_sociaux && (
                      <>
                        <div className="bg-slate-900/40 p-3 rounded-lg border border-white/5">
                          <div className="text-[9px] font-bold text-slate-500 uppercase mb-1">Logements Financés</div>
                          <div className="text-base font-bold text-slate-200">{kpiData.kpis.logements_sociaux.logements_finances_total}</div>
                        </div>
                        <div className="bg-slate-900/40 p-3 rounded-lg border border-white/5">
                          <div className="text-[9px] font-bold text-slate-500 uppercase mb-1">Programmes</div>
                          <div className="text-base font-bold text-slate-200">{kpiData.kpis.logements_sociaux.nb_programmes}</div>
                        </div>
                      </>
                    )}
                    {catKey === 'comparaison' && kpiData.kpis.comparaison && (
                      <>
                        <div className="bg-slate-900/40 p-3 rounded-lg border border-white/5">
                          <div className="text-[9px] font-bold text-slate-500 uppercase mb-1">Prix m² Médian</div>
                          <div className="text-base font-bold text-slate-200">{Math.round(kpiData.kpis.comparaison.prix_m2_median).toLocaleString()} €</div>
                        </div>
                        <div className="bg-slate-900/40 p-3 rounded-lg border border-white/5">
                          <div className="text-[9px] font-bold text-slate-500 uppercase mb-1">Loyer Réf.</div>
                          <div className="text-base font-bold text-slate-200">{kpiData.kpis.comparaison.loyer_reference_median} €/m²</div>
                        </div>
                      </>
                    )}
                  </div>

                  {/* Historical Chart */}
                  {historicalData && historicalData.length >= 2 && (
                    <MiniChart data={historicalData} dataKey={getHistoricalLabel(catKey)} color={color} />
                  )}
                </div>
              )
            })}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-24 text-center">
            <Info className="w-8 h-8 text-slate-600 mb-3" />
            <p className="text-slate-500 text-sm font-medium">Sélectionnez un quartier</p>
          </div>
        )}
      </div>

      {/* Footer Summary */}
      <div className="p-6 border-t border-white/5 bg-white/5">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Indice Global</div>
            <div className="text-xl font-bold text-white">
              {Math.round(calculateIndiceGlobal())}
              <span className="text-xs text-slate-500 ml-1">/100</span>
            </div>
          </div>
          <button
            onClick={handleRapportClick}
            className="bg-slate-700 hover:bg-slate-600 text-white px-5 py-2 rounded-lg text-xs font-bold transition-all flex items-center gap-2"
          >
            RAPPORT COMPLET <ArrowRight className="w-3 h-3" />
          </button>
        </div>
      </div>
    </div>
  )
}
