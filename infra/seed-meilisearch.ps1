param(
  [string]$MeilisearchUrl = "http://127.0.0.1:7700",
  [string]$ApiKey = "",
  [string]$Index = "productos",
  [string]$SeedPath = "$PSScriptRoot\catalogo-seed.json"
)

$headers = @{ "Content-Type" = "application/json" }
if ($ApiKey) { $headers["Authorization"] = "Bearer $ApiKey" }

$settings = @{
  searchableAttributes = @("nombre", "componentes")
  filterableAttributes = @("stock_disponible", "descuento_porcentaje", "precios_bajos", "requiere_receta")
  sortableAttributes = @("precio_regular", "stock_disponible")
} | ConvertTo-Json -Depth 5

Invoke-RestMethod -Method Patch -Uri "$MeilisearchUrl/indexes/$Index/settings" -Headers $headers -Body $settings
$documents = Get-Content -Raw -LiteralPath $SeedPath
Invoke-RestMethod -Method Post -Uri "$MeilisearchUrl/indexes/$Index/documents?primaryKey=id" -Headers $headers -Body $documents
Write-Output "Seed enviado a Meilisearch: $Index"
