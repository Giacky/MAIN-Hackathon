import L from 'leaflet'
import { Fragment, useEffect, useMemo, useState } from 'react'
import {
  Circle,
  MapContainer,
  Marker,
  Popup,
  TileLayer,
  useMap,
  useMapEvents,
} from 'react-leaflet'
import { Link } from 'react-router-dom'
import type { LocationPin, Report, ReportType } from '../api/types'
import { firstLine, timeAgo } from '../time'
import { Badge } from './ui/Badge'

const MAAS_CENTER: [number, number] = [50.8514, 5.69]

/** Pin and circle colors: lost = coral accent, found = teal primary. */
export const PIN_COLORS: Record<ReportType, string> = {
  lost: '#F28C68',
  found: '#176B68',
}

const TILE_URL = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'
const TILE_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'

interface PinIconOptions {
  kind: ReportType
  label?: string
  active?: boolean
}

const iconCache = new Map<string, L.DivIcon>()

/**
 * Frosted-glass teardrop with a colored core, 28x36, anchored bottom-center.
 * `label` renders inside the core (used for pin index while editing);
 * `active` scales the pin up and adds a pulsing halo.
 */
export function pinIcon({ kind, label, active = false }: PinIconOptions): L.DivIcon {
  const key = `${kind}|${label ?? ''}|${active ? 1 : 0}`
  const cached = iconCache.get(key)
  if (cached) return cached

  const core = PIN_COLORS[kind]
  const text = label
    ? `<text x="14" y="17.5" text-anchor="middle" font-family="Figtree, system-ui, sans-serif" font-size="9.5" font-weight="700" fill="#fff">${escapeHtml(label)}</text>`
    : `<circle cx="14" cy="14" r="2.6" fill="rgba(255,255,255,.85)"/>`
  const halo = active ? `<span class="lf-pin-pulse" style="background:${core}"></span>` : ''

  const icon = L.divIcon({
    className: `lf-pin${active ? ' active' : ''}`,
    html: `${halo}<svg width="28" height="36" viewBox="0 0 28 36" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <path d="M14 1C6.82 1 1 6.82 1 14c0 8.6 13 21 13 21s13-12.4 13-21C27 6.82 21.18 1 14 1Z" fill="rgba(255,255,255,.9)" stroke="rgba(255,255,255,.95)" stroke-width="1"/>
  <path d="M14 2.2C7.5 2.2 2.2 7.5 2.2 14" fill="none" stroke="rgba(255,255,255,1)" stroke-width="1.2" stroke-linecap="round" opacity=".9"/>
  <circle cx="14" cy="14" r="8" fill="${core}"/>
  <circle cx="14" cy="14" r="8" fill="none" stroke="rgba(255,255,255,.5)" stroke-width="1"/>
  ${text}
</svg>`,
    iconSize: [28, 36],
    iconAnchor: [14, 36],
    popupAnchor: [0, -34],
  })
  iconCache.set(key, icon)
  return icon
}

