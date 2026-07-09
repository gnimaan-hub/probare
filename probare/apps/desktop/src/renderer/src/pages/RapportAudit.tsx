import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Stamp, Scale, Wand2, CheckCircle, AlertTriangle, RefreshCw, FileText,
  Building2, ArrowDownToLine, ArrowUpFromLine, Sparkles, Lock,
} from 'lucide-react'
import { Header } from '../components/layout/Header'
import { Spinner } from '../components/ui/Spinner'
import { useApi } from '../hooks/useApi'
import { useToast } from '../hooks/useToast'
import { useProjetStore } from '../stores/projetStore'
import { useSyncProjet } from '../hooks/useProjet'
import { normeLabel, formatMontant } from '../lib/utils'

// ─── Helpers ────────────────────────────────────────────────────────────────

const CABINET_KEY = 'probare_cabinet_config'

function loadCabinet(): Record<string, any> {
  try {
    const raw = localStorage.getItem(CABINET_KEY)
    if (raw) return JSON.parse(raw)
  } catch { /* ignore */ }
  return {}
}

function saveBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

const RIGUEURS = [
  {
    id: 'stricte', label: 'Stricte',
    desc: "Très exigeante. Validation quasi parfaite exigée ; réserve à la moindre anomalie significative non corrigée.",
  },
  {
    id: 'moderee', label: 'Modérée',
    desc: "Équilibrée (pratique courante). Tolère les anomalies mineures et moyennes si l'essentiel des contrôles est concluant et le cumul reste sous le seuil.",
  },
  {
    id: 'permissive', label: 'Permissive',
    desc: "Conciliante. Privilégie une opinion favorable ; les irrégularités mineures sont traitées en recommandations, sauf dépassement franc du seuil.",
  },
] as const

const TYPE_OPINION_OPTIONS = [
  { id: 'sans_reserve', label: 'Opinion sans réserve' },
  { id: 'avec_reserve', label: 'Opinion avec réserve' },
  { id: 'defavorable', label: 'Opinion défavorable' },
  { id: 'impossibilite', label: "Impossibilité d'exprimer une opinion" },
]

