import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import * as teamsApi from '@/api/teams'
import { downloadBlob } from '@/lib/utils'

export function useMyTeams() {
  return useQuery({
    queryKey: ['teams', 'mine'],
    queryFn: () => teamsApi.listMyTeams(),
  })
}

export function useTeam(teamId: string | null) {
  return useQuery({
    queryKey: ['teams', teamId],
    queryFn: () => teamsApi.getTeam(teamId ?? ''),
    enabled: teamId !== null,
  })
}

export function useTeamDecks(teamId: string | null) {
  return useQuery({
    queryKey: ['teams', teamId, 'decks'],
    queryFn: () => teamsApi.listTeamDecks(teamId ?? ''),
    enabled: teamId !== null,
  })
}

export function useMemberDecks(teamId: string | null) {
  return useQuery({
    queryKey: ['teams', teamId, 'members', 'decks'],
    queryFn: () => teamsApi.listMemberDecks(teamId ?? ''),
    enabled: teamId !== null,
  })
}

export function useTeamDeckThreadMessages(teamId: string | null, nameKey: string | null) {
  return useQuery({
    queryKey: ['teams', teamId, 'decks', nameKey, 'thread', 'messages'],
    queryFn: () => teamsApi.listTeamDeckThreadMessages(teamId ?? '', nameKey ?? ''),
    enabled: teamId !== null && nameKey !== null,
  })
}

function useInvalidateTeams() {
  const queryClient = useQueryClient()
  return () => {
    void queryClient.invalidateQueries({ queryKey: ['teams'] })
  }
}

export function useCreateTeam() {
  const invalidate = useInvalidateTeams()
  return useMutation({
    mutationFn: (name: string) => teamsApi.createTeam(name),
    onSuccess: invalidate,
  })
}

export function useJoinTeam() {
  const invalidate = useInvalidateTeams()
  return useMutation({
    mutationFn: (inviteCode: string) => teamsApi.joinTeam(inviteCode),
    onSuccess: invalidate,
  })
}

export function useUpdateTeamDescription() {
  const invalidate = useInvalidateTeams()
  return useMutation({
    mutationFn: ({
      teamId,
      description,
    }: {
      teamId: string
      description: string | null
    }) => teamsApi.updateTeamDescription(teamId, description),
    onSuccess: invalidate,
  })
}

export function useDeleteTeam() {
  const invalidate = useInvalidateTeams()
  return useMutation({
    mutationFn: ({ teamId, inviteCode }: { teamId: string; inviteCode: string }) =>
      teamsApi.deleteTeam(teamId, inviteCode),
    onSuccess: invalidate,
  })
}

export function useLeaveTeam() {
  const invalidate = useInvalidateTeams()
  return useMutation({
    mutationFn: (teamId: string) => teamsApi.leaveTeam(teamId),
    onSuccess: invalidate,
  })
}

export function useRemoveTeamMember() {
  const invalidate = useInvalidateTeams()
  return useMutation({
    mutationFn: ({ teamId, userId }: { teamId: string; userId: string }) =>
      teamsApi.removeTeamMember(teamId, userId),
    onSuccess: invalidate,
  })
}

export function useFlagTeamDeck() {
  const invalidate = useInvalidateTeams()
  return useMutation({
    mutationFn: ({ teamId, deckId }: { teamId: string; deckId: string }) =>
      teamsApi.flagTeamDeck(teamId, deckId),
    onSuccess: invalidate,
  })
}

export function useUnflagTeamDeck() {
  const invalidate = useInvalidateTeams()
  return useMutation({
    mutationFn: ({ teamId, nameKey }: { teamId: string; nameKey: string }) =>
      teamsApi.unflagTeamDeck(teamId, nameKey),
    onSuccess: invalidate,
  })
}

export function useDownloadTeamDeckReport() {
  return useMutation({
    mutationFn: async ({
      teamId,
      nameKey,
      filename,
    }: {
      teamId: string
      nameKey: string
      filename: string
    }) => {
      const blob = await teamsApi.getTeamDeckReportPdf(teamId, nameKey)
      downloadBlob(blob, filename)
    },
  })
}

export function useEnableTeamDeckThread() {
  const invalidate = useInvalidateTeams()
  return useMutation({
    mutationFn: ({ teamId, nameKey }: { teamId: string; nameKey: string }) =>
      teamsApi.enableTeamDeckThread(teamId, nameKey),
    onSuccess: invalidate,
  })
}

export function usePostTeamDeckThreadMessage() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      teamId,
      nameKey,
      body,
    }: {
      teamId: string
      nameKey: string
      body: string
    }) => teamsApi.postTeamDeckThreadMessage(teamId, nameKey, body),
    onSuccess: (_data, { teamId, nameKey }) => {
      void queryClient.invalidateQueries({
        queryKey: ['teams', teamId, 'decks', nameKey, 'thread', 'messages'],
      })
    },
  })
}
