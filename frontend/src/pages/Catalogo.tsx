import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useInfiniteQuery } from '@tanstack/react-query';
import { useVirtualizer } from '@tanstack/react-virtual';
import { buscarCatalogo, ProductoCatalogo } from '../services/catalog';

const PAGE_SIZE = 8;

export const Catalogo: React.FC = () => {
  const [searchInput, setSearchInput] = useState('');
  const [query, setQuery] = useState('');
  const [cart, setCart] = useState<Record<number, number>>({});
  const scrollRef = useRef<HTMLDivElement>(null);

  const catalogQuery = useInfiniteQuery({
    queryKey: ['catalogo', query],
    queryFn: ({ pageParam }) => buscarCatalogo(query, pageParam, PAGE_SIZE),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => (lastPage.has_next ? lastPage.next_cursor : undefined),
  });

  const products = useMemo(
    () => catalogQuery.data?.pages.flatMap((page) => page.items) ?? [],
    [catalogQuery.data],
  );

  const virtualizer = useVirtualizer({
    count: products.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => 330,
    overscan: 3,
    getItemKey: (index) => products[index]?.id ?? index,
  });

  useEffect(() => {
    const visibleItems = virtualizer.getVirtualItems();
    const lastItem = visibleItems[visibleItems.length - 1];
    if (
      lastItem &&
      lastItem.index >= products.length - 3 &&
      catalogQuery.hasNextPage &&
      !catalogQuery.isFetchingNextPage
    ) {
      void catalogQuery.fetchNextPage();
    }
  }, [catalogQuery, products.length, virtualizer]);

  const cartCount = Object.values(cart).reduce((total, value) => total + value, 0);

  const addToCart = (product: ProductoCatalogo) => {
    if (product.stock_disponible < 1) return;
    setCart((current) => ({ ...current, [product.id]: (current[product.id] ?? 0) + 1 }));
  };

  const submitSearch = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setQuery(searchInput.trim());
  };

  return (
    <main style={styles.page}>
      <header style={styles.header}>
        <div>
          <p style={styles.eyebrow}>Botica la Luz</p>
          <h1 style={styles.title}>Catálogo</h1>
        </div>
        <div aria-live="polite" style={styles.cartCounter}>Carrito temporal: {cartCount}</div>
      </header>

      <form onSubmit={submitSearch} style={styles.searchForm} role="search">
        <label htmlFor="catalog-search" style={styles.srOnly}>Buscar productos</label>
        <input
          id="catalog-search"
          name="q"
          value={searchInput}
          onChange={(event) => setSearchInput(event.target.value)}
          placeholder="Buscar por producto o componente"
          style={styles.searchInput}
        />
        <button type="submit" style={styles.searchButton}>Buscar</button>
      </form>

      {catalogQuery.isLoading && <p role="status" style={styles.status}>Cargando catálogo...</p>}
      {catalogQuery.isError && <p role="alert" style={styles.error}>Error al cargar el catálogo: {catalogQuery.error.message}</p>}
      {!catalogQuery.isLoading && !catalogQuery.isError && products.length === 0 && (
        <p role="status" style={styles.status}>No se encontraron productos.</p>
      )}

      {products.length > 0 && (
        <div ref={scrollRef} style={styles.scrollArea} aria-label="Productos del catálogo">
          <div style={{ height: virtualizer.getTotalSize(), position: 'relative' }}>
            {virtualizer.getVirtualItems().map((virtualItem) => {
              const product = products[virtualItem.index];
              return (
                <article
                  key={product.id}
                  style={{
                    ...styles.cardPosition,
                    ...styles.card,
                    height: virtualItem.size,
                    transform: `translateY(${virtualItem.start}px)`,
                  }}
                >
                  <img
                    src={product.imagen_url ?? 'https://placehold.co/640x480?text=Producto'}
                    alt={product.nombre}
                    style={styles.image}
                  />
                  <div style={styles.cardBody}>
                    <h2 style={styles.productName}>{product.nombre}</h2>
                    <p style={styles.components}>{product.componentes}</p>
                    <p style={styles.price}>{product.moneda} {product.precio_regular.toFixed(2)}</p>
                    {product.descuento_porcentaje > 0 && (
                      <span style={styles.offer}>Oferta -{product.descuento_porcentaje}%</span>
                    )}
                    {product.stock_bajo && (
                      <p style={styles.stockWarning}>Últimas unidades disponibles (menos de 6 en stock)</p>
                    )}
                    {product.precios_bajos && <span style={styles.lowPrice}>Precios bajos</span>}
                    {product.requiere_receta && <span style={styles.recipe}>Requiere receta</span>}
                    <button
                      type="button"
                      disabled={product.stock_disponible < 1}
                      onClick={() => addToCart(product)}
                      aria-label={`Agregar ${product.nombre} al carrito`}
                      style={styles.addButton}
                    >
                      Agregar al carrito
                    </button>
                  </div>
                </article>
              );
            })}
          </div>
        </div>
      )}

      {catalogQuery.isFetchingNextPage && <p role="status" style={styles.status}>Cargando más productos...</p>}
    </main>
  );
};