function escapeHtml(s: string): string {
  return s.replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`)
}

function circleOptions(kind: ReportType): L.PathOptions {
  const color = PIN_COLORS[kind]
  return { color, fillColor: color, weight: 1.5, fillOpacity: 0.1 }
}

/** Circle plus a zoom-in, mounted only for the pin the viewer just tapped. */
function RadiusReveal({
  lat,
  lng,
  radius,
  kind,
}: {
  lat: number
  lng: number
  radius: number
  kind: ReportType
}) {
  const map = useMap()
  useEffect(() => {
    const bounds = L.latLng(lat, lng).toBounds(Math.max(radius, 40) * 2.2)
    map.fitBounds(bounds, { padding: [40, 40], maxZoom: 16, animate: true })
  }, [map, lat, lng, radius])
  return <Circle center={[lat, lng]} radius={radius} pathOptions={circleOptions(kind)} />
}

/** View mode always starts on Maastricht; far pins stay on the map for panning. */
function MaastrichtHome() {
  const map = useMap()
  useEffect(() => {
    map.setView(MAAS_CENTER, 13)
  }, [map])
  return null
}

function ClickToAdd({
  enabled,
  radiusMeters,
  onAdd,
}: {
  enabled: boolean
  radiusMeters: number
  onAdd: (pin: LocationPin) => void
}) {
  useMapEvents({
    click(e) {
      if (!enabled) return
      onAdd({
        latitude: e.latlng.lat,
        longitude: e.latlng.lng,
        radius_meters: radiusMeters,
      })
    },
  })
  return null
}

interface EditorProps {
  mode: 'edit'
  /** Lost or found: colors pins and circles to match the report being filed. */
  variant: ReportType
  pins: LocationPin[]
  radiusMeters: number
  onAdd: (pin: LocationPin) => void
  onRemove: (index: number) => void
  onClear: () => void
  onRadiusChange: (radius: number) => void
}

interface ViewProps {
  mode: 'view'
  reports: Report[]
  /** Ids of the viewer's own reports; those get a "See matches" link in the popup. */
  mineIds?: ReadonlySet<string>
  className?: string
}

type LocationMapProps = EditorProps | ViewProps

export function LocationMap(props: LocationMapProps) {
  const [openPin, setOpenPin] = useState<string | null>(null)
  const center = useMemo((): [number, number] => {
    if (props.mode === 'edit' && props.pins.length > 0) {
      const last = props.pins[props.pins.length - 1]
      return [last.latitude, last.longitude]
    }
    return MAAS_CENTER
  }, [props])

  const zoom = props.mode === 'edit' ? (props.pins.length ? 14 : 13) : 13
  const heightClass = props.mode === 'view' ? (props.className ?? 'h-[26rem]') : 'h-64'

  return (
    <div className="space-y-3">
      <div className="glass overflow-hidden p-0">
        <MapContainer center={center} zoom={zoom} className={`${heightClass} w-full`} scrollWheelZoom>
          <TileLayer attribution={TILE_ATTRIBUTION} url={TILE_URL} />

          {props.mode === 'edit' ? (
            <>
              <ClickToAdd enabled radiusMeters={props.radiusMeters} onAdd={props.onAdd} />
              {props.pins.map((pin, i) => {
                const isLast = i === props.pins.length - 1
                return (
                  <Fragment key={`${pin.latitude}-${pin.longitude}-${i}`}>
                    <Marker
                      position={[pin.latitude, pin.longitude]}
                      icon={pinIcon({ kind: props.variant, label: String(i + 1), active: isLast })}
                      zIndexOffset={isLast ? 1000 : 0}
                    />
                    <Circle
                      center={[pin.latitude, pin.longitude]}
                      radius={pin.radius_meters}
                      pathOptions={circleOptions(props.variant)}
                    />
                  </Fragment>
                )
              })}
            </>
          ) : (
            <>
              <MaastrichtHome />
              {props.reports.map((report) => {
                if (report.latitude == null || report.longitude == null) return null
                const kind: ReportType = report.report_type === 'lost' ? 'lost' : 'found'
                const locs =
                  report.locations?.length > 0
                    ? report.locations
                    : [
                        {
                          latitude: report.latitude,
                          longitude: report.longitude,
                          radius_meters: report.radius_meters ?? 200,
                        },
                      ]
                return locs.map((loc, i) => {
                  const pinKey = `${report.id}-${i}`
                  const open = openPin === pinKey
                  return (
                    <Fragment key={pinKey}>
                      <Marker
                        position={[loc.latitude, loc.longitude]}
                        icon={pinIcon({ kind, active: open })}
                        zIndexOffset={open ? 1000 : 0}
                        eventHandlers={{
                          click: () => setOpenPin(pinKey),
                          popupclose: () => setOpenPin((current) => (current === pinKey ? null : current)),
                        }}
                      >
                        <Popup closeButton={false} minWidth={200} maxWidth={240}>
                          <ReportPopup
                            report={report}
                            mine={props.mineIds?.has(report.id) ?? false}
                            radiusMeters={loc.radius_meters}
                          />
                        </Popup>
                      </Marker>
                      {open ? (
                        <RadiusReveal
                          lat={loc.latitude}
                          lng={loc.longitude}
                          radius={loc.radius_meters}
                          kind={kind}
                        />
                      ) : null}
                    </Fragment>
                  )
                })
              })}
            </>
          )}
        </MapContainer>
      </div>

      {props.mode === 'edit' ? (
        <div className="space-y-3">
          <label className="block space-y-1.5">
            <span className="flex justify-between text-sm font-medium text-ink">
              <span>Search radius</span>
              <span className="tabular-nums text-muted">{props.radiusMeters} m</span>
            </span>
            <input
              type="range"
              min={10}
              max={5000}
              step={10}
              value={props.radiusMeters}
              onChange={(e) => props.onRadiusChange(Number(e.target.value))}
              className={`w-full ${props.variant === 'lost' ? 'accent-accent' : 'accent-primary'}`}
            />
          </label>

          {props.pins.length === 0 ? (
            <p className="text-sm text-muted">Tap the map to drop a pin.</p>
          ) : (
            <ul className="space-y-2">
              {props.pins.map((pin, i) => (
                <li
                  key={`${pin.latitude}-${pin.longitude}-${i}`}
                  className="glass flex items-center justify-between gap-3 rounded-2xl px-3 py-2 text-sm"
                >
                  <span className="flex items-center gap-2 text-muted">
                    <span
                      className="inline-flex h-5 w-5 items-center justify-center rounded-full text-[11px] font-bold text-white"
                      style={{ backgroundColor: PIN_COLORS[props.variant] }}
                    >
                      {i + 1}
                    </span>
                    <span className="tabular-nums">
                      {pin.latitude.toFixed(4)}, {pin.longitude.toFixed(4)} · {pin.radius_meters} m
                    </span>
                  </span>
                  <button
                    type="button"
                    className="font-medium text-primary transition duration-150 hover:underline"
                    onClick={() => props.onRemove(i)}
                  >
                    Remove
                  </button>
                </li>
              ))}
            </ul>
          )}

          {props.pins.length > 0 ? (
            <button
              type="button"
              className="text-sm text-muted transition duration-150 hover:text-ink"
              onClick={props.onClear}
            >
              Clear all pins
            </button>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}

function ReportPopup({
  report,
  mine,
  radiusMeters,
}: {
  report: Report
  mine: boolean
  radiusMeters: number
}) {
  const photo = report.image_urls?.[0]
  const when = timeAgo(report.event_time ?? report.created_at)
  return (
    <div className="flex gap-2.5">
      <div className="h-14 w-14 shrink-0 overflow-hidden rounded-xl bg-primary-light/60">
        {photo ? <img src={photo} alt="" className="h-full w-full object-cover" /> : null}
      </div>
      <div className="min-w-0 flex-1">
        <div className="mb-1 flex items-center gap-1.5">
          <Badge tone={report.report_type === 'lost' ? 'lost' : 'found'}>{report.report_type}</Badge>
          {mine ? <Badge tone="ink">Yours</Badge> : null}
          {when ? <span className="text-[11px] text-muted">{when}</span> : null}
        </div>
        <p className="line-clamp-2 text-[13px] leading-snug text-ink">{firstLine(report.description, 90)}</p>
        <p className="mt-0.5 text-[11px] text-muted">Within {Math.round(radiusMeters)} m</p>
        {mine ? (
          <Link
            to={`/reports/${report.id}`}
            className="mt-1.5 inline-block text-[13px] font-semibold text-primary"
          >
            View report
          </Link>
        ) : null}
      </div>
    </div>
  )
}