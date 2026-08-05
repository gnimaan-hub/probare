/**
 * Fiche identité du cabinet — saisie dans la page Configuration, conservée sur
 * le poste. Point d'accès unique : la clé de stockage et la forme des champs
 * étaient dupliquées entre Configuration et RapportAudit, ce qui exposait à ce
 * qu'un renommage de champ n'en corrige qu'une.
 */

export const CABINET_STORAGE_KEY = 'probare_cabinet_config'

export interface CabinetConfig {
  nom: string
  forme_juridique: string
  adresse_rue: string
  adresse_code_postal: string
  adresse_ville: string
  adresse_pays: string
  telephone: string
  email: string
  site_web: string
  numero_agrement: string
  numero_ordre: string
  inscription_cour_appel: string
  responsable_nom: string
  responsable_titre: string
  logo_data_url: string
}

export const CABINET_DEFAUT: CabinetConfig = {
  nom: '',
  forme_juridique: '',
  adresse_rue: '',
  adresse_code_postal: '',
  adresse_ville: '',
  adresse_pays: 'Djibouti',
  telephone: '',
  email: '',
  site_web: '',
  numero_agrement: '',
  numero_ordre: '',
  inscription_cour_appel: '',
  responsable_nom: '',
  responsable_titre: 'Commissaire aux comptes',
  logo_data_url: '',
}

export function loadCabinet(): CabinetConfig {
  try {
    const raw = localStorage.getItem(CABINET_STORAGE_KEY)
    if (raw) return { ...CABINET_DEFAUT, ...JSON.parse(raw) }
  } catch {
    /* stockage illisible : on repart des valeurs par défaut */
  }
  return { ...CABINET_DEFAUT }
}

export function saveCabinet(config: CabinetConfig): void {
  localStorage.setItem(CABINET_STORAGE_KEY, JSON.stringify(config))
}

/**
 * Nom porté à la piste d'audit comme auteur des actions (ISA 230). C'est le
 * responsable signataire de la fiche Cabinet : la personne qui engage le
 * cabinet est celle qui répond des diligences enregistrées.
 *
 * Rend une chaîne vide tant que la fiche n'est pas renseignée — l'en-tête n'est
 * alors pas envoyé et le journal reste sans auteur, ce qui est un état visible
 * (« Auteur non renseigné ») plutôt qu'un nom inventé.
 */
export function acteurCourant(): string {
  const cabinet = loadCabinet()
  const nom = cabinet.responsable_nom.trim()
  if (!nom) return ''
  const titre = cabinet.responsable_titre.trim()
  return titre ? `${nom} (${titre})` : nom
}
