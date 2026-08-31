import {
  ArrowRight,
  CalendarDays,
  Check,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  CircleAlert,
  Expand,
  FileText,
  MonitorSmartphone,
  MoreVertical,
  Search,
  ShieldCheck,
  Smartphone,
  ZoomIn,
  ZoomOut,
} from "lucide-react";

import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { cn } from "@/lib/cn";

const metrics = [
  {
    label: "Findings detected",
    value: 7,
    icon: ShieldCheck,
    action: "View all",
    color: "text-brand-400",
  },
  {
    label: "Need review",
    value: 2,
    icon: CircleAlert,
    action: "Review now",
    color: "text-warning",
  },
  { label: "Resolved", value: 5, icon: CheckCircle2, action: "View resolved", color: "text-white" },
];

const flowSteps = [
  { name: "Product Intro", issue: false },
  { name: "Option Selection", issue: true },
  { name: "Consent", issue: true },
  { name: "Final Review", issue: false },
  { name: "Complete", issue: false },
];

const findings = [
  {
    code: "DP-04",
    title: "Preselected Option",
    copy: "유료 옵션이 기본 선택되어 추가 비용이 발생할 수 있습니다.",
    variant: "danger" as const,
  },
  {
    code: "DP-12",
    title: "Emotional Pressure",
    copy: "불안감을 자극하는 문구가 사용자의 합리적 판단을 저해할 수 있습니다.",
    variant: "warning" as const,
  },
  {
    code: "DP-15",
    title: "Sequential Pricing",
    copy: "가격 정보가 단계적으로 제공되어 전체 비용 인식이 어려울 수 있습니다.",
    variant: "success" as const,
  },
];

function MobileScreen({ complete = false }: { complete?: boolean }) {
  return (
    <div className="mx-auto h-full min-h-56 w-[210px] rounded-t-[28px] border-[6px] border-[#252927] bg-white p-4 shadow-xl sm:w-[240px]">
      <div className="mx-auto mb-5 h-1.5 w-12 rounded-full bg-black/70" />
      {complete ? (
        <div className="flex h-40 flex-col items-center justify-center text-center">
          <span className="flex size-10 items-center justify-center rounded-full bg-brand-600 text-white">
            <Check size={22} />
          </span>
          <p className="mt-4 text-sm font-bold">신청이 완료되었습니다</p>
        </div>
      ) : (
        <>
          <p className="text-sm font-bold">보험 옵션을 선택해주세요</p>
          <p className="mt-5 text-[9px] font-semibold">필수 보장</p>
          <div className="mt-2 flex justify-between rounded border border-border p-3 text-[9px]">
            <span>상해 사망 / 후유장해</span>
            <span>가입됨 ✓</span>
          </div>
          <p className="mt-5 text-[9px] font-semibold">추가 보장 (선택)</p>
          <div className="mt-2 flex items-center gap-2 rounded border-2 border-danger/45 bg-danger/5 p-3 text-[9px]">
            <span className="flex size-4 items-center justify-center rounded bg-brand-600 text-white">
              <Check size={10} />
            </span>
            <span className="flex-1">해외 의료비 보장</span>
            <strong>+₩3,000 / 월</strong>
          </div>
          <div className="mt-2 flex items-center gap-2 rounded border border-border p-3 text-[9px]">
            <span className="size-4 rounded border border-border" />
            <span className="flex-1">골절 진단비 보장</span>
            <strong>+₩2,000 / 월</strong>
          </div>
        </>
      )}
    </div>
  );
}

function MiniScreen({ index }: { index: number }) {
  return (
    <div className="h-22 w-14 rounded border border-border bg-white p-1.5 shadow-sm">
      <div className="h-1 w-5 rounded bg-black/70" />
      <div className="mt-2 h-1.5 w-8 rounded bg-black/60" />
      <div className="mt-2 space-y-1">
        <div className="h-2 rounded bg-brand-50" />
        <div className={cn("h-2 rounded", index === 1 ? "bg-danger/20" : "bg-black/5")} />
        <div className="h-2 rounded bg-black/5" />
      </div>
    </div>
  );
}

