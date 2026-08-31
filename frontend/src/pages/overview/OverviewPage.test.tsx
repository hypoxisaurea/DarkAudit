import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import { OverviewPage } from "@/pages/overview/OverviewPage";

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/app/overview"]}>
        <OverviewPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("OverviewPage", () => {
  it("loads dashboard data and changes the selected audit", async () => {
    const user = userEvent.setup();
    renderPage();

    expect(screen.getByLabelText("대시보드 불러오는 중")).toBeInTheDocument();
    expect(
      await screen.findByRole("heading", { name: "Insurance Signup Flow v1" }),
    ).toBeInTheDocument();

    await user.click(screen.getByText("Savings Account Flow v2"));

    expect(screen.getByRole("heading", { name: "Savings Account Flow v2" })).toBeInTheDocument();
    expect(screen.getByText("탐지된 항목이 없습니다")).toBeInTheDocument();
  });
});
