from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field

from playwright.sync_api import TimeoutError, expect, sync_playwright


@dataclass
class SmokeResult:
    checks: list[str] = field(default_factory=list)
    console_errors: list[str] = field(default_factory=list)
    request_failures: list[str] = field(default_factory=list)

    def ok(self, message: str) -> None:
        self.checks.append(message)

    def as_json(self) -> str:
        return json.dumps(
            {
                "checks": self.checks,
                "console_errors": self.console_errors,
                "request_failures": self.request_failures,
            },
            ensure_ascii=False,
            indent=2,
        )


def run_frontend_smoke(base_url: str, source_path: str, question: str, timeout_ms: int) -> SmokeResult:
    result = SmokeResult()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.add_init_script("localStorage.setItem('aiKnowledgeAgent.language', 'en')")
        page.on(
            "console",
            lambda message: result.console_errors.append(message.text)
            if message.type in {"error", "warning"}
            else None,
        )
        page.on(
            "requestfailed",
            lambda request: result.request_failures.append(
                f"{request.method} {request.url}: {request.failure}"
            ),
        )
        page.set_default_timeout(timeout_ms)

        page.goto(f"{base_url}/", wait_until="networkidle")
        expect(page.locator("#statusBar")).to_be_visible()
        result.ok("app loaded")

        page.goto(f"{base_url}/goal", wait_until="networkidle")
        expect(page.locator("pre")).to_contain_text("AI Knowledge Agent Final Goal")
        result.ok("/goal loaded")

        page.goto(f"{base_url}/#documents", wait_until="networkidle")
        page.fill("#sourcePath", source_path)
        page.click("#saveSourceButton")
        page.wait_for_function(
            "document.querySelector('#statusBar')?.textContent.includes('saved')"
            " || document.querySelector('#statusBar')?.textContent.includes('已保存')",
        )
        expect(page.locator("#documentSourcesList")).to_contain_text("raw")
        result.ok("document source saved through UI")
        page.click("#indexButton")
        page.wait_for_function(
            "document.querySelector('#statusBar')?.textContent.includes('Indexed')"
            " || document.querySelector('#statusBar')?.textContent.includes('已索引')",
        )
        expect(page.locator("#documentsList")).to_contain_text("product-brief.md")
        expect(page.locator(".document-controls button").first).to_be_visible()
        result.ok("sample documents indexed through UI")

        page.click("nav a[data-page='ask']")
        page.fill("#questionInput", question)
        page.click("#askButton")
        page.wait_for_selector(".chat-message.assistant:not(.pending) .chat-sources")
        expect(page.locator(".chat-message.user").last).to_contain_text(question)
        expect(page.locator(".chat-message.assistant").last).to_contain_text("product-brief.md")
        expect(page.locator(".chat-message.assistant .chat-sources").last).to_be_visible()
        result.ok("chat answer rendered with citations")

        page.click("nav a[data-page='evaluations']")
        expect(page.locator("#evalButton")).to_be_visible()
        page.click("#evalButton")
        expect(page.locator("#evalBox")).to_contain_text("retrieval_hit_rate")
        page.wait_for_function("document.querySelector('#evalHistoryList')?.textContent.includes('eval-')")
        expect(page.locator("#evalHistoryList")).to_contain_text("eval-")
        result.ok("evaluation run rendered with history")

        browser.close()

    if result.console_errors or result.request_failures:
        raise AssertionError(result.as_json())
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Browser-driven frontend smoke test.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8766")
    parser.add_argument("--source-path", default="./data/raw")
    parser.add_argument(
        "--question",
        default="How does the app preserve local data?",
    )
    parser.add_argument("--timeout-ms", type=int, default=15000)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = run_frontend_smoke(args.base_url, args.source_path, args.question, args.timeout_ms)
    except TimeoutError as error:
        print(f"Frontend smoke timed out: {error}", file=sys.stderr)
        return 1
    except Exception as error:
        print(f"Frontend smoke failed: {error}", file=sys.stderr)
        return 1
    print(result.as_json())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
