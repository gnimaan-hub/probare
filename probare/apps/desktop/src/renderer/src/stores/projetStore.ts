import { create } from 'zustand'

export interface Projet {
  id: string
  nom: string
  client?: string
  nif?: string
  exercice?: string
  seuil_signification?: number
  seuil_planification?: number
  consentement_client: boolean
  consentement_horodatage?: string
  etat_courant: string
  cycles_couverts: string[]
  cree_le?: string
  modifie_le?: string
}

export interface DocumentAnnexe {
  id: string
  projet_id: string
  nom: string
  description?: string
  resume_ia?: string
  points_cles?: string[]
  alertes?: string[]
  ia_analysee: number
  ajoute_le?: string
}

export interface DocumentRequis {
  type: string
  label: string
  requis: boolean
  description: string
  importe: boolean
  nb_fichiers: number
  cycles: string[]
}

export interface Exception {
  id: string
  projet_id: string
  controle_ref?: string
  nep_ref?: string
  severite?: string
  description?: string
  statut: 'ouverte' | 'tranchee'
  decision_humaine?: string
  decideur?: string
  type_resolution?: 'corrigee' | 'sans_incidence' | 'non_corrigee' | null
  montant_incidence?: number | null
  interpretation_llm?: string
  hypotheses?: string[]
  diligences?: string[]
  decision_proposee?: string
  urgence?: 'faible' | 'moyenne' | 'elevee'
  ia_analysee?: number
  fichiers_sources?: string[]
  horodatage?: string
}

export interface ResultatControle {
  id: string
  projet_id: string
  controle_ref: string
  valeur?: number
  statut: 'ok' | 'exception'
  details?: string
  sources: string[]
  calcule_le?: string
}

export interface FichierSource {
  id: string
  projet_id: string
  nom: string
  type?: string
  hash?: string
  importe_le?: string
}

interface ProjetStore {
  projets: Projet[]
  projetActif: Projet | null
  loading: boolean
  error: string | null
  exceptions: Exception[]
  resultats: ResultatControle[]
  fichiers: FichierSource[]
  annexes: DocumentAnnexe[]
  documentsRequis: DocumentRequis[]
  journal: any[]
  apiPort: number
  apiToken: string

  setApiPort: (port: number) => void
  setApiToken: (token: string) => void
  setLoading: (v: boolean) => void
  setError: (e: string | null) => void
  setProjets: (projets: Projet[]) => void
  setProjetActif: (projet: Projet | null) => void
  updateProjetActif: (data: Partial<Projet>) => void
  setExceptions: (exceptions: Exception[]) => void
  setResultats: (resultats: ResultatControle[]) => void
  setFichiers: (fichiers: FichierSource[]) => void
  setAnnexes: (annexes: DocumentAnnexe[]) => void
  setDocumentsRequis: (docs: DocumentRequis[]) => void
  setJournal: (journal: any[]) => void
}

export const useProjetStore = create<ProjetStore>((set) => ({
  projets: [],
  projetActif: null,
  loading: false,
  error: null,
  exceptions: [],
  resultats: [],
  fichiers: [],
  annexes: [],
  documentsRequis: [],
  journal: [],
  apiPort: 8765,
  apiToken: '',

  setApiPort: (port) => set({ apiPort: port }),
  setApiToken: (token) => set({ apiToken: token }),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
  setProjets: (projets) => set({ projets }),
  setProjetActif: (projetActif) => set({ projetActif }),
  updateProjetActif: (data) =>
    set((s) => ({
      projetActif: s.projetActif ? { ...s.projetActif, ...data } : null,
    })),
  setExceptions: (exceptions) => set({ exceptions }),
  setResultats: (resultats) => set({ resultats }),
  setFichiers: (fichiers) => set({ fichiers }),
  setAnnexes: (annexes) => set({ annexes }),
  setDocumentsRequis: (documentsRequis) => set({ documentsRequis }),
  setJournal: (journal) => set({ journal }),
}))
