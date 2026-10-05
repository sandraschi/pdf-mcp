import { defineConfig } from "@playwright/test";

export default defineConfig({
    testDir: "./e2e",
    timeout: 60000,
    retries: 1,
    use: {
        baseURL: "http://localhost:11130",
        headless: true,
        screenshot: "only-on-failure",
    },
    // Self-contained: bring up backend + frontend so `just e2e` and CI work
    // without a pre-started stack. Locally an already-running stack is reused.
    webServer: [
        {
            command: "uv run --directory .. python run_server.py --mode http --port 11131",
            url: "http://127.0.0.1:11131/api/health",
            reuseExistingServer: !process.env.CI,
            timeout: 180000,
        },
        {
            command: "bun run dev",
            url: "http://localhost:11130",
            reuseExistingServer: !process.env.CI,
            timeout: 120000,
        },
    ],
});
