export type AuditStatus = "draft" | "queued" | "analyzing" | "completed" | "failed";
export type FindingSeverity = "HIGH" | "REVIEW";
export type FindingStatus = "open" | "reviewing" | "resolved";

export type AuditScreenDto = {
  id: string;
  order: number;
  flowStep: string;
  imageUrl: string;
  findingCount: number;
};

export type FindingDto = {
  id: string;
  ruleId: "DA-03" | "DA-04" | "DA-12" | "DA-15";
  riskType:
    | "PRESELECTED_OPTION"
    | "VISUAL_HIERARCHY_DISTORTION"
    | "EMOTIONAL_LANGUAGE"
    | "SEQUENTIAL_PRICE_DISCLOSURE";
  title: string;
  description: string;
  screenIds: string[];
  element: string;
  defaultState?: string;
  costImpact?: string;
  severity: FindingSeverity;
  status: FindingStatus;
  confidence: number;
  recommendation: string;
  guideline: string;
};

export type AuditDto = {
  id: string;
  name: string;
  platform: "mobile-web" | "desktop-web" | "app";
  status: AuditStatus;
  updatedAt: string;
  screens: AuditScreenDto[];
  findings: FindingDto[];
};

export type DashboardSummaryDto = {
  activeAuditId: string | null;
  audits: AuditDto[];
};
