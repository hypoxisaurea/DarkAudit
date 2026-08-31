import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import { AuditCreatePage } from "@/pages/audit-create/AuditCreatePage";

describe("AuditCreatePage", () => {
  it("creates an audit and completes mock analysis", async () => {
    const user = userEvent.setup();
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const { container } = render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <AuditCreatePage />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    await user.type(screen.getByLabelText("Audit 이름"), "테스트 가입 Flow");
    const fileInput = container.querySelector<HTMLInputElement>('input[type="file"]')!;
    await user.upload(fileInput, new File(["screen"], "screen.png", { type: "image/png" }));
    await user.click(screen.getByRole("button", { name: "분석 시작하기" }));

    expect(
      await screen.findByRole("heading", { name: "금융 UX를 분석하고 있습니다" }),
    ).toBeInTheDocument();
    expect(
      await screen.findByRole(
        "heading",
        { name: "Audit 분석이 완료되었습니다" },
        { timeout: 7_000 },
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /결과 확인하기/ })).toHaveAttribute(
      "href",
      expect.stringContaining("/app/overview?audit="),
    );
  }, 10_000);
});
