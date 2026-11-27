param(
  [string]$Python = ".\.venv\Scripts\python.exe"
)

& $Python -m src.modules.carrito.jobs
if ($LASTEXITCODE -ne 0) {
  throw "No se pudieron liberar las reservas expiradas."
}