function FlowOverview() {
  return (
    <Card className="p-5">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-bold">Audit flow overview</h2>
        <button className="flex items-center gap-2 rounded-control border border-border px-3 py-2 text-xs font-semibold text-brand-700">
          View full flow <ArrowRight size={13} />
        </button>
      </div>
      <div className="mt-7 grid grid-cols-5 gap-2 overflow-x-auto">
        {flowSteps.map((step, index) => (
          <div className="relative min-w-20 text-center" key={step.name}>
            {index < flowSteps.length - 1 && (
              <span className="absolute left-[60%] top-3 h-px w-[80%] border-t border-dashed border-muted/40" />
            )}
            <div className="relative mx-auto flex size-6 items-center justify-center rounded-full bg-brand-900 text-[9px] font-bold text-white">
              {index + 1}
              {step.issue && (
                <span className="absolute -right-5 flex size-4 items-center justify-center rounded-full bg-danger text-[8px]">
                  1
                </span>
              )}
            </div>
            <div className="mx-auto mt-4 w-fit">
              <MiniScreen index={index} />
            </div>
            <p className="mt-2 truncate text-[10px] font-medium">{step.name}</p>
          </div>
        ))}
      </div>
    </Card>
  );
}

function ScreenPreview() {
  return (
    <Card className="relative mt-4 min-h-[380px] overflow-hidden p-5">
      <h2 className="text-sm font-bold">Screen preview</h2>
      <div className="absolute inset-x-0 bottom-0 top-14 flex items-end justify-center bg-gradient-to-b from-white to-brand-50/60">
        <MobileScreen />
      </div>
      <div className="absolute right-4 top-20 overflow-hidden rounded-control border border-border bg-white shadow-sm">
        {[ZoomIn, ZoomOut, Search, Expand].map((Icon, index) => (
          <button
            aria-label={["확대", "축소", "배율", "전체 화면"][index]}
            className="flex h-10 w-9 items-center justify-center border-b border-border last:border-0"
            key={index}
          >
            <Icon size={15} />
          </button>
        ))}
      </div>
    </Card>
  );
}

function FindingDetails() {
  return (
    <Card className="overflow-hidden">
      <div className="flex items-center justify-between border-b border-border px-6 py-4">
        <h2 className="text-sm font-bold">Finding details</h2>
        <div className="flex items-center gap-3 text-sm">
          <ChevronLeft size={15} />
          <span>2 / 7</span>
          <ChevronRight size={15} />
          <MoreVertical size={16} />
        </div>
      </div>
      <div className="p-6">
        <div className="flex items-center justify-between">
          <p className="text-sm font-bold text-brand-700">DP-04</p>
          <Badge variant="danger">●&nbsp; Needs Review</Badge>
        </div>
        <h3 className="mt-3 text-2xl font-bold">Preselected Option</h3>
        <p className="mt-3 text-sm leading-6 text-muted">
          유료 옵션이 기본 선택되어 사용자의 능동적 선택을 침해할 수 있습니다.
        </p>
        <dl className="mt-6 divide-y divide-border border-y border-border text-sm">
          <div className="grid grid-cols-2 py-3">
            <dt className="text-muted">Element</dt>
            <dd>Checkbox</dd>
          </div>
          <div className="grid grid-cols-2 py-3">
            <dt className="text-muted">Default state</dt>
            <dd className="font-semibold text-danger">Selected</dd>
          </div>
          <div className="grid grid-cols-2 py-3">
            <dt className="text-muted">Cost impact</dt>
            <dd className="font-semibold text-danger">+₩3,000 / month</dd>
          </div>
        </dl>
        <div className="mt-6 flex gap-4 rounded-card border border-border p-5">
          <FileText className="shrink-0 text-brand-600" size={25} />
          <div>
            <p className="text-sm font-bold">FSC 금융소비자 보호 가이드라인</p>
            <p className="mt-2 text-xs leading-6 text-muted">
              2.1.1. (사전선택 금지) 금융회사는 소비자가 추가 비용이 발생하는 서비스를 이용하지
              않도록 기본 설정해서는 안 됩니다.
            </p>
          </div>
        </div>
        <button className="mt-6 flex w-full items-center justify-center gap-3 rounded-control border border-brand-700 py-3 text-sm font-semibold text-brand-700">
          View recommendation <ArrowRight size={15} />
        </button>
      </div>
    </Card>
  );
}

