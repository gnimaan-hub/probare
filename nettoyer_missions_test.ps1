# Supprime les missions de test restees verrouillees par Probare.
# A executer APRES avoir ferme l'application (le moteur garde la base ouverte).
$base = Join-Path $env:USERPROFILE ".probare\projets"
$ids = @(
  'eda4c902-cd5a-47f5-b8c1-5b994d26b6a9'
  'cc34368c-f69e-4d49-a4a5-515621880eb9'
  'e9fd17c6-09f8-4b73-a0b6-895381fb0e1f'
  'ead6d68e-b019-46bc-9192-aa21d472fef7'
  'e3a8a51f-30cc-49cd-9338-3bab15e95324'
  'dc653147-83cd-48ea-88eb-29d9a526c995'
  'f4e081c7-8471-41dc-92f9-223ed5973d7d'
  'd86831d6-e275-4a87-ba83-583b801b22b1'
  'd4c4bbcd-a3a5-40d2-9001-c6c96cd2c0ca'
  'f2aae87a-8474-4952-8a9d-8ad15f837c06'
  'd80dd741-b9a6-4a4f-8816-ee7a0b548fbf'
  'fe29983f-8b6d-4f9e-b2ab-24f73f3c1c4a'
  'f1019ac4-b676-4212-af9f-3198b699fe03'
  'c9909803-3437-4c68-ae31-2594f4db0654'
  'e0c9f27c-e5ea-477f-a17f-c26c9b76c5f1'
  'e649dd43-55b6-45b7-bf55-8d121c3c8203'
  'd6fc1783-215f-4e33-a0bf-000092662e11'
  'e071d088-9fe4-48a5-84fc-c48fc2547901'
)
$ok = 0
foreach ($id in $ids) {
  $dir = Join-Path $base $id
  if (Test-Path $dir) {
    try { Remove-Item -Recurse -Force $dir -ErrorAction Stop; $ok++ }
    catch { Write-Host "Verrouille : $id" }
  }
}
Write-Host "$ok mission(s) de test supprimee(s)."
