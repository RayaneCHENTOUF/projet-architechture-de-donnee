/**
 * API Service — Client-side service using local JSON data
 * Fully typed, no `any` casts.
 */

import * as turf from '@turf/turf'
import type { Feature, Polygon, MultiPolygon } from 'geojson'

import quartiersGeoJSON from '../data/paris-quartiers.json'
import confortKPI from '../data/kpi/confort_urbain.json'
import sureteKPI from '../data/kpi/surete.json'
import prixM2KPI from '../data/kpi/prix_m2.json'
import loyersKPI from '../data/kpi/loyers.json'
import socialKPI from '../data/kpi/logements_sociaux.json'
import comparaisonKPI from '../data/kpi/comparaison_immobilier.json'

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

// ─── Typed JSON casts ────────────────────────────────────────────────────────

const confortData = confortKPI as KPIConfort[]
const sureteData = sureteKPI as KPISurete[]
const prixM2Data = prixM2KPI as KPIPrixM2[]
const loyersData = loyersKPI as KPILoyers[]
const socialData = socialKPI as KPILogementsSociaux[]
const comparaisonData = comparaisonKPI as KPIComparaison[]

interface ParisGeoJSON {
  type: string
  features: Feature<Polygon | MultiPolygon, QuartierGeoProperties>[]
}
const parisData = quartiersGeoJSON as unknown as ParisGeoJSON

// ─── Utility ─────────────────────────────────────────────────────────────────

const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms))

// ─── API calls ───────────────────────────────────────────────────────────────

export async function fetchQuartiers(): Promise<Quartier[]> {
  await delay(100)
  return parisData.features.map(f => ({
    code_insee: f.properties.c_quinsee,
    nom_quartier: f.properties.l_qu,
    arrondissement: f.properties.c_ar,
    code_quartier: f.properties.c_qu,
    surface: f.properties.surface,
    perimetre: f.properties.perimetre,
    lat: f.properties.geom_x_y.lat,
    lon: f.properties.geom_x_y.lon,
  }))
}

export async function fetchArrondissements(): Promise<Arrondissement[]> {
  await delay(100)
  const quartiers = await fetchQuartiers()
  return Array.from({ length: 20 }, (_, i) => i + 1).map(num => {
    const arrQuartiers = quartiers.filter(q => q.arrondissement === num)
    return {
      arrondissement: num,
      nb_quartiers: arrQuartiers.length,
      quartiers: arrQuartiers.map(q => q.nom_quartier)
    }
  })
}

// ─── Address Search (Purely Local) ───────────────────────────────────────────

import { generateMockAddresses, RUES_PAR_ARRONDISSEMENT } from '../data/mock-addresses'

export async function searchAddress(query: string): Promise<Address[]> {
  await delay(150)
  const q = query.toLowerCase().trim()
  if (!q) return []

  const results: Address[] = []
  const quartiers = await fetchQuartiers()

  // 1. Search in Quartier names
  const matchingQuartiers = quartiers.filter(quartier => 
    quartier.nom_quartier.toLowerCase().includes(q)
  )

  matchingQuartiers.forEach(quartier => {
    results.push({
      numero: '',
      rue: quartier.nom_quartier,
      code_postal: `750${String(quartier.arrondissement).padStart(2, '0')}`,
      lat: quartier.lat,
      lon: quartier.lon,
      full: `${quartier.nom_quartier}, Paris`,
      type: 'Quartier'
    })
  })

  // 2. Search in Streets data
  for (const [arr, rues] of Object.entries(RUES_PAR_ARRONDISSEMENT)) {
    const arrNum = parseInt(arr)
    const matchingRues = rues.filter(rue => rue.toLowerCase().includes(q))
    
    matchingRues.forEach(rue => {
      // Find a quartier in this arrondissement to get a base lat/lon
      const representativeQuartier = quartiers.find(quartier => quartier.arrondissement === arrNum)
      if (representativeQuartier) {
        results.push({
          numero: '1',
          rue: rue,
          code_postal: `750${String(arrNum).padStart(2, '0')}`,
          lat: representativeQuartier.lat,
          lon: representativeQuartier.lon,
          full: `${rue}, 750${String(arrNum).padStart(2, '0')} Paris`,
          type: 'Rue'
        })
      }
    })
  }

  return results.slice(0, 10)
}

// ─── Point-in-Polygon quartier lookup (Turf.js) ─────────────────────────────

export async function lookupQuartier(lat: number, lon: number): Promise<Quartier> {
  await delay(50)
  const point = turf.point([lon, lat])

  for (const feature of parisData.features) {
    if (turf.booleanPointInPolygon(point, feature)) {
      const p = feature.properties
      return {
        code_insee: p.c_quinsee,
        nom_quartier: p.l_qu,
        arrondissement: p.c_ar,
        code_quartier: p.c_qu,
        surface: p.surface,
        perimetre: p.perimetre,
        lat: p.geom_x_y.lat,
        lon: p.geom_x_y.lon,
      }
    }
  }

  // Fallback: closest centroid (edge case — point just outside Paris borders)
  const quartiers = await fetchQuartiers()
  return quartiers.sort((a, b) => {
    const distA = Math.pow(a.lat - lat, 2) + Math.pow(a.lon - lon, 2)
    const distB = Math.pow(b.lat - lat, 2) + Math.pow(b.lon - lon, 2)
    return distA - distB
  })[0]
}

