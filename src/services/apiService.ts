/**
 * API Service — backend-first client for MongoDB + MySQL data.
 *
 * Expected backend endpoints:
 * - GET /api/quartiers/geojson
 * - GET /api/arrondissements/geojson
 * - GET /api/quartiers/lookup?lat=...&lon=...
 * - GET /api/search/address?q=...
 * - GET /api/quartiers/{codeInsee}/addresses
 * - GET /api/kpi/quartier/{codeInsee}?categories=...&annee=...
 * - GET /api/ranking/arrondissement/{arrNum}?categories=...
 * - GET /api/quartiers/choropleth?category=...
 */

import * as turf from '@turf/turf'
import type { Feature, FeatureCollection, Polygon, MultiPolygon } from 'geojson'

// ─── GeoJSON Feature Properties ──────────────────────────────────────────────

export interface QuartierGeoProperties {
  n_sq_qu: string
  c_qu: string
  c_quinsee: string
  l_qu: string
  c_ar: number
  n_sq_ar: string
  perimetre: number
  surface: number
  geom_x_y: { lon: number; lat: number }
  st_area_shape: number
  st_perimeter_shape: number
}

export interface ArrondissementGeoProperties {
  arrondissement?: number
  nom_arrondissement?: string
  nom_officiel_arrondissement?: string
  numero_arrondissement_insee?: string
  surface?: number
  perimetre?: number
}

// ─── Domain Types ────────────────────────────────────────────────────────────

export interface Quartier {
  code_insee: string
  nom_quartier: string
  arrondissement: number
  code_quartier: string
  surface: number
  perimetre: number
  lat: number
  lon: number
}

export interface Arrondissement {
  arrondissement: number
  nb_quartiers: number
  quartiers: string[]
}

export interface KPIConfort {
  arrondissement: number
  code_insee_quartier: number
  nom_quartier: string
  surface_quartier_m2: number
  part_surface: number
  incidents_estime: number
  travaux_estime: number
  gares_estime: number
  risque_incidents_100: number
  score_confort_urbain_100: number
}

export interface KPISurete {
  annee: number
  arrondissement: number
  code_insee_quartier: number
  score_surete_quartier_moyen_100: number
  score_risque_quartier_moyen_100: number
  score_surete_iris_min_100: number
  score_surete_iris_max_100: number
  score_surete_iris_std_100: number
  score_risque_iris_min_100: number
  score_risque_iris_max_100: number
  score_risque_iris_std_100: number
  nb_iris_rattaches: number
  codes_iris_rattaches: string
  noms_iris_rattaches: string
  dist_commissariat_km_moyenne: number
  nb_cameras_arrondissement: number
}

export interface KPIPrixM2 {
  annee: number
  arrondissement: number
  code_insee_quartier: number
  prix_m2_median: number
  prix_m2_moyen: number
  nb_ventes: number
  nb_ventes_estime: number
  surface_quartier_m2: number
  part_surface: number
}

export interface KPILoyers {
  annee: number
  arrondissement: number
  code_insee_quartier: number
  loyer_reference_median: number
  loyer_reference_moyen: number
  nb_observations: number
  loyer_reference_majore_median: number
  loyer_reference_minore_median: number
  nombre_pieces_median: number
  nom_quartier: string
  type_location_mode: string
  epoque_construction_mode: string
}

export interface KPILogementsSociaux {
  arrondissement: number
  annee: number
  code_insee_quartier: number
  nom_quartier: string
  logements_finances_total: number
  logements_finances_moyen: number
  nb_programmes: number
  nb_bailleurs: number
  nb_pla_i_total: number
  nb_plus_total: number
  nb_plus_cd_total: number
  nb_pls_total: number
  latitude_moyenne: number
  longitude_moyenne: number
}

export interface KPIComparaison {
  annee: number
  arrondissement: number
  code_insee_quartier: number
  prix_m2_median: number
  prix_m2_moyen: number
  nb_transactions: number
  loyer_reference_median: number
  loyer_reference_moyen: number
  nb_observations: number
  kpi_comparaison_achat_location: number
  surface_quartier_m2: number
  part_surface: number
  nb_transactions_estime: number
  nb_observations_estime: number
}

export interface QuartierKPIResponse {
  quartier: Quartier | null
  kpis: {
    confort?: KPIConfort
    surete?: KPISurete
    surete_historique?: KPISurete[]
    prix_m2?: KPIPrixM2
    prix_m2_historique?: KPIPrixM2[]
    loyers?: KPILoyers
    loyers_historique?: KPILoyers[]
    logements_sociaux?: KPILogementsSociaux
    logements_sociaux_historique?: KPILogementsSociaux[]
    comparaison?: KPIComparaison
    comparaison_historique?: KPIComparaison[]
  }
  categories_requested: string[]
}

