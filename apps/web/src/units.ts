/** Unit helpers. The API always stores metric; the UI shows the user's preference. */
export type Units = 'metric' | 'imperial'

export const KG_PER_LB = 0.45359237
export const CM_PER_IN = 2.54

export const kgToDisplay = (kg: number, units: Units) => (units === 'imperial' ? kg / KG_PER_LB : kg)
export const displayToKg = (v: number, units: Units) => (units === 'imperial' ? v * KG_PER_LB : v)
export const weightUnit = (units: Units) => (units === 'imperial' ? 'lb' : 'kg')

export function formatWeight(kg: number, units: Units, digits = 1) {
  return `${kgToDisplay(kg, units).toFixed(digits)} ${weightUnit(units)}`
}

export function cmToFtIn(cm: number) {
  const totalIn = cm / CM_PER_IN
  const ft = Math.floor(totalIn / 12)
  return { ft, inches: Math.round(totalIn - ft * 12) }
}

export const ftInToCm = (ft: number, inches: number) => (ft * 12 + inches) * CM_PER_IN

export const round = (n: number | null | undefined, digits = 0) =>
  n == null ? '–' : Number(n).toLocaleString(undefined, { maximumFractionDigits: digits })
