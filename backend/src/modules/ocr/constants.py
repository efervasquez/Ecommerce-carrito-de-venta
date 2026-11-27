"""Textos exactos del contrato HU-06 (no negociables)."""

FORMATO_MESSAGE = "Formato de archivo no soportado. Usa JPG, PNG o PDF"
TAMANO_MESSAGE = "El archivo supera el tamaño máximo permitido"
SIN_STOCK_TEMPLATE = (
    "Lo sentimos, no contamos con stock disponible de {nombre} "
    "para completar su receta médica"
)
RECETA_BLOCK_MESSAGE = (
    "Debes adjuntar y validar tu receta médica para continuar con el pago"
)
LOW_CONFIDENCE_MESSAGE = (
    "No pudimos leer la receta con suficiente confianza. Revisa y confirma los medicamentos"
)
ERROR_MESSAGE = "No se pudo procesar la receta. Intenta nuevamente"
LOGIN_MESSAGE = "Inicia sesión para leer tu receta médica."

MAX_FILE_BYTES = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "pdf"}
CONFIDENCE_THRESHOLD = 65.0
POLL_INTERVAL_MS = 1500
MAX_POLL_INTENTOS = 15
QUEUE_NAME = "ocr.procesar"