// ─── Quartier Addresses (mock) ───────────────────────────────────────────────

import { generateMockAddresses } from '../data/mock-addresses'

export async function fetchQuartierAddresses(codeInsee: string): Promise<Address[]> {
  await delay(200)
  const quartiers = await fetchQuartiers()
  const quartier = quartiers.find(q => q.code_insee === codeInsee)
  if (!quartier) return []

  const arrStr = String(quartier.arrondissement).padStart(2, '0')
  const codePostal = `750${arrStr}`.slice(-5)
  const mockDetails = generateMockAddresses(quartier.nom_quartier)

  return mockDetails.map(d => ({
    numero: d.numero,
    rue: d.rue,
    code_postal: codePostal,
    lat: quartier.lat + (Math.random() - 0.5) * 0.005,
    lon: quartier.lon + (Math.random() - 0.5) * 0.005,
    full: `${d.numero} ${d.rue}, ${codePostal} Paris`,
    type: d.type,
    statut: d.statut,
  }))
}

// ─── KPI Fetch ───────────────────────────────────────────────────────────────

export async function fetchQuartierKPIs(
  codeInsee: string,
  categories: KPICategory[],
  annee: number = 2023
): Promise<QuartierKPIResponse> {
  await delay(200)
  const quartiers = await fetchQuartiers()
  const quartier = quartiers.find(q => q.code_insee === codeInsee) || null
  const insee = parseInt(codeInsee)

  const response: QuartierKPIResponse = {
    quartier,
    kpis: {},
    categories_requested: categories,
  }

  if (categories.includes('confort')) {
    response.kpis.confort = confortData.find(k => k.code_insee_quartier === insee)
  }
  if (categories.includes('surete')) {
    const data = sureteData.filter(k => k.code_insee_quartier === insee)
    response.kpis.surete = data.find(k => k.annee === annee) || data[data.length - 1]
    response.kpis.surete_historique = [...data].sort((a, b) => a.annee - b.annee)
  }
  if (categories.includes('prix_m2')) {
    const data = prixM2Data.filter(k => k.code_insee_quartier === insee)
    response.kpis.prix_m2 = data.find(k => k.annee === annee) || data[data.length - 1]
    response.kpis.prix_m2_historique = [...data].sort((a, b) => a.annee - b.annee)
  }
  if (categories.includes('loyers')) {
    const data = loyersData.filter(k => k.code_insee_quartier === insee)
    response.kpis.loyers = data.find(k => k.annee === annee) || data[data.length - 1]
    response.kpis.loyers_historique = [...data].sort((a, b) => a.annee - b.annee)
  }
  if (categories.includes('logements_sociaux')) {
    const data = socialData.filter(k => k.code_insee_quartier === insee)
    response.kpis.logements_sociaux = data.find(k => k.annee === annee) || data[data.length - 1]
    response.kpis.logements_sociaux_historique = [...data].sort((a, b) => a.annee - b.annee)
  }
  if (categories.includes('comparaison')) {
    const data = comparaisonData.filter(k => k.code_insee_quartier === insee)
    response.kpis.comparaison = data.find(k => k.annee === annee) || data[data.length - 1]
    response.kpis.comparaison_historique = [...data].sort((a, b) => a.annee - b.annee)
  }

  return response
}

// ─── Arrondissement Ranking (ALL categories) ─────────────────────────────────