export interface RankedQuartier {
  code_insee: string
  nom_quartier: string
  arrondissement: number
  scores: Record<string, number | null>
  composite_score: number
  rank: number
}

export interface RankingResponse {
  arrondissement: number
  categories: string[]
  ranking: RankedQuartier[]
}

export type KPICategory = 'confort' | 'surete' | 'prix_m2' | 'loyers' | 'logements_sociaux' | 'comparaison'

export const KPI_CATEGORIES: { key: KPICategory; label: string; icon: string; description: string }[] = [
  { key: 'confort', label: 'Confort Urbain', icon: 'confort', description: 'Gares, espaces verts et nuisances' },
  { key: 'surete', label: 'Sûreté', icon: 'surete', description: 'Indices de sécurité et incidents' },
  { key: 'prix_m2', label: 'Prix au m²', icon: 'prix', description: 'Prix médians de vente immobilière' },
  { key: 'loyers', label: 'Encadrement Loyers', icon: 'loyer', description: 'Loyers de référence par m²' },
  { key: 'logements_sociaux', label: 'Logements Sociaux', icon: 'social', description: 'Part de logements sociaux' },
  { key: 'comparaison', label: 'Comparaison', icon: 'compare', description: 'Analyse comparative locale' },
]

export interface Address {
  numero: string
  rue: string
  code_postal: string
  lat: number
  lon: number
  full: string
  type?: string
  statut?: string
}

// ─── Backend helpers ─────────────────────────────────────────────────────────

type QuartiersFeatureCollection = FeatureCollection<Polygon | MultiPolygon, QuartierGeoProperties>
type ArrondissementsFeatureCollection = FeatureCollection<Polygon | MultiPolygon, ArrondissementGeoProperties>

const EMPTY_QUARTIERS: QuartiersFeatureCollection = {
  type: 'FeatureCollection',
  features: [],
}

const EMPTY_ARRONDISSEMENTS: ArrondissementsFeatureCollection = {
  type: 'FeatureCollection',
  features: [],
}

const API_BASE_URL = import.meta.env.VITE_API_URL?.replace(/\/$/, '') ?? ''

