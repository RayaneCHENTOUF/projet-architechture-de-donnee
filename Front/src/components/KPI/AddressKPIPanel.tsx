import { X, MapPin } from 'lucide-react'
import { X, MapPin } from 'lucide-react'
import type { Address, QuartierKPIResponse, KPICategory } from '@/services/apiService'
import KPIDisplay from './KPIDisplay'
import type { SelectedQuartier } from '@/App'

interface AddressKPIPanelProps {
  address: Address
  quartierName: string
  quartier: SelectedQuartier
  kpiData: QuartierKPIResponse | null
  selectedCategories: KPICategory[]
  onClose: () => void
}

export default function AddressKPIPanel({
  address,
  quartierName,
  quartier,
  kpiData,
  selectedCategories,
  onClose
}: AddressKPIPanelProps) {
  return (
    <div className="absolute bottom-0 right-0 top-0 w-96 bg-slate-950 border-l border-slate-800 shadow-2xl z-30 flex flex-col pointer-events-auto overflow-hidden">
      {/* Header */}
      <div className="px-6 py-5 bg-slate-900/80 border-b border-slate-800 flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <MapPin className="w-4 h-4 text-blue-400 flex-shrink-0" />
            <span className="text-xs uppercase tracking-wider text-blue-400 font-semibold">Adresse sélectionnée</span>
          </div>
          <h2 className="text-lg font-bold text-white truncate">{address.numero} {address.rue}</h2>
          <p className="text-sm text-slate-400 mt-1">{quartierName}</p>
        </div>
        <button
          onClick={onClose}
          className="p-2 bg-slate-800 hover:bg-slate-700 rounded-lg text-slate-400 hover:text-white transition-colors flex-shrink-0 ml-2"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto custom-scrollbar px-6 py-6">
        <KPIDisplay
          quartier={quartier}
          kpiData={kpiData}
          selectedCategories={selectedCategories}
          isLoading={false}
          onClose={onClose}
        />
      </div>

      {/* Footer info */}
      <div className="px-6 py-4 border-t border-slate-800 bg-slate-900/40">
        <p className="text-xs text-slate-500">Les KPI affichés correspondent aux données du quartier</p>
      </div>
    </div>
  )
}