function typeOpinionStyle(t: string): string {
  switch (t) {
    case 'sans_reserve': return 'bg-emerald-50 border-emerald-200 text-emerald-700'
    case 'avec_reserve': return 'bg-amber-50 border-amber-200 text-amber-700'
    case 'defavorable':
    case 'impossibilite': return 'bg-red-50 border-red-200 text-red-700'
    default: return 'bg-slate-50 border-slate-200 text-slate-600'
  }
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export function RapportAudit() {
  const { projetId } = useParams<{ projetId: string }>()
  const navigate = useNavigate()
  const { get, put, post, downloadBlob } = useApi()
  const toast = useToast()
  const { projetActif } = useProjetStore()
  useSyncProjet()

  const [synthese, setSynthese] = useState<any>(null)
  const [opinion, setOpinion] = useState<any>(null)
  const [rigueur, setRigueur] = useState<string>('moderee')
  const [loading, setLoading] = useState(true)
  const [proposing, setProposing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [validating, setValidating] = useState(false)
  const [exporting, setExporting] = useState<'' | 'rapport' | 'memo'>('')

  const cabinet = loadCabinet()
  const cabinetPret = Boolean(cabinet.nom && cabinet.responsable_nom)

  const loadData = async () => {
    if (!projetId) return
    try {
      const [s, o] = await Promise.all([
        get(`/projets/${projetId}/synthese-mission`),
        get(`/projets/${projetId}/opinion`),
      ])
      setSynthese(s)
      if (o.opinion) {
        setOpinion(o.opinion)
        if (o.opinion.rigueur) setRigueur(o.opinion.rigueur)
      }
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadData() }, [projetId])

  const handleProposer = async () => {
    if (!projetId) return
    setProposing(true)
    try {
      const { opinion: op } = await post(`/projets/${projetId}/opinion/proposer`, { rigueur })
      setOpinion(op)
      toast.success("Opinion proposée par l'IA (Opus). Relisez et validez ou corrigez.")
      loadData()
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setProposing(false)
    }
  }

  const patchOpinion = (field: string, value: any) =>
    setOpinion((o: any) => ({ ...o, [field]: value }))

  const persist = async (extra: Record<string, any> = {}) => {
    const payload = {
      type_opinion: opinion.type_opinion,
      titre: opinion.titre,
      texte_opinion: opinion.texte_opinion,
      fondement: opinion.fondement,
      observations: opinion.observations,
      ...extra,
    }
    const { opinion: op } = await put(`/projets/${projetId}/opinion`, payload)
    setOpinion(op)
    return op
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      await persist({ validee: false })
      toast.success('Opinion enregistrée (brouillon).')
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setSaving(false)
    }
  }

  const handleValider = async () => {
    setValidating(true)
    try {
      await persist({ validee: true, validee_par: cabinet.responsable_nom || 'Auditeur responsable' })
      toast.success('Opinion validée. Les livrables finaux peuvent être générés.')
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setValidating(false)
    }
  }

  const handleExport = async (kind: 'rapport' | 'memo') => {
    if (!projetId) return
    setExporting(kind)
    try {
      const path = kind === 'rapport'
        ? `/projets/${projetId}/exporter-rapport-audit`
        : `/projets/${projetId}/exporter-memorandum`
      const { blob, filename } = await downloadBlob(path, 'POST', { cabinet })
      saveBlob(blob, filename)
      toast.success(kind === 'rapport' ? "Rapport d'audit généré." : 'Mémorandum généré.')
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setExporting('')
    }
  }

  if (loading) {
    return (
      <div className="flex flex-col h-full">
        <Header title="Rapport d'audit" subtitle={`${normeLabel('700')} — Opinion & livrables finaux`} />
        <div className="flex-1 flex items-center justify-center"><Spinner /></div>
      </div>
    )
  }

  const anomalies = synthese?.anomalies || {}
  const opinionValidee = Boolean(opinion?.validee)

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Rapport d'audit"
        subtitle={`${normeLabel('700')} — Synthèse de mission, opinion & livrables finaux`}
        actions={
          <button onClick={loadData} className="btn-ghost"><RefreshCw className="w-4 h-4" /></button>
        }
      />

      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-4xl mx-auto space-y-5">

          {/* ── 1. Récapitulatif de la mission ─────────────────────────────── */}
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="card p-5">
            <h2 className="font-semibold text-slate-900 mb-1">Récapitulatif de la mission</h2>
            <p className="text-xs text-slate-500 mb-4">
              Vue d'ensemble du travail accompli à chaque phase — pour vérifier et mesurer la mission
              avant de conclure. {synthese?.projet?.referentiel_comptable_label} · Référentiel d'audit {synthese?.projet?.referentiel_audit}.
            </p>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {(synthese?.phases || []).map((ph: any) => (
                <div key={ph.id} className="bg-slate-50 rounded-xl p-3">
                  <div className="text-xs font-semibold text-slate-700 mb-1.5">{ph.label}</div>
                  <div className="space-y-0.5">
                    {Object.entries(ph.indicateurs || {}).map(([k, v]) => (
                      <div key={k} className="flex justify-between gap-2 text-[11px]">
                        <span className="text-slate-500 truncate">{k}</span>
                        <span className="text-slate-800 font-medium text-right whitespace-nowrap">{String(v ?? '—')}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>

            {/* Bandeau anomalies / seuil */}
            <div className={`mt-4 flex items-start gap-3 p-3 rounded-xl border ${
              anomalies.depasse_seuil_signification
                ? 'bg-red-50 border-red-200' : 'bg-emerald-50 border-emerald-200'
            }`}>
              {anomalies.depasse_seuil_signification
                ? <AlertTriangle className="w-5 h-5 text-red-500 flex-shrink-0" />
                : <CheckCircle className="w-5 h-5 text-emerald-600 flex-shrink-0" />}
              <div className="text-xs">
                <div className="font-semibold text-slate-800">
                  Cumul des anomalies non corrigées : {formatMontant(anomalies.cumul_non_corrigees)}
                  {anomalies.seuil_signification
                    ? ` / seuil ${formatMontant(anomalies.seuil_signification)}` : ' (seuil non défini)'}
                </div>
                <div className="text-slate-600 mt-0.5">
                  {anomalies.depasse_seuil_signification
                    ? `${normeLabel('450')} : le cumul DÉPASSE le seuil de signification — une réserve est à envisager.`
                    : `${normeLabel('450')} : le cumul reste sous le seuil de signification.`}
                  {typeof anomalies.nb_ouvertes === 'number' && anomalies.nb_ouvertes > 0 &&
                    ` · ${anomalies.nb_ouvertes} exception(s) encore ouverte(s).`}
                </div>
              </div>
            </div>
          </motion.div>

          {/* ── 2. Fichiers de la mission ──────────────────────────────────── */}
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.04 }} className="card p-5">
            <h2 className="font-semibold text-slate-900 mb-3">Fichiers de la mission</h2>
            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-600 mb-2">
                  <ArrowDownToLine className="w-3.5 h-3.5" /> Ingérés ({synthese?.fichiers?.['ingérés']?.length || 0})
                </div>
                <div className="space-y-1">
                  {(synthese?.fichiers?.['ingérés'] || []).map((f: any, i: number) => (
                    <div key={i} className="flex items-center justify-between gap-2 text-[11px] bg-slate-50 rounded px-2 py-1">
                      <span className="truncate text-slate-700">{f.nom}</span>
                      <span className="text-slate-400 whitespace-nowrap">{f.categorie}</span>
                    </div>
                  ))}
                  {(synthese?.fichiers?.['ingérés']?.length || 0) === 0 &&
                    <p className="text-[11px] text-slate-400">Aucun fichier ingéré.</p>}
                </div>
              </div>
              <div>
                <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-600 mb-2">
                  <ArrowUpFromLine className="w-3.5 h-3.5" /> Produits ({synthese?.fichiers?.produits?.length || 0})
                </div>
                <div className="space-y-1">
                  {(synthese?.fichiers?.produits || []).map((f: any, i: number) => (
                    <div key={i} className="flex items-center justify-between gap-2 text-[11px] bg-slate-50 rounded px-2 py-1">
                      <span className="truncate text-slate-700">{f.nom}</span>
                      <span className="text-slate-400 whitespace-nowrap">{f.detail}</span>
                    </div>
                  ))}
                  {(synthese?.fichiers?.produits?.length || 0) === 0 &&
                    <p className="text-[11px] text-slate-400">Aucun livrable produit pour l'instant.</p>}
                </div>
              </div>
            </div>
          </motion.div>

          {/* ── 3. Rigueur de l'opinion ────────────────────────────────────── */}
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.08 }} className="card p-5">
            <div className="flex items-center gap-2 mb-1">
              <Scale className="w-4 h-4 text-primary-600" />
              <h2 className="font-semibold text-slate-900">Rigueur de l'opinion</h2>
            </div>
            <p className="text-xs text-slate-500 mb-4">
              Choisissez le niveau d'exigence que l'IA appliquera pour transformer les constats en opinion.
              Le verrou {normeLabel('450')} (dépassement du seuil) reste appliqué quelle que soit la rigueur.
            </p>

            <div className="grid md:grid-cols-3 gap-3">
              {RIGUEURS.map((r) => (
                <button
                  key={r.id}
                  type="button"
                  onClick={() => setRigueur(r.id)}
                  className={`p-3 rounded-xl border-2 text-left transition-all ${
                    rigueur === r.id ? 'border-primary-500 bg-primary-50' : 'border-border hover:border-slate-300'
                  }`}
                >
                  <div className="text-sm font-semibold text-slate-800">{r.label}</div>
                  <div className="text-[11px] text-slate-500 mt-1 leading-relaxed">{r.desc}</div>
                </button>
              ))}
            </div>

            <button
              onClick={handleProposer}
              disabled={proposing}
              className="btn-primary mt-4 w-full justify-center py-2.5"
            >
              {proposing ? <Spinner size="sm" /> : <Wand2 className="w-4 h-4" />}
              {opinion ? "Reproposer l'opinion (IA Opus)" : "Proposer l'opinion (IA Opus)"}
            </button>
          </motion.div>

          {/* ── 4. Opinion proposée ────────────────────────────────────────── */}
          {opinion && (
            <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="card p-5">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-primary-600" />
                  <h2 className="font-semibold text-slate-900">Opinion proposée</h2>
                </div>
                {opinionValidee
                  ? <span className="flex items-center gap-1 text-xs text-emerald-600 font-medium"><CheckCircle className="w-3.5 h-3.5" /> Validée</span>
                  : <span className="flex items-center gap-1 text-xs text-amber-600 font-medium"><AlertTriangle className="w-3.5 h-3.5" /> À valider</span>}
              </div>

              {opinion.justification && (
                <div className="text-[11px] text-slate-500 italic bg-slate-50 rounded-lg p-2.5 mb-3">
                  Justification IA ({opinion.modele_ia || 'Opus'}) : {opinion.justification}
                </div>
              )}

              <div className="space-y-3">
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Type d'opinion</label>
                  <div className="flex flex-wrap gap-2">
                    {TYPE_OPINION_OPTIONS.map((t) => (
                      <button
                        key={t.id}
                        type="button"
                        onClick={() => patchOpinion('type_opinion', t.id)}
                        className={`text-xs px-2.5 py-1.5 rounded-lg border transition-all ${
                          opinion.type_opinion === t.id
                            ? typeOpinionStyle(t.id) + ' font-semibold'
                            : 'bg-white border-border text-slate-500 hover:border-slate-300'
                        }`}
                      >
                        {t.label}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Intitulé</label>
                  <input
                    className="input-field text-sm"
                    value={opinion.titre || ''}
                    onChange={(e) => patchOpinion('titre', e.target.value)}
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Paragraphe d'opinion</label>
                  <textarea
                    className="input-field text-sm min-h-[140px] leading-relaxed"
                    value={opinion.texte_opinion || ''}
                    onChange={(e) => patchOpinion('texte_opinion', e.target.value)}
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Fondement de l'opinion</label>
                  <textarea
                    className="input-field text-sm min-h-[90px] leading-relaxed"
                    value={opinion.fondement || ''}
                    onChange={(e) => patchOpinion('fondement', e.target.value)}
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">
                    Observation / incertitude (facultatif)
                  </label>
                  <textarea
                    className="input-field text-sm min-h-[60px] leading-relaxed"
                    placeholder="Continuité d'exploitation, événements postérieurs… — laisser vide si sans objet."
                    value={opinion.observations || ''}
                    onChange={(e) => patchOpinion('observations', e.target.value)}
                  />
                </div>
              </div>

              <div className="flex gap-2 mt-4">
                <button onClick={handleSave} disabled={saving} className="btn-secondary text-sm">
                  {saving ? <Spinner size="sm" /> : <FileText className="w-4 h-4" />}
                  Enregistrer le brouillon
                </button>
                <button onClick={handleValider} disabled={validating} className="btn-primary text-sm">
                  {validating ? <Spinner size="sm" /> : <CheckCircle className="w-4 h-4" />}
                  {opinionValidee ? "Revalider l'opinion" : "Valider l'opinion"}
                </button>
              </div>
              <p className="text-[11px] text-slate-400 mt-2">
                L'opinion et la signature relèvent de votre responsabilité exclusive. Probare ne signe pas.
              </p>
            </motion.div>
          )}

          {/* ── 5. Livrables finaux ────────────────────────────────────────── */}
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.12 }} className="card p-5">
            <h2 className="font-semibold text-slate-900 mb-1">Livrables finaux</h2>
            <p className="text-xs text-slate-500 mb-3">
              Générés une fois l'opinion validée. Le rapport reprend l'identité du cabinet
              (onglet <button onClick={() => navigate('/configuration')} className="text-primary-600 underline">Cabinet</button>).
            </p>

            {!cabinetPret && (
              <div className="flex items-start gap-2 p-3 mb-3 bg-amber-50 border border-amber-200 rounded-lg">
                <Building2 className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" />
                <p className="text-xs text-amber-700">
                  L'identité du cabinet (nom + responsable signataire) est incomplète. Renseignez-la dans
                  l'onglet <button onClick={() => navigate('/configuration')} className="underline font-medium">Cabinet</button> pour
                  un en-tête et une signature complets sur le rapport.
                </p>
              </div>
            )}

            {!opinionValidee && (
              <div className="flex items-center gap-2 p-3 mb-3 bg-slate-50 border border-border rounded-lg">
                <Lock className="w-4 h-4 text-slate-400" />
                <p className="text-xs text-slate-500">Validez l'opinion ci-dessus pour débloquer la génération.</p>
              </div>
            )}

            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => handleExport('rapport')}
                disabled={exporting !== '' || !opinionValidee}
                className="btn-primary justify-center py-3"
              >
                {exporting === 'rapport' ? <Spinner size="sm" /> : <Stamp className="w-5 h-5" />}
                <div className="text-left">
                  <div className="text-sm font-semibold">Rapport d'audit</div>
                  <div className="text-xs opacity-75">Format .docx — {normeLabel('700')}</div>
                </div>
              </button>

              <button
                onClick={() => handleExport('memo')}
                disabled={exporting !== '' || !opinionValidee}
                className="btn-secondary justify-center py-3"
              >
                {exporting === 'memo' ? <Spinner size="sm" /> : <FileText className="w-5 h-5" />}
                <div className="text-left">
                  <div className="text-sm font-semibold">Mémorandum sur le contrôle des comptes</div>
                  <div className="text-xs opacity-75">Format .docx — par cycle</div>
                </div>
              </button>
            </div>
          </motion.div>

        </div>
      </div>
    </div>
  )
}
