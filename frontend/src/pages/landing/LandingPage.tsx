import { ArrowRight, ShieldCheck } from "lucide-react";
import { Link } from "react-router-dom";

import { Brand } from "@/components/common/Brand";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";

export function LandingPage() {
  return (
    <div className="min-h-screen bg-brand-950 text-white">
      <header className="mx-auto flex max-w-7xl items-center justify-between px-6 py-6 lg:px-10">
        <Brand />
        <Button asChild variant="outline">
          <Link to="/app/overview">Audit 시작하기</Link>
        </Button>
      </header>
      <main className="mx-auto grid max-w-7xl items-center gap-14 px-6 py-20 lg:grid-cols-[1fr_0.9fr] lg:px-10 lg:py-28">
        <section>
          <p className="mb-6 text-sm font-semibold uppercase tracking-widest text-brand-400">
            Financial UX Review
          </p>
          <h1 className="max-w-3xl text-4xl font-bold leading-tight tracking-tight sm:text-6xl">
            금융상품 UX를 <span className="text-brand-400">더 명확한 기준으로</span> 검토하세요.
          </h1>
          <p className="mt-7 max-w-xl text-base leading-8 text-white/70 sm:text-lg">
            금융위원회 다크패턴 가이드라인을 기반으로 AI가 금융상품 화면과 이용 흐름을 분석합니다.
          </p>
          <div className="mt-9 flex flex-wrap gap-4">
            <Button asChild variant="secondary">
              <Link to="/app/overview">
                Audit 시작하기 <ArrowRight aria-hidden="true" size={17} />
              </Link>
            </Button>
          </div>
          <p className="mt-10 flex items-center gap-2 text-sm text-white/65">
            <ShieldCheck aria-hidden="true" className="text-brand-400" size={18} />
            금융권 보안 기준을 준수하여 안전하게 데이터를 처리합니다.
          </p>
        </section>
        <Card className="border-white/10 bg-white/95 p-6 text-text shadow-2xl">
          <div className="flex items-center justify-between border-b border-border pb-5">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-brand-600">
                Overview
              </p>
              <h2 className="mt-1 text-xl font-bold">Insurance Signup Flow</h2>
            </div>
            <span className="rounded-full bg-brand-100 px-3 py-1 text-xs font-semibold text-brand-700">
              분석 중
            </span>
          </div>
          <div className="grid grid-cols-3 gap-3 py-6">
            {[
              ["탐지 항목", "7"],
              ["검토 필요", "2"],
              ["해결됨", "5"],
            ].map(([label, value]) => (
              <div className="rounded-control bg-background p-4" key={label}>
                <p className="text-xs text-muted">{label}</p>
                <p className="mt-2 text-2xl font-bold">{value}</p>
              </div>
            ))}
          </div>
          <div className="rounded-control border border-danger/25 bg-danger/5 p-5">
            <p className="text-xs font-bold text-brand-700">DP-04</p>
            <p className="mt-1 font-semibold">특정 옵션의 사전선택</p>
            <p className="mt-2 text-sm leading-6 text-muted">
              유료 옵션이 기본 선택되어 사용자의 능동적 선택을 침해할 수 있습니다.
            </p>
          </div>
        </Card>
      </main>
    </div>
  );
}
