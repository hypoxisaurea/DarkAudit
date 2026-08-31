import { z } from "zod";

export const findingSchema = z.object({
  id: z.string().min(1),
  ruleId: z.enum(["DA-03", "DA-04", "DA-12", "DA-15"]),
  riskType: z.enum([
    "PRESELECTED_OPTION",
    "VISUAL_HIERARCHY_DISTORTION",
    "EMOTIONAL_LANGUAGE",
    "SEQUENTIAL_PRICE_DISCLOSURE",
  ]),
  title: z.string(),
  description: z.string(),
  screenIds: z.array(z.string()),
  element: z.string(),
  defaultState: z.string().optional(),
  costImpact: z.string().optional(),
  severity: z.enum(["HIGH", "REVIEW"]),
  status: z.enum(["open", "reviewing", "resolved"]),
  confidence: z.number().min(0).max(1),
  recommendation: z.string(),
  guideline: z.string(),
});

export const auditSchema = z.object({
  id: z.string().min(1),
  name: z.string().min(1),
  platform: z.enum(["mobile-web", "desktop-web", "app"]),
  status: z.enum(["draft", "queued", "analyzing", "completed", "failed"]),
  updatedAt: z.string().datetime({ offset: true }),
  screens: z.array(
    z.object({
      id: z.string().min(1),
      order: z.number().int().positive(),
      flowStep: z.string().min(1),
      imageUrl: z.string(),
      findingCount: z.number().int().nonnegative(),
    }),
  ),
  findings: z.array(findingSchema),
});

export const dashboardSummarySchema = z.object({
  activeAuditId: z.string().nullable(),
  audits: z.array(auditSchema),
});

export const analysisJobSchema = z.object({
  jobId: z.string().min(1),
  auditId: z.string().min(1),
  status: z.enum(["queued", "analyzing", "completed", "failed"]),
  progress: z.number().min(0).max(100),
});
