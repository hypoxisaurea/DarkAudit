import { useMutation, useQueryClient } from "@tanstack/react-query";

import { updateFindingStatus } from "@/api/audits";
import type { FindingStatus } from "@/entities/audit/types";
import { dashboardKeys } from "@/features/audit-dashboard/useDashboardSummary";

export function useFindingStatus() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ findingId, status }: { findingId: string; status: FindingStatus }) =>
      updateFindingStatus(findingId, status),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: dashboardKeys.all }),
  });
}
