import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { LandingPage } from "@/pages/landing/LandingPage";

describe("LandingPage", () => {
  it("introduces the product and links to the audit dashboard", () => {
    render(
      <MemoryRouter>
        <LandingPage />
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { name: /금융상품 UX를/ })).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Audit 시작하기" })[0]).toHaveAttribute(
      "href",
      "/app/overview",
    );
  });
});
