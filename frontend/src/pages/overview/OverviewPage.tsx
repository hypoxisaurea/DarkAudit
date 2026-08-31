import { Card } from "@/components/ui/Card";

const metrics = [
  { label: "탐지 항목", value: 7 },
  { label: "검토 필요", value: 2 },
  { label: "해결됨", value: 5 },
];

export function OverviewPage() {
  return (
    <div className="mx-auto max-w-[1440px]">
      <p className="text-sm font-semibold text-brand-700">Dashboard</p>
      <h1 className="mt-1 text-3xl font-bold tracking-tight">Overview</h1>
      <Card className="mt-7 overflow-hidden border-0 bg-brand-900 p-8 text-white">
        <div className="grid items-center gap-8 lg:grid-cols-[1fr_1.15fr]">
          <div>
            <span className="rounded-full bg-brand-600 px-3 py-1 text-xs font-semibold">
              In Progress
            </span>
            <h2 className="mt-5 text-3xl font-bold">Insurance Signup Flow v1</h2>
            <p className="mt-3 text-sm text-white/65">
              Mobile Web · 15 screens · 최근 업데이트 14:20
            </p>
          </div>
          <div className="grid grid-cols-3 divide-x divide-white/15 rounded-card border border-white/15">
            {metrics.map((metric) => (
              <div className="p-5" key={metric.label}>
                <p className="text-3xl font-bold">{metric.value}</p>
                <p className="mt-2 text-sm text-white/65">{metric.label}</p>
              </div>
            ))}
          </div>
        </div>
      </Card>
      <div className="mt-5 grid gap-5 xl:grid-cols-[1.35fr_1fr]">
        <Card className="min-h-80 p-6">
          <h2 className="font-semibold">Audit flow overview</h2>
          <div className="mt-8 flex items-center justify-between gap-3">
            {["상품 안내", "옵션 선택", "동의", "최종 확인", "완료"].map((step, index) => (
              <div className="text-center" key={step}>
                <span className="mx-auto flex size-8 items-center justify-center rounded-full bg-brand-700 text-xs font-bold text-white">
                  {index + 1}
                </span>
                <p className="mt-3 text-xs text-muted">{step}</p>
              </div>
            ))}
          </div>
        </Card>
        <Card className="min-h-80 p-6">
          <p className="text-sm font-bold text-brand-700">DP-04</p>
          <h2 className="mt-2 text-2xl font-bold">특정 옵션의 사전선택</h2>
          <p className="mt-4 leading-7 text-muted">
            유료 옵션이 기본 선택되어 사용자의 능동적 선택을 침해할 수 있습니다.
          </p>
          <div className="mt-8 rounded-control bg-background p-4 text-sm">
            금융소비자 보호 가이드라인에 따라 추가 비용이 발생하는 옵션은 사용자가 직접 선택하도록
            제공해야 합니다.
          </div>
        </Card>
      </div>
    </div>
  );
}
