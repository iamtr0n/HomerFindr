/**
 * Straight-line commute time estimator.
 * Uses Haversine distance + assumed average speed (25 mph urban driving)
 * as a rough proxy when no maps API is available.
 */

const EARTH_RADIUS_MILES = 3_958.8
const PEAK_SPEED_MPH = 15    // rush hour (7–9 am, 4–7 pm) urban average
const OFF_PEAK_SPEED_MPH = 30 // off-hours urban average

function toRad(deg) {
  return deg * (Math.PI / 180)
}

function haversineDistance(lat1, lng1, lat2, lng2) {
  const dLat = toRad(lat2 - lat1)
  const dLng = toRad(lng2 - lng1)
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLng / 2) ** 2
  return EARTH_RADIUS_MILES * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
}

/**
 * Estimate one-way commute time in minutes between two lat/lng points.
 * Applies a 1.35x road factor to convert straight-line to driving distance.
 * Returns { peak, offPeak } minutes for rush-hour vs. off-hours.
 */
export function estimateCommute(homeLat, homeLng, workLat, workLng) {
  if (homeLat == null || homeLng == null || workLat == null || workLng == null) return null
  const distanceMiles = haversineDistance(homeLat, homeLng, workLat, workLng) * 1.35
  return {
    peak: Math.round((distanceMiles / PEAK_SPEED_MPH) * 60),
    offPeak: Math.round((distanceMiles / OFF_PEAK_SPEED_MPH) * 60),
  }
}
