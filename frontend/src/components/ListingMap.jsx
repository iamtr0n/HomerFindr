import 'leaflet/dist/leaflet.css'
import '@geoman-io/leaflet-geoman-free/dist/leaflet-geoman.css'
import React, { useEffect } from 'react'
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from 'react-leaflet'

// Inject pulse keyframes once
if (typeof document !== 'undefined' && !document.getElementById('hf-pulse-style')) {
  const style = document.createElement('style')
  style.id = 'hf-pulse-style'
  style.textContent = `
    @keyframes hf-pulse {
      0%   { stroke-width: 2; stroke-opacity: 0.9; r: 14; }
      70%  { stroke-width: 6; stroke-opacity: 0;   r: 22; }
      100% { stroke-width: 2; stroke-opacity: 0;   r: 22; }
    }
    .new-listing-pulse { animation: hf-pulse 1.8s ease-out infinite; }
  `
  document.head.appendChild(style)
}

function markerColor(listing) {
  if (listing.is_gold_star) return '#f59e0b'
  const days = listing.days_on_mls
  if (days == null) return '#6b7280'
  if (days <= 14) return '#22c55e'
  if (days <= 45) return '#f97316'
  return '#9ca3af'
}

function markerOptions(listing) {
  const fill = markerColor(listing)
  return {
    radius: listing.is_gold_star ? 11 : 8,
    pathOptions: {
      fillColor: fill,
      color: listing.is_gold_star ? '#fbbf24' : '#1f2937',
      weight: listing.is_gold_star ? 3 : 1,
      fillOpacity: 0.9,
    },
  }
}

function GeomanControls({ onPolygonComplete }) {
  const map = useMap()
  useEffect(() => {
    if (!onPolygonComplete) return
    import('@geoman-io/leaflet-geoman-free').then(() => {
      if (!map.pm) return
      map.pm.addControls({
        position: 'topleft',
        drawCircle: false,
        drawMarker: false,
        drawPolyline: false,
        drawRectangle: true,
        drawPolygon: true,
        editMode: false,
        dragMode: false,
        cutPolygon: false,
        removalMode: false,
      })
      const handler = (e) => {
        const latlngs = e.layer.getLatLngs()[0]
        const coords = latlngs.map(ll => [ll.lng, ll.lat])
        coords.push(coords[0])
        map.removeLayer(e.layer)
        onPolygonComplete(coords)
      }
      map.on('pm:create', handler)
      map._pmCreateHandler = handler
    })
    return () => {
      if (map.pm) map.pm.removeControls()
      if (map._pmCreateHandler) map.off('pm:create', map._pmCreateHandler)
    }
  }, [map, onPolygonComplete])
  return null
}

function MapReady() {
  const map = useMap()
  useEffect(() => {
    setTimeout(() => map.invalidateSize(), 0)
  }, [map])
  return null
}

function MapFlyTo({ target }) {
  const map = useMap()
  useEffect(() => {
    if (target) map.flyTo([target.lat, target.lng], target.zoom ?? 13, { duration: 1.2 })
  }, [map, target])
  return null
}

function FitBounds({ listings }) {
  const map = useMap()
  useEffect(() => {
    const valid = listings.filter(l => l.latitude && l.longitude)
    if (valid.length === 0) return
    const bounds = valid.map(l => [l.latitude, l.longitude])
    map.fitBounds(bounds, { padding: [40, 40] })
  }, [map, listings])
  return null
}

const LEGEND = [
  { color: '#f59e0b', label: '⭐ Perfect match', ring: '#fbbf24' },
  { color: '#22c55e', label: 'New find (unseen)', ring: '#4ade80', pulse: true },
  { color: '#22c55e', label: 'Recent (0–14 days)' },
  { color: '#f97316', label: 'Active (15–45 days)' },
  { color: '#9ca3af', label: 'Older (46+ days)' },
  { color: '#6b7280', label: 'Unknown' },
]

function Legend() {
  return (
    <div
      style={{
        position: 'absolute',
        bottom: 24,
        right: 10,
        zIndex: 1000,
        background: 'rgba(15,15,20,0.88)',
        border: '1px solid rgba(255,255,255,0.12)',
        borderRadius: 10,
        padding: '10px 14px',
        minWidth: 160,
        pointerEvents: 'none',
      }}
    >
      <p style={{ color: '#a1a1aa', fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 7 }}>Legend</p>
      {LEGEND.map(({ color, label, ring, pulse }) => (
        <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 5 }}>
          <svg width={14} height={14} viewBox="0 0 14 14" style={{ overflow: 'visible' }}>
            {pulse && (
              <circle cx={7} cy={7} r={5} fill="none" stroke={ring} strokeWidth={2}
                style={{ animation: 'hf-pulse 1.8s ease-out infinite' }} />
            )}
            <circle
              cx={7} cy={7} r={ring && !pulse ? 5.5 : 5}
              fill={color}
              stroke={ring ?? '#1f2937'}
              strokeWidth={ring ? 2 : 1}
            />
          </svg>
          <span style={{ color: '#d4d4d8', fontSize: 11 }}>{label}</span>
        </div>
      ))}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 8, paddingTop: 8, borderTop: '1px solid rgba(255,255,255,0.1)' }}>
        <svg width={14} height={14} viewBox="0 0 14 14">
          <circle cx={7} cy={7} r={5} fill='#3b82f6' stroke='#1d4ed8' strokeWidth={1.5} />
        </svg>
        <span style={{ color: '#d4d4d8', fontSize: 11 }}>Your location</span>
      </div>
    </div>
  )
}

