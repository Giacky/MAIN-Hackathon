import L from 'leaflet'
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png'
import markerIcon from 'leaflet/dist/images/marker-icon.png'
import markerShadow from 'leaflet/dist/images/marker-shadow.png'
import { Fragment, useEffect, useMemo } from 'react'
import {
  Circle,
  MapContainer,
  Marker,
  TileLayer,
  useMap,
  useMapEvents,
} from 'react-leaflet'
import type { LocationPin, Report } from '../api/types'

// Fix default marker icons under Vite bundling
const DefaultIcon = L.icon({
  iconUrl: markerIcon,
  iconRetinaUrl: markerIcon2x,
  shadowUrl: markerShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
})
L.Marker.prototype.options.icon = DefaultIcon

const MAAS_CENTER: [number, number] = [50.8514, 5.69]
const LOST_COLOR = '#2563eb'
const FOUND_COLOR = '#15803d'

function lostIcon() {
  return L.divIcon({
    className: '',
    html: `<span style="display:block;width:14px;height:14px;border-radius:999px;background:${LOST_COLOR};border:2px solid white;box-shadow:0 1px 4px rgba(0,0,0,.25)"></span>`,
    iconSize: [14, 14],
    iconAnchor: [7, 7],
  })
}

function foundIcon() {
  return L.divIcon({
    className: '',
    html: `<span style="display:block;width:14px;height:14px;border-radius:999px;background:${FOUND_COLOR};border:2px solid white;box-shadow:0 1px 4px rgba(0,0,0,.25)"></span>`,
    iconSize: [14, 14],
    iconAnchor: [7, 7],
  })
}

function FitBounds({ points }: { points: [number, number][] }) {
  const map = useMap()
  useEffect(() => {
    if (points.length >= 2) {
      map.fitBounds(L.latLngBounds(points), { padding: [28, 28] })
    } else if (points.length === 1) {
      map.setView(points[0], 14)
    }
  }, [map, points])
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
}

type LocationMapProps = EditorProps | ViewProps

export function LocationMap(props: LocationMapProps) {
  const center = useMemo((): [number, number] => {
    if (props.mode === 'edit' && props.pins.length > 0) {
      const last = props.pins[props.pins.length - 1]
      return [last.latitude, last.longitude]
    }
    if (props.mode === 'view') {
      const withCoords = props.reports.filter(
        (r) => r.latitude != null && r.longitude != null,
      )
      if (withCoords.length === 1) {
        return [withCoords[0].latitude!, withCoords[0].longitude!]
      }
    }
    return MAAS_CENTER
  }, [props])

  const viewPoints = useMemo((): [number, number][] => {
    if (props.mode !== 'view') return []
    return props.reports
      .filter((r) => r.latitude != null && r.longitude != null)
      .map((r) => [r.latitude!, r.longitude!] as [number, number])
  }, [props])

  const zoom = props.mode === 'edit' ? (props.pins.length ? 14 : 13) : 13

  return (
    <div className="space-y-3">
      <div className="overflow-hidden rounded-2xl border border-hairline">
        <MapContainer
          center={center}
          zoom={zoom}
          className="h-64 w-full"
          scrollWheelZoom
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          {props.mode === 'edit' ? (
            <>
              <ClickToAdd
                enabled
                radiusMeters={props.radiusMeters}
                onAdd={props.onAdd}
              />
              {props.pins.map((pin, i) => (
                <Fragment key={`${pin.latitude}-${pin.longitude}-${i}`}>
                  <Marker position={[pin.latitude, pin.longitude]} />
                  <Circle
                    center={[pin.latitude, pin.longitude]}
                    radius={pin.radius_meters}
                    pathOptions={{
                      color: LOST_COLOR,
                      fillColor: LOST_COLOR,
                      fillOpacity: 0.12,
                    }}
                  />
                </Fragment>
              ))}
            </>
          ) : (
            <>
              <FitBounds points={viewPoints} />
              {props.reports.map((report) => {
                if (report.latitude == null || report.longitude == null) return null
                const color =
                  report.report_type === 'lost' ? LOST_COLOR : FOUND_COLOR
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
                return locs.map((loc, i) => (
                  <Fragment key={`${report.id}-${i}`}>
                    <Marker
                      position={[loc.latitude, loc.longitude]}
                      icon={
                        report.report_type === 'lost' ? lostIcon() : foundIcon()
                      }
                    />
                    <Circle
                      center={[loc.latitude, loc.longitude]}
                      radius={loc.radius_meters}
                      pathOptions={{
                        color,
                        fillColor: color,
                        fillOpacity: 0.12,
                      }}
                    />
                  </Fragment>
                ))
              })}
            </>
          )}
        </MapContainer>
      </div>

      {props.mode === 'edit' ? (
        <div className="space-y-3">
          <label className="block space-y-1.5">
            <span className="text-sm font-medium text-ink">
              Pin radius: {props.radiusMeters} m
            </span>
            <input
              type="range"
              min={10}
              max={5000}
              step={10}
              value={props.radiusMeters}
              onChange={(e) => props.onRadiusChange(Number(e.target.value))}
              className="w-full accent-primary"
            />
          </label>

          {props.pins.length === 0 ? (
            <p className="text-sm text-muted">Tap the map to add a pin.</p>
          ) : (
            <ul className="space-y-2">
              {props.pins.map((pin, i) => (
                <li
                  key={`${pin.latitude}-${pin.longitude}-${i}`}
                  className="flex items-center justify-between gap-3 rounded-xl border border-hairline bg-card px-3 py-2 text-sm"
                >
                  <span className="text-muted">
                    {pin.latitude.toFixed(5)}, {pin.longitude.toFixed(5)} ·{' '}
                    {pin.radius_meters} m
                  </span>
                  <button
                    type="button"
                    className="text-primary transition duration-150 hover:underline"
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