export async function fetchArrondissementRanking(
  arrNum: number,
  categories: KPICategory[]
): Promise<RankingResponse> {
  await delay(300)
  const quartiers = await fetchQuartiers()
  const arrQuartiers = quartiers.filter(q => q.arrondissement === arrNum)

  const ranking: RankedQuartier[] = arrQuartiers.map(q => {
    const insee = parseInt(q.code_insee)
    const scores: Record<string, number | null> = {}
    let totalScore = 0
    let count = 0

    if (categories.includes('confort')) {
      const val = confortData.find(k => k.code_insee_quartier === insee)?.score_confort_urbain_100 ?? null
      scores.confort = val
      if (val !== null) { totalScore += val; count++ }
    }
    if (categories.includes('surete')) {
      const val = sureteData.find(k => k.code_insee_quartier === insee && k.annee === 2023)?.score_surete_quartier_moyen_100 ?? null
      scores.surete = val
      if (val !== null) { totalScore += val; count++ }
    }
    if (categories.includes('prix_m2')) {
      // Lower price → better score (inverted: 100 - normalized)
      const entry = prixM2Data.find(k => k.code_insee_quartier === insee && k.annee === 2023)
        || prixM2Data.find(k => k.code_insee_quartier === insee)
      const val = entry ? Math.max(0, 100 - (entry.prix_m2_median / 200)) : null
      scores.prix_m2 = val
      if (val !== null) { totalScore += val; count++ }
    }
    if (categories.includes('loyers')) {
      const entry = loyersData.find(k => k.code_insee_quartier === insee && k.annee === 2025)
        || loyersData.find(k => k.code_insee_quartier === insee)
      const val = entry ? Math.max(0, 100 - (entry.loyer_reference_median * 2)) : null
      scores.loyers = val
      if (val !== null) { totalScore += val; count++ }
    }
    if (categories.includes('logements_sociaux')) {
      const entry = socialData.find(k => k.code_insee_quartier === insee)
      const val = entry ? Math.min(100, entry.logements_finances_total / 5) : null
      scores.logements_sociaux = val
      if (val !== null) { totalScore += val; count++ }
    }
    if (categories.includes('comparaison')) {
      const entry = comparaisonData.find(k => k.code_insee_quartier === insee && k.annee === 2023)
        || comparaisonData.find(k => k.code_insee_quartier === insee)
      const val = entry?.kpi_comparaison_achat_location ?? null
      scores.comparaison = val
      if (val !== null) { totalScore += val; count++ }
    }

    return {
      code_insee: q.code_insee,
      nom_quartier: q.nom_quartier,
      arrondissement: q.arrondissement,
      scores,
      composite_score: count > 0 ? totalScore / count : 0,
      rank: 0,
    }
  })

  ranking.sort((a, b) => b.composite_score - a.composite_score)
  ranking.forEach((r, i) => r.rank = i + 1)

  return { arrondissement: arrNum, categories, ranking }
}

// ─── Choropleth score map ────────────────────────────────────────────────────

export function getChoroplethScores(category: KPICategory): Record<string, number> {
  const scores: Record<string, number> = {}

  switch (category) {
    case 'confort':
      confortData.forEach(k => {
        scores[String(k.code_insee_quartier)] = k.score_confort_urbain_100
      })
      break
    case 'surete': {
      // Latest year per quartier
      const latest = new Map<number, KPISurete>()
      sureteData.forEach(k => {
        const prev = latest.get(k.code_insee_quartier)
        if (!prev || k.annee > prev.annee) latest.set(k.code_insee_quartier, k)
      })
      latest.forEach((k, insee) => {
        scores[String(insee)] = k.score_surete_quartier_moyen_100
      })
      break
    }
    case 'prix_m2': {
      const latest = new Map<number, KPIPrixM2>()
      prixM2Data.forEach(k => {
        const prev = latest.get(k.code_insee_quartier)
        if (!prev || k.annee > prev.annee) latest.set(k.code_insee_quartier, k)
      })
      // Normalize: lower price = higher score
      const allPrices = Array.from(latest.values()).map(k => k.prix_m2_median)
      const minP = Math.min(...allPrices)
      const maxP = Math.max(...allPrices)
      const range = maxP - minP || 1
      latest.forEach((k, insee) => {
        scores[String(insee)] = 100 * (1 - (k.prix_m2_median - minP) / range)
      })
      break
    }
    case 'loyers': {
      const latest = new Map<number, KPILoyers>()
      loyersData.forEach(k => {
        const prev = latest.get(k.code_insee_quartier)
        if (!prev || k.annee > prev.annee) latest.set(k.code_insee_quartier, k)
      })
      const allLoyers = Array.from(latest.values()).map(k => k.loyer_reference_median)
      const minL = Math.min(...allLoyers)
      const maxL = Math.max(...allLoyers)
      const rangeL = maxL - minL || 1
      latest.forEach((k, insee) => {
        scores[String(insee)] = 100 * (1 - (k.loyer_reference_median - minL) / rangeL)
      })
      break
    }
    case 'logements_sociaux': {
      const latest = new Map<number, KPILogementsSociaux>()
      socialData.forEach(k => {
        const prev = latest.get(k.code_insee_quartier)
        if (!prev || k.annee > prev.annee) latest.set(k.code_insee_quartier, k)
      })
      const allVals = Array.from(latest.values()).map(k => k.logements_finances_total)
      const maxV = Math.max(...allVals) || 1
      latest.forEach((k, insee) => {
        scores[String(insee)] = 100 * (k.logements_finances_total / maxV)
      })
      break
    }
    case 'comparaison': {
      const latest = new Map<number, KPIComparaison>()
      comparaisonData.forEach(k => {
        const prev = latest.get(k.code_insee_quartier)
        if (!prev || k.annee > prev.annee) latest.set(k.code_insee_quartier, k)
      })
      latest.forEach((k, insee) => {
        scores[String(insee)] = k.kpi_comparaison_achat_location
      })
      break
    }
  }

  return scores
}
