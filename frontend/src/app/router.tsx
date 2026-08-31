import { createBrowserRouter, Navigate } from "react-router-dom";

import { AppLayout } from "@/layouts/AppLayout";
import { PublicLayout } from "@/layouts/PublicLayout";
import { LandingPage } from "@/pages/landing/LandingPage";
import { OverviewPage } from "@/pages/overview/OverviewPage";

export const router = createBrowserRouter([
  {
    element: <PublicLayout />,
    children: [{ path: "/", element: <LandingPage /> }],
  },
  {
    path: "/app",
    element: <AppLayout />,
    children: [
      { index: true, element: <Navigate to="overview" replace /> },
      { path: "overview", element: <OverviewPage /> },
    ],
  },
]);
