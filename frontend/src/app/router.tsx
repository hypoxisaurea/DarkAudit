import { createBrowserRouter, Navigate } from "react-router-dom";

import { AppLayout } from "@/layouts/AppLayout";
import { PublicLayout } from "@/layouts/PublicLayout";
export const router = createBrowserRouter([
  {
    element: <PublicLayout />,
    children: [
      {
        path: "/",
        lazy: async () => ({
          Component: (await import("@/pages/landing/LandingPage")).LandingPage,
        }),
      },
    ],
  },
  {
    path: "/app",
    element: <AppLayout />,
    children: [
      { index: true, element: <Navigate to="overview" replace /> },
      {
        path: "overview",
        lazy: async () => ({
          Component: (await import("@/pages/overview/OverviewPage")).OverviewPage,
        }),
      },
      { path: "audits", element: <Navigate to="/app/audits/new" replace /> },
      {
        path: "audits/new",
        lazy: async () => ({
          Component: (await import("@/pages/audit-create/AuditCreatePage")).AuditCreatePage,
        }),
      },
    ],
  },
]);
