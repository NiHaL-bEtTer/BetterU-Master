import createClient from 'openapi-fetch'
import type { components, paths } from './schema'

/** Typed API client generated from FastAPI's OpenAPI schema (`npm run gen:api`). */
export const api = createClient<paths>({ baseUrl: '', credentials: 'same-origin' })

export type S = components['schemas']
export type User = S['UserOut']
export type Profile = S['ProfileOut']
export type ProfileInput = S['ProfileIn']
export type Targets = S['Targets']
export type Food = S['FoodOut']
export type DaySummary = S['DaySummary']
export type MealEntry = S['MealEntryOut']
export type Meal = MealEntry['meal']
export type Progress = S['ProgressOut']
export type WorkoutPlan = S['WorkoutPlanOut']
export type PlanExercise = S['PlanExercise']
export type WorkoutSet = S['SetOut']
export type ChatMessage = S['ChatMessageOut']
export type Source = S['Source']
export type ChatAction = S['ChatAction']

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

/** Turn FastAPI error bodies ({detail: string | ValidationError[]}) into a readable message. */
export function errorMessage(error: unknown, fallback = 'Something went wrong. Please try again.'): string {
  if (!error) return fallback
  if (error instanceof Error) return error.message
  const detail = (error as { detail?: unknown }).detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail.length) {
    const first = detail[0] as { loc?: (string | number)[]; msg?: string }
    const field = first.loc?.filter((p) => p !== 'body').join('.')
    return field ? `${field}: ${first.msg}` : first.msg ?? fallback
  }
  return fallback
}

/** Unwrap an openapi-fetch result: return data or throw ApiError. */
export async function unwrap<T>(
  promise: Promise<{ data?: T; error?: unknown; response: Response }>,
): Promise<T> {
  const { data, error, response } = await promise
  if (!response.ok) throw new ApiError(response.status, errorMessage(error))
  return data as T
}

export const todayISO = () => {
  const d = new Date()
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10)
}
