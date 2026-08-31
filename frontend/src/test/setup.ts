import "@testing-library/jest-dom/vitest";

import { server } from "@/mocks/server";

Object.defineProperty(window, "scrollTo", { value: vi.fn(), writable: true });
Object.defineProperty(URL, "createObjectURL", {
  value: vi.fn(() => "blob:preview"),
  writable: true,
});
Object.defineProperty(URL, "revokeObjectURL", { value: vi.fn(), writable: true });

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
