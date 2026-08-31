import { BookOpen, ChartNoAxesColumn, ClipboardList, Home, Settings } from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";

import { Brand } from "@/components/common/Brand";
import { cn } from "@/lib/cn";

const navigation = [
  { label: "Overview", icon: Home, to: "/app/overview" },
  { label: "Audits", icon: ClipboardList, to: "/app/audits" },
  { label: "Guidelines", icon: BookOpen, to: "/app/guidelines" },
  { label: "Benchmark", icon: ChartNoAxesColumn, to: "/app/benchmark" },
  { label: "Settings", icon: Settings, to: "/app/settings" },
];

export function AppLayout() {
  return (
    <div className="min-h-screen bg-background lg:grid lg:grid-cols-[280px_1fr]">
      <aside className="hidden bg-brand-950 p-7 text-white lg:flex lg:flex-col">
        <Brand />
        <nav aria-label="주요 메뉴" className="mt-10 space-y-2">
          {navigation.map(({ label, icon: Icon, to }) => (
            <NavLink
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-control px-4 py-3 text-sm font-medium text-white/80",
                  isActive && "bg-brand-600 text-white",
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
      </aside>
      <main className="min-w-0 p-5 sm:p-8 lg:p-10">
        <Outlet />
      </main>
    </div>
  );
}
