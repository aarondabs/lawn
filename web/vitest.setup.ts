import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// Auto-cleanup only registers itself under vitest globals; we import
// explicitly, so unmount between tests here.
afterEach(() => {
  cleanup();
});

// jsdom implements neither; components call them incidentally.
if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = () => {};
}
