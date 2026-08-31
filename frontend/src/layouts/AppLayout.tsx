import {
  Bell,
  BookOpen,
  Building2,
  ChartNoAxesColumn,
  ChevronDown,
  ClipboardList,
  Home,
  Menu,
  Settings,
  ShieldCheck,
} from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";

import { Brand } from "@/components/common/Brand";
import { cn } from "@/lib/cn";

const navigation = [
  { label: "대시보드", icon: Home, to: "/app/overview" },
  { label: "진단 관리", icon: ClipboardList, to: "/app/audits" },
  { label: "검토 기준", icon: BookOpen, to: "/app/guidelines" },
  { label: "비교 분석", icon: ChartNoAxesColumn, to: "/app/benchmark" },
  { label: "설정", icon: Settings, to: "/app/settings" },
];

function Sidebar() {
  return (
    <aside className="fixed inset-y-0 left-0 z-20 hidden w-[280px] flex-col bg-brand-950 p-5 text-white lg:flex">
      <div className="flex items-center justify-between px-2 py-2">
        <Brand />
        <button
          aria-label="사이드바 접기"
          className="rounded-control border border-white/20 p-2 text-white/80"
        >
          <Menu size={17} />
        </button>
      </div>
      <nav aria-label="주요 메뉴" className="mt-7 space-y-2">
        {navigation.map(({ label, icon: Icon, to }) => (
          <NavLink
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-control px-4 py-3.5 text-sm font-medium text-white/75 transition-colors hover:bg-white/5 hover:text-white",
                isActive && "bg-brand-600 text-white shadow-lg shadow-black/10",
              )
            }
            key={to}
            to={to}
          >
            <Icon aria-hidden="true" size={19} />
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="mt-auto space-y-4">
        <div className="rounded-card border border-white/20 p-4">
          <p className="flex items-center gap-2 text-sm font-semibold">
            <ShieldCheck className="text-brand-400" size={21} /> 안전한 규제 준수
          </p>
          <p className="mt-3 text-xs leading-5 text-white/55">
            금융보안 및 개인정보 보호 기준을 준수하여 안전하게 운영됩니다.
          </p>
          <button className="mt-4 text-xs font-semibold text-brand-400">자세히 보기 →</button>
        </div>
        <button className="flex w-full items-center gap-3 rounded-card border border-white/20 p-4 text-left">
          <Building2 size={23} />
          <span className="min-w-0 flex-1">
            <span className="block truncate text-sm font-semibold">다온손해보험</span>
            <span className="mt-1 inline-block rounded bg-white/10 px-1.5 py-0.5 text-[10px] text-white/60">
              기업용
            </span>
          </span>
          <ChevronDown size={16} />
        </button>
      </div>
    </aside>
  );
}

function AppHeader() {
  return (
    <header className="flex h-16 items-center justify-between border-b border-border bg-surface px-5 lg:h-18 lg:px-9">
      <div className="lg:hidden">
        <Brand dark />
      </div>
      <div className="hidden lg:block" />
      <div className="flex items-center gap-4">
        <button aria-label="알림" className="relative p-2 text-text">
          <Bell size={20} />
          <span className="absolute right-1.5 top-1.5 size-2 rounded-full border-2 border-white bg-success" />
        </button>
        <span className="flex size-9 items-center justify-center rounded-full bg-brand-950 text-xs font-semibold text-white">
          HJ
        </span>
        <div className="hidden sm:block">
          <p className="text-sm font-semibold">김현진</p>
          <p className="text-xs text-muted">준법감시 담당자</p>
        </div>
        <ChevronDown className="hidden text-muted sm:block" size={16} />
      </div>
    </header>
  );
}

export function AppLayout() {
  return (
    <div className="min-h-screen bg-background lg:pl-[280px]">
      <Sidebar />
      <AppHeader />
      <main className="min-w-0 p-4 sm:p-6 lg:p-8">
        <Outlet />
      </main>
    </div>
  );
}
