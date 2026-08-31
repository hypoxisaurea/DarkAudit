import { delay, http, HttpResponse } from "msw";

import { dashboardFixture } from "@/mocks/fixtures/dashboard";

export const handlers = [
  http.get("/api/v1/dashboard/summary", async () => {
    await delay(350);
    return HttpResponse.json(dashboardFixture);
  }),
];
