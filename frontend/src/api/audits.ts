import { apiRequest } from "@/api/client";
import type {
  AnalysisJobDto,
  AuditDto,
  CreateAuditDto,
  FindingStatus,
} from "@/entities/audit/types";

export function createAudit(input: CreateAuditDto) {
  return apiRequest<AuditDto>("/api/v1/audits", { method: "POST", body: JSON.stringify(input) });
}

export function startAnalysis(auditId: string) {
  return apiRequest<AnalysisJobDto>(`/api/v1/audits/${auditId}/analyze`, { method: "POST" });
}

export function getAnalysisStatus(jobId: string) {
  return apiRequest<AnalysisJobDto>(`/api/v1/analysis-jobs/${jobId}`);
}

export function updateFindingStatus(findingId: string, status: FindingStatus) {
  return apiRequest<{ id: string; status: FindingStatus }>(`/api/v1/findings/${findingId}`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}