function buildApiUrl(path: string): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${API_BASE_URL}${normalizedPath}`
}

async function apiFetchJson<T>(path: string): Promise<T | null> {
  try {
    const response = await fetch(buildApiUrl(path))
    if (!response.ok) return null
    return (await response.json()) as T
  } catch {
    return null
  }
}

function normalizeQuartiersGeoJSON(payload: unknown): QuartiersFeatureCollection | null {
  if (!payload || typeof payload !== 'object') return null

  const objectPayload = payload as {
    type?: string
    features?: Array<Feature<Polygon | MultiPolygon, QuartierGeoProperties> | Feature<any, Record<string, unknown>>>
  }

  if (objectPayload.type === 'FeatureCollection' && Array.isArray(objectPayload.features)) {
    const features = objectPayload.features.map(feature => {
      const properties = (feature.properties ?? {}) as Record<string, unknown>
      const geometry = feature.geometry as unknown as { type?: string; coordinates?: unknown }
      const pointCoordinates = geometry?.type === 'Point' && Array.isArray(geometry.coordinates)
        ? (geometry.coordinates as number[])
        : null

      const lon = typeof pointCoordinates?.[0] === 'number' ? pointCoordinates[0] : undefined
      const lat = typeof pointCoordinates?.[1] === 'number' ? pointCoordinates[1] : undefined

      return {
        ...feature,
        properties: {
          ...properties,
          c_ar: properties.c_ar ?? properties.arrondissement,
          c_quinsee: properties.c_quinsee ?? properties.code_insee_quartier ?? properties.code_insee,
          l_qu: properties.l_qu ?? properties.nom_quartier ?? properties.name,
          c_qu: properties.c_qu ?? properties.code_quartier_id ?? properties.code_quartier,
          surface: properties.surface ?? properties.surface_quartier_m2,
          perimetre: properties.perimetre ?? properties.st_perimeter_shape,
          geom_x_y: properties.geom_x_y ?? (lon !== undefined && lat !== undefined ? { lon, lat } : undefined),
        },
      }
    })

    return {
      type: 'FeatureCollection',
      features: features as QuartiersFeatureCollection['features'],
    }
  }
  return null
}

function normalizeArrondissementsGeoJSON(payload: unknown): ArrondissementsFeatureCollection | null {
  if (!payload || typeof payload !== 'object') return null

  const objectPayload = payload as {
    type?: string
    features?: Array<Feature<Polygon | MultiPolygon, ArrondissementGeoProperties> | Feature<any, Record<string, unknown>>>
  }

  if (objectPayload.type === 'FeatureCollection' && Array.isArray(objectPayload.features)) {
    const features = objectPayload.features.map(feature => {
      const properties = (feature.properties ?? {}) as Record<string, unknown>

      return {
        ...feature,
        properties: {
          ...properties,
          arrondissement: properties.arrondissement ?? properties['numero_d’arrondissement'] ?? properties['numero_d_arrondissement'] ?? properties['numero_d_arrondissement_insee'],
          nom_arrondissement: properties.nom_arrondissement ?? properties['nom_de_l’arrondissement'] ?? properties['nom_de_l_arrondissement'] ?? properties['nom_officiel_de_l’arrondissement'] ?? properties['nom_officiel_de_l_arrondissement'] ?? properties.name,
          nom_officiel_arrondissement: properties.nom_officiel_arrondissement ?? properties['nom_officiel_de_l’arrondissement'] ?? properties['nom_officiel_de_l_arrondissement'],
          numero_arrondissement_insee: properties.numero_arrondissement_insee ?? properties['numero_d’arrondissement_insee'] ?? properties['numero_d_arrondissement_insee'],
          surface: properties.surface,
          perimetre: properties.perimetre,
        },
      }
    })

    return {
      type: 'FeatureCollection',
      features: features as ArrondissementsFeatureCollection['features'],
    }
  }

  return null
}

function readQuartierCoordinates(feature: Feature<Polygon | MultiPolygon, QuartierGeoProperties>): { lon: number; lat: number } {
  const properties = feature.properties as unknown as Record<string, unknown> | undefined
  const geomXy = properties?.geom_x_y as { lon?: unknown; lat?: unknown } | undefined

  if (geomXy && typeof geomXy.lon === 'number' && typeof geomXy.lat === 'number') {
    return { lon: geomXy.lon, lat: geomXy.lat }
  }

  const geometry = feature.geometry as unknown as { type?: string; coordinates?: unknown }
  if (geometry?.type === 'Point' && Array.isArray(geometry.coordinates)) {
    const [lon, lat] = geometry.coordinates as number[]
    if (typeof lon === 'number' && typeof lat === 'number') {
      return { lon, lat }
    }
  }

  return { lon: 0, lat: 0 }
}

function readQuartierField<T>(
  feature: Feature<Polygon | MultiPolygon, QuartierGeoProperties>,
  keys: string[],
  fallback: T
): T {
  const properties = feature.properties as unknown as Record<string, unknown> | undefined
  if (!properties) return fallback

  for (const key of keys) {
    const value = properties[key]
    if (typeof value === 'number' || typeof value === 'string') {
      return value as unknown as T
    }
  }

  return fallback
}

function quartierToDomain(feature: Feature<Polygon | MultiPolygon, QuartierGeoProperties>): Quartier {
  return {
    code_insee: String(readQuartierField(feature, ['c_quinsee', 'code_insee_quartier', 'code_insee'], '')),
    nom_quartier: String(readQuartierField(feature, ['l_qu', 'nom_quartier', 'name'], '')),
    arrondissement: Number(readQuartierField(feature, ['c_ar', 'arrondissement'], 0)),
    code_quartier: String(readQuartierField(feature, ['c_qu', 'code_quartier_id', 'code_quartier'], '')),
    surface: Number(readQuartierField(feature, ['surface', 'surface_quartier_m2'], 0)),
    perimetre: Number(readQuartierField(feature, ['perimetre', 'st_perimeter_shape'], 0)),
    ...readQuartierCoordinates(feature),
  }
}

async function loadQuartiersGeoJSON(): Promise<QuartiersFeatureCollection> {
  const remote = await apiFetchJson<unknown>('/api/quartiers/geojson')
  if (normalizeQuartiersGeoJSON(remote)) {
    return normalizeQuartiersGeoJSON(remote) as QuartiersFeatureCollection
  }

  try {
    const localResponse = await fetch('/data/exports/nosql/quartiers.geojson')
    if (localResponse.ok) {
      const localPayload = await localResponse.json()
      const normalizedLocal = normalizeQuartiersGeoJSON(localPayload)
      if (normalizedLocal) return normalizedLocal
    }
  } catch {
    // Ignore local asset fallback failures.
  }

  return EMPTY_QUARTIERS
}

async function loadArrondissementsGeoJSON(): Promise<ArrondissementsFeatureCollection> {
  const remote = await apiFetchJson<unknown>('/api/arrondissements/geojson')
  if (normalizeArrondissementsGeoJSON(remote)) {
    return normalizeArrondissementsGeoJSON(remote) as ArrondissementsFeatureCollection
  }

  try {
    const localResponse = await fetch('/data/exports/nosql/arrondissements.geojson')
    if (localResponse.ok) {
      const localPayload = await localResponse.json()
      const normalizedLocal = normalizeArrondissementsGeoJSON(localPayload)
      if (normalizedLocal) return normalizedLocal
    }
  } catch {
    // Ignore local asset fallback failures.
  }

  return EMPTY_ARRONDISSEMENTS
}

// ─── API calls ───────────────────────────────────────────────────────────────

export async function fetchQuartiersGeoJSON(): Promise<QuartiersFeatureCollection> {
  return loadQuartiersGeoJSON()
}

export async function fetchArrondissementsGeoJSON(): Promise<ArrondissementsFeatureCollection> {
  return loadArrondissementsGeoJSON()
}

export async function fetchQuartiers(): Promise<Quartier[]> {
  const geojson = await loadQuartiersGeoJSON()
  return geojson.features.map(quartierToDomain)
}

export async function fetchArrondissements(): Promise<Arrondissement[]> {
  const quartiers = await fetchQuartiers()
  return Array.from({ length: 20 }, (_, i) => i + 1).map(num => {
    const arrQuartiers = quartiers.filter(q => q.arrondissement === num)
    return {
      arrondissement: num,
      nb_quartiers: arrQuartiers.length,
      quartiers: arrQuartiers.map(q => q.nom_quartier),
    }
  })
}

export async function findQuartierByName(name: string): Promise<Quartier | null> {
  const q = name.toLowerCase().trim()
  if (!q) return null

  const quartiers = await fetchQuartiers()
  return (
    quartiers.find(quartier => quartier.nom_quartier.toLowerCase() === q) ||
    quartiers.find(quartier => quartier.nom_quartier.toLowerCase().includes(q)) ||
    null
  )
}

export async function searchAddress(query: string): Promise<Address[]> {
  const q = query.toLowerCase().trim()
  if (!q) return []

  const remote = await apiFetchJson<Address[]>(`/api/search/address?q=${encodeURIComponent(query)}`)
  if (remote && remote.length > 0) return remote

  const quartiers = await fetchQuartiers()
  const quartierMatches = quartiers
    .filter(quartier => quartier.nom_quartier.toLowerCase().includes(q) || String(quartier.arrondissement) === q)
    .map(quartier => ({
      numero: '',
      rue: quartier.nom_quartier,
      code_postal: `75${String(quartier.arrondissement).padStart(2, '0')}`,
      lat: quartier.lat,
      lon: quartier.lon,
      full: `${quartier.nom_quartier}, Paris`,
      type: 'Quartier' as const,
    }))

  return quartierMatches.slice(0, 20)
}

export async function lookupQuartier(lat: number, lon: number): Promise<Quartier> {
  const remote = await apiFetchJson<Quartier>(
    `/api/quartiers/lookup?lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lon)}`
  )
  if (remote) return remote

  const point = turf.point([lon, lat])
  const geojson = await loadQuartiersGeoJSON()

  for (const feature of geojson.features) {
    if (turf.booleanPointInPolygon(point, feature)) {
      return quartierToDomain(feature)
    }
  }

  const quartiers = await fetchQuartiers()
  const fallback = quartiers.sort((a, b) => {
    const distA = Math.pow(a.lat - lat, 2) + Math.pow(a.lon - lon, 2)
    const distB = Math.pow(b.lat - lat, 2) + Math.pow(b.lon - lon, 2)
    return distA - distB
  })[0]

  if (!fallback) {
    throw new Error('Unable to resolve quartier from coordinates')
  }

  return fallback
}

export async function fetchQuartierAddresses(codeInsee: string): Promise<Address[]> {
  const remote = await apiFetchJson<Address[]>(`/api/quartiers/${encodeURIComponent(codeInsee)}/addresses`)
  if (remote && remote.length > 0) return remote

  return []
}

export async function fetchQuartierKPIs(
  codeInsee: string,
  categories: KPICategory[],
  annee: number = 2023
): Promise<QuartierKPIResponse | null> {
  const remote = await apiFetchJson<QuartierKPIResponse>(
    `/api/kpi/quartier/${encodeURIComponent(codeInsee)}?categories=${encodeURIComponent(categories.join(','))}&annee=${encodeURIComponent(annee)}`
  )
  if (remote) return remote

  // API not available; return null instead of empty fallback
  return null
}

export async function fetchArrondissementRanking(
  arrNum: number,
  categories: KPICategory[]
): Promise<RankingResponse> {
  const remote = await apiFetchJson<RankingResponse>(
    `/api/ranking/arrondissement/${encodeURIComponent(arrNum)}?categories=${encodeURIComponent(categories.join(','))}`
  )
  if (remote) return remote

  return { arrondissement: arrNum, categories, ranking: [] }
}

export async function fetchChoroplethScores(category: KPICategory): Promise<Record<string, number>> {
  const remote = await apiFetchJson<Record<string, number>>(
    `/api/quartiers/choropleth?category=${encodeURIComponent(category)}`
  )
  return remote || {}
}

// Backward-compatible helper, kept for callers that still expect a sync function.
export function getChoroplethScores(): Record<string, number> {
  return {}
}
