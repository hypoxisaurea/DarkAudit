import { apiRequest } from "@/api/client";
import type { DashboardSummaryDto } from "@/entities/audit/types";

export function getDashboardSummary() {
  return apiRequest<DashboardSummaryDto>("/api/v1/dashboard/summary");
}
