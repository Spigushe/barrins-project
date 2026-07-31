import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import * as sessionsApi from '@/api/sessions'
import { downloadBlob } from '@/lib/utils'
import type { SessionCreate, SessionPatch } from '@/schemas/tamiyoScroll'

export function useSessions(personalDeckId: string | null, includeArchived = false) {
  return useQuery({
    queryKey: ['sessions', personalDeckId, includeArchived],
    queryFn: () => sessionsApi.listSessions(personalDeckId ?? '', includeArchived),
    enabled: personalDeckId !== null,
  })
}

export function useSessionComparison(sessionId: string | null) {
  return useQuery({
    queryKey: ['session-comparison', sessionId],
    queryFn: () => sessionsApi.getSessionComparison(sessionId ?? ''),
    enabled: sessionId !== null,
  })
}

function useInvalidateSessions() {
  const queryClient = useQueryClient()
  return () => {
    void queryClient.invalidateQueries({ queryKey: ['sessions'] })
    void queryClient.invalidateQueries({ queryKey: ['session-comparison'] })
  }
}

export function useCreateSession() {
  const invalidate = useInvalidateSessions()
  return useMutation({
    mutationFn: (payload: SessionCreate) => sessionsApi.createSession(payload),
    onSuccess: invalidate,
  })
}

export function useUpdateSession() {
  const invalidate = useInvalidateSessions()
  return useMutation({
    mutationFn: ({
      sessionId,
      payload,
    }: {
      sessionId: string
      payload: SessionPatch
    }) => sessionsApi.updateSession(sessionId, payload),
    onSuccess: invalidate,
  })
}

export function useArchiveSession() {
  const invalidate = useInvalidateSessions()
  return useMutation({
    mutationFn: (sessionId: string) => sessionsApi.archiveSession(sessionId),
    onSuccess: invalidate,
  })
}

export function useDownloadSessionReport() {
  return useMutation({
    mutationFn: async ({ sessionId, filename }: { sessionId: string; filename: string }) => {
      const blob = await sessionsApi.getSessionReportPdf(sessionId)
      downloadBlob(blob, filename)
    },
  })
}