const styles: Record<string, React.CSSProperties> = {
  page: { minHeight: '100vh', background: '#f8fafc', padding: '1rem', fontFamily: 'system-ui, -apple-system, sans-serif' },
  header: { maxWidth: 900, margin: '0 auto 1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'end', gap: '1rem' },
  eyebrow: { margin: 0, color: '#2563eb', fontWeight: 700, letterSpacing: '0.05em', textTransform: 'uppercase', fontSize: '0.75rem' },
  title: { margin: '0.25rem 0 0', color: '#1e293b' },
  cartCounter: { color: '#334155', fontWeight: 600, background: '#dbeafe', padding: '0.5rem 0.75rem', borderRadius: 999 },
  searchForm: { maxWidth: 900, margin: '0 auto 1rem', display: 'flex', gap: '0.5rem' },
  searchInput: { flex: 1, minWidth: 0, padding: '0.75rem', border: '1px solid #cbd5e1', borderRadius: 6, fontSize: '1rem' },
  searchButton: { padding: '0.75rem 1rem', border: 0, borderRadius: 6, background: '#2563eb', color: '#fff', fontWeight: 700 },
  scrollArea: { maxWidth: 900, height: '70vh', margin: '0 auto', overflow: 'auto', borderRadius: 8 },
  cardPosition: { position: 'absolute', top: 0, left: 0, width: '100%', paddingBottom: '0.75rem', boxSizing: 'border-box' },
  card: { display: 'grid', gridTemplateColumns: '120px 1fr', gap: '1rem', alignItems: 'center', margin: '0 0.25rem', background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8, padding: '1rem', boxSizing: 'border-box' },
  cardBody: { minWidth: 0 },
  image: { width: 120, height: 100, objectFit: 'cover', borderRadius: 6, background: '#f1f5f9' },
  productName: { margin: 0, color: '#1e293b', fontSize: '1.1rem' },
  components: { margin: '0.25rem 0', color: '#64748b' },
  price: { margin: '0.25rem 0', color: '#0f172a', fontWeight: 700 },
  offer: { color: '#b45309', fontWeight: 700 },
  stockWarning: { margin: '0.25rem 0', color: '#b91c1c', fontWeight: 600 },
  lowPrice: { color: '#047857', fontWeight: 700 },
  recipe: { color: '#7c3aed', fontWeight: 600 },
  addButton: { marginTop: '0.5rem', padding: '0.6rem 0.85rem', border: 0, borderRadius: 5, background: '#0f766e', color: '#fff', fontWeight: 700 },
  status: { maxWidth: 900, margin: '1rem auto', color: '#475569' },
  error: { maxWidth: 900, margin: '1rem auto', color: '#b91c1c', background: '#fef2f2', padding: '0.75rem', borderRadius: 6 },
  srOnly: { position: 'absolute', width: 1, height: 1, padding: 0, margin: -1, overflow: 'hidden', clip: 'rect(0, 0, 0, 0)', whiteSpace: 'nowrap', border: 0 },
};

export default Catalogo;
