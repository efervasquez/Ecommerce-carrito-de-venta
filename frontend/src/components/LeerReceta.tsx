import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { useAuthStore } from '../store/useAuthStore';
import {
  confirmarJob,
  Faltante,
  getJob,
  ItemSugerido,
  JobEstado,
  OcrApiError,
  subirReceta,
} from '../services/ocr';

const MSG_ERROR = 'No se pudo procesar la receta. Intenta nuevamente';
const MSG_LOGIN = 'Inicia sesión para leer tu receta médica.';
const POLL_MS = 1500;
const MAX_INTENTOS = 15;

export const LeerReceta: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const token = useAuthStore((state) => state.accessToken);
  const inputRef = useRef<HTMLInputElement>(null);
  const [jobId, setJobId] = useState<number | null>(null);
  const [procesando, setProcesando] = useState(false);
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [faltantes, setFaltantes] = useState<Faltante[]>([]);
  const [sugeridos, setSugeridos] = useState<ItemSugerido[]>([]);
  const [modal, setModal] = useState(false);

  useEffect(() => {
    if (jobId === null) return;
    let cancelado = false;
    const aplicar = (estado: JobEstado) => {
      if (estado.estado === 'completado') {
        queryClient.invalidateQueries({ queryKey: ['carrito'] });
        setMensaje(null);
        navigate('/carrito');
      } else if (estado.estado === 'requiere_validacion') {
        setSugeridos(estado.items_sugeridos ?? []);
        setMensaje(estado.mensaje ?? MSG_ERROR);
        setModal(true);
      } else if (estado.estado === 'sin_stock') {
        setFaltantes(estado.faltantes ?? []);
        setMensaje(estado.mensaje ?? MSG_ERROR);
      } else {
        setMensaje(estado.mensaje ?? MSG_ERROR);
      }
      setProcesando(false);
    };
    (async () => {
      for (let intento = 0; intento < MAX_INTENTOS && !cancelado; intento += 1) {
        await new Promise((resolve) => setTimeout(resolve, POLL_MS));
        if (cancelado) return;
        try {
          const estado = await getJob(jobId);
          if (estado.estado !== 'procesando') {
            aplicar(estado);
            return;
          }
        } catch (error) {
          if (!cancelado) {
            setMensaje(error instanceof Error ? error.message : MSG_ERROR);
            setProcesando(false);
          }
          return;
        }
      }
      if (!cancelado) {
        setMensaje(MSG_ERROR);
        setProcesando(false);
      }
    })();
    return () => {
      cancelado = true;
    };
  }, [jobId, navigate, queryClient]);

  const subir = async (archivo: File | undefined) => {
    if (!archivo) return;
    setMensaje(null);
    setFaltantes([]);
    setProcesando(true);
    try {
      const job = await subirReceta(archivo);
      setJobId(job.job_id);
    } catch (error) {
      setProcesando(false);
      setMensaje(error instanceof Error ? error.message : MSG_ERROR);
    }
  };

  const confirmar = async () => {
    if (jobId === null) return;
    try {
      const estado = await confirmarJob(
        jobId,
        sugeridos.map((item) => ({
          producto_id: Number(item.producto_id),
          cantidad: Number(item.cantidad),
        })),
      );
      setModal(false);
      queryClient.invalidateQueries({ queryKey: ['carrito'] });
      navigate('/carrito');
      if (estado.estado === 'sin_stock') {
        setFaltantes(estado.faltantes ?? []);
        setMensaje(estado.mensaje ?? MSG_ERROR);
      }
    } catch (error) {
      if (error instanceof OcrApiError && error.body?.estado === 'sin_stock') {
        setModal(false);
        setFaltantes(error.body.faltantes ?? []);
        setMensaje(error.body.mensaje ?? MSG_ERROR);
      } else {
        setMensaje(error instanceof Error ? error.message : MSG_ERROR);
      }
    }
  };

  return (
    <section aria-label="Leer receta">
      <h2>Leer receta</h2>
      {!token && (
        <p>
          {MSG_LOGIN} <Link to="/login">Iniciar sesión</Link>
        </p>
      )}
      <input
        ref={inputRef}
        type="file"
        accept=".jpg,.jpeg,.png,.pdf"
        aria-label="Archivo de receta"
        onChange={(event) => subir(event.target.files?.[0])}
      />
      <button type="button" onClick={() => inputRef.current?.click()} disabled={procesando}>
        Leer receta
      </button>
      {procesando && <p role="status">Procesando receta...</p>}
      {mensaje && <p role="alert">{mensaje}</p>}
      {faltantes.length > 0 && (
        <ul>
          {faltantes.map((faltante) => (
            <li key={faltante.nombre}>
              {faltante.nombre}: solicitado {faltante.solicitado}, disponible {faltante.disponible}
            </li>
          ))}
        </ul>
      )}
      {modal && (
        <div role="dialog" aria-label="Validación asistida">
          <h3>Revisa los medicamentos de tu receta</h3>
          {sugeridos.map((item, indice) => (
            <div key={`${item.texto}-${indice}`}>
              <span>{item.texto}</span>
              <input
                aria-label={`Producto ${indice}`}
                type="number"
                value={item.producto_id ?? 0}
                onChange={(event) => {
                  const copia = [...sugeridos];
                  copia[indice] = { ...item, producto_id: Number(event.target.value) };
                  setSugeridos(copia);
                }}
              />
              <input
                aria-label={`Cantidad ${indice}`}
                type="number"
                min="1"
                value={item.cantidad}
                onChange={(event) => {
                  const copia = [...sugeridos];
                  copia[indice] = { ...item, cantidad: Number(event.target.value) };
                  setSugeridos(copia);
                }}
              />
            </div>
          ))}
          <button type="button" onClick={confirmar}>Confirmar receta</button>
        </div>
      )}
    </section>
  );
};

export default LeerReceta;
