import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import { AuditCreatePage } from "@/pages/audit-create/AuditCreatePage";

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AuditCreatePage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("AuditCreatePage", () => {
  it("captures a URL for desktop and mobile and completes analysis", async () => {
    const user = userEvent.setup();
    renderPage();
    await user.type(screen.getByLabelText("진단 이름"), "URL 자동 진단");
    await user.type(screen.getByLabelText("검사할 웹사이트 주소"), "https://example.com/product");
    await user.click(screen.getByRole("button", { name: "분석 시작하기" }));
    expect(
      await screen.findByRole("heading", { name: "사이트를 캡처하고 분석하고 있습니다" }),
    ).toBeInTheDocument();
    expect(
      await screen.findByRole("heading", { name: "진단이 완료되었습니다" }, { timeout: 7_000 }),
    ).toBeInTheDocument();
  }, 10_000);

  it("keeps the manual screenshot workflow", async () => {
    const user = userEvent.setup();
    const { container } = renderPage();
    await user.click(screen.getByRole("tab", { name: "스크린샷 업로드" }));
    await user.type(screen.getByLabelText("진단 이름"), "업로드 진단");
    const fileInput = container.querySelector<HTMLInputElement>('input[type="file"]')!;
    await user.upload(fileInput, new File(["screen"], "screen.png", { type: "image/png" }));
    await user.click(screen.getByRole("button", { name: "분석 시작하기" }));
    expect(
      await screen.findByRole("heading", { name: "금융 UX를 분석하고 있습니다" }),
    ).toBeInTheDocument();
    expect(
      await screen.findByRole("heading", { name: "진단이 완료되었습니다" }, { timeout: 7_000 }),
    ).toBeInTheDocument();
  }, 10_000);
});
