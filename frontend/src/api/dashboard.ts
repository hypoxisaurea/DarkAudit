import { apiRequest } from "@/api/client";
import { dashboardSummarySchema } from "@/api/schemas";

export async function getDashboardSummary() {
  return dashboardSummarySchema.parse(await apiRequest<unknown>("/api/v1/dashboard/summary"));
}