function FindingsRow() {
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-[1fr_1fr_1fr_1.05fr]">
      {findings.map((finding, index) => (
        <Card className={cn("p-5", index === 0 && "border-danger/60")} key={finding.code}>
          <div className="flex items-center justify-between">
            <p className="text-xs font-bold text-brand-700">{finding.code}</p>
            <Badge variant={finding.variant}>{index === 2 ? "Minor" : "Review Needed"}</Badge>
          </div>
          <div className="mt-2 flex items-start justify-between gap-3">
            <div>
              <h3 className="font-bold">{finding.title}</h3>
              <p className="mt-1 text-xs leading-5 text-muted">{finding.copy}</p>
            </div>
            <ChevronRight className="mt-1 shrink-0" size={16} />
          </div>
        </Card>
      ))}
      <Card className="flex items-center justify-between p-5">
        <div>
          <p className="font-bold">View all findings</p>
          <p className="mt-2 text-xs text-muted">7 findings</p>
        </div>
        <span className="flex size-8 items-center justify-center rounded-full bg-brand-700 text-white">
          <ArrowRight size={15} />
        </span>
      </Card>
    </div>
  );
}

function RecentAudits() {
  return (
    <Card className="mt-4 overflow-hidden">
      <div className="flex items-center justify-between border-b border-border px-6 py-4">
        <h2 className="text-sm font-bold">Recent audits</h2>
        <button className="flex items-center gap-2 text-xs font-semibold text-brand-700">
          View all audits <ArrowRight size={13} />
        </button>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[780px] text-left text-xs">
          <thead className="border-b border-border bg-black/[0.015] text-muted">
            <tr>
              {["Audit name", "Platform", "Screens", "Findings", "Status", "Last updated", ""].map(
                (head) => (
                  <th className="px-6 py-3 font-medium" key={head}>
                    {head}
                  </th>
                ),
              )}
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="px-6 py-4 font-semibold">Insurance Signup Flow v1</td>
              <td className="px-6 py-4">
                <span className="flex items-center gap-2">
                  <Smartphone size={14} /> Mobile Web
                </span>
              </td>
              <td className="px-6 py-4">15</td>
              <td className="px-6 py-4">
                <span className="flex gap-5">
                  <i className="not-italic text-danger">● 7</i>
                  <i className="not-italic text-warning">● 2</i>
                  <i className="not-italic text-success">● 5</i>
                </span>
              </td>
              <td className="px-6 py-4">
                <Badge variant="success">In Progress</Badge>
              </td>
              <td className="px-6 py-4">May 15, 2024 14:20</td>
              <td className="px-6 py-4">
                <MoreVertical size={15} />
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </Card>
  );
}

export function OverviewPage() {
  return (
    <div className="mx-auto max-w-[1500px]">
      <h1 className="text-2xl font-bold tracking-tight">Overview</h1>
      <section className="subtle-grid mt-6 overflow-hidden rounded-card bg-brand-900 p-6 text-white lg:p-8">
        <div className="grid items-center gap-8 xl:grid-cols-[1fr_1.15fr]">
          <div>
            <Badge className="bg-brand-600 text-white">●&nbsp; In Progress</Badge>
            <h2 className="mt-4 text-2xl font-bold sm:text-3xl">Insurance Signup Flow v1</h2>
            <div className="mt-5 flex flex-wrap gap-6 text-xs text-white/70">
              <span className="flex items-center gap-2">
                <Smartphone size={15} /> Mobile Web
              </span>
              <span className="flex items-center gap-2">
                <MonitorSmartphone size={15} /> 15 screens
              </span>
              <span className="flex items-center gap-2">
                <CalendarDays size={15} /> May 15, 2024 14:20
              </span>
            </div>
          </div>
          <div className="grid grid-cols-1 divide-y divide-white/15 rounded-card border border-white/20 sm:grid-cols-3 sm:divide-x sm:divide-y-0">
            {metrics.map(({ label, value, icon: Icon, action, color }) => (
              <div className="p-5" key={label}>
                <div className="flex items-center gap-3">
                  <Icon className={color} size={22} />
                  <span className="text-2xl font-bold">{value}</span>
                </div>
                <p className="mt-3 text-xs font-semibold">{label}</p>
                <p className="mt-5 flex items-center gap-2 text-xs text-brand-400">
                  {action} <ArrowRight size={12} />
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>
      <div className="mt-4 grid gap-4 xl:grid-cols-[1.35fr_1fr]">
        <div>
          <FlowOverview />
          <ScreenPreview />
        </div>
        <FindingDetails />
      </div>
      <div className="mt-4">
        <FindingsRow />
      </div>
      <RecentAudits />
    </div>
  );
}
