import { useQuery } from '@tanstack/react-query'
import { getTelemetry } from '@/api/telemetry'

export function useTelemetry() {
  return useQuery({ queryKey: ['telemetry'], queryFn: getTelemetry })
}