export default function ListingMap({ listings = [], onPolygonComplete, workLocation, flyTarget, userLocation, onDismiss }) {
  const validListings = listings.filter(l => l.latitude && l.longitude)

  return (
    <div style={{ position: 'relative', height: '100%', width: '100%' }}>
      <MapContainer
        center={[39.5, -98.35]}
        zoom={4}
        style={{ height: '100%', width: '100%' }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        <MapReady />
        {validListings.length > 0 && <FitBounds listings={validListings} />}
        {flyTarget && <MapFlyTo target={flyTarget} />}
        {onPolygonComplete && <GeomanControls onPolygonComplete={onPolygonComplete} />}

        {/* User location pin */}
        {userLocation && (
          <CircleMarker
            center={[userLocation.lat, userLocation.lng]}
            radius={10}
            pathOptions={{ fillColor: '#3b82f6', color: '#1d4ed8', weight: 2, fillOpacity: 0.9 }}
          >
            <Popup><span className="font-semibold text-sm">You are here</span></Popup>
          </CircleMarker>
        )}

        {validListings.map((listing, i) => {
          const { radius, pathOptions } = markerOptions(listing)
          return (
            <React.Fragment key={`${listing.source}-${listing.source_id}-${i}`}>
            {listing.is_new && (
              <CircleMarker
                center={[listing.latitude, listing.longitude]}
                radius={radius + 7}
                pathOptions={{
                  fill: false,
                  color: '#4ade80',
                  weight: 2,
                  opacity: 0.8,
                  className: 'new-listing-pulse',
                }}
                interactive={false}
              />
            )}
            <CircleMarker
              center={[listing.latitude, listing.longitude]}
              radius={radius}
              pathOptions={pathOptions}
            >
              <Popup maxWidth={200}>
                <div className="text-sm" style={{ width: '200px' }}>
                  {listing.photo_url && (
                    <div style={{ width: '200px', height: '100px', overflow: 'hidden', borderRadius: '6px 6px 0 0', marginTop: '-2px', marginBottom: '6px' }}>
                      <img
                        src={listing.photo_url}
                        alt=""
                        style={{ width: '200px', height: '100px', objectFit: 'cover', display: 'block' }}
                        onError={(e) => { e.target.parentElement.style.display = 'none' }}
                      />
                    </div>
                  )}
                  <div className="space-y-1 px-0.5">
                    {listing.is_gold_star && (
                      <p style={{ fontSize: 11, color: '#f59e0b', fontWeight: 700, marginBottom: 2 }}>⭐ Perfect Match</p>
                    )}
                    <p className="font-semibold text-gray-900 leading-tight">{listing.address || 'Address unavailable'}</p>
                    {listing.price && (
                      <p className="text-amber-600 font-bold text-base">${listing.price.toLocaleString()}</p>
                    )}
                    <p className="text-gray-500 text-xs">
                      {[listing.bedrooms && `${listing.bedrooms} bd`, listing.bathrooms && `${listing.bathrooms} ba`, listing.sqft && `${listing.sqft.toLocaleString()} sqft`].filter(Boolean).join(' · ')}
                    </p>
                    {listing.days_on_mls != null && (
                      <p style={{ fontSize: 11, color: listing.days_on_mls <= 14 ? '#16a34a' : listing.days_on_mls <= 45 ? '#ea580c' : '#6b7280' }}>
                        {listing.days_on_mls === 0 ? 'Listed today' : `${listing.days_on_mls}d on market`}
                      </p>
                    )}
                    <div className="flex gap-1 mt-2">
                      {listing.source_url ? (
                        <a
                          href={listing.source_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex-1 block px-3 py-1.5 bg-amber-500 hover:bg-amber-400 text-white text-xs font-semibold rounded text-center transition-colors"
                        >
                          View →
                        </a>
                      ) : (
                        <span className="flex-1" />
                      )}
                      {onDismiss && (
                        <button
                          onClick={() => onDismiss(listing.source_id)}
                          style={{ padding: '4px 8px', fontSize: 11, color: '#9ca3af', border: '1px solid #d1d5db', borderRadius: 4, cursor: 'pointer', background: 'white' }}
                          title="Dismiss listing"
                        >
                          ✕ Hide
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              </Popup>
            </CircleMarker>
            </React.Fragment>
          )
        })}

        {workLocation && (
          <CircleMarker
            center={[workLocation.lat, workLocation.lng]}
            radius={10}
            pathOptions={{ fillColor: '#ef4444', color: '#7f1d1d', weight: 2, fillOpacity: 0.9 }}
          >
            <Popup><span className="font-semibold text-sm">Work</span></Popup>
          </CircleMarker>
        )}
      </MapContainer>
      <Legend />
    </div>
  )
}
