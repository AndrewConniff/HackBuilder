using System.Diagnostics;
using System.Net;
using System.Net.Sockets;
using Microsoft.Playwright;
using Xunit;

namespace Restaurant.Tests;

/// <summary>Real Chromium local shell/negative checks; full business and agent journeys remain deployment acceptance.</summary>
public sealed class BrowserTests
{
    /// <summary>Runs the application on a dedicated local port and verifies desktop/mobile behavior without Azure.</summary>
    [Fact]
    public async Task RealBrowserRendersBothWorkspacesAndExplicitUnavailableState()
    {
        var folder = new DirectoryInfo(AppContext.BaseDirectory);
        while (folder is not null && !File.Exists(Path.Combine(folder.FullName, "Restaurant.slnx"))) folder = folder.Parent;
        var root = folder?.FullName ?? throw new DirectoryNotFoundException("Scenario solution root not found.");
        var listener = new TcpListener(IPAddress.Loopback, 0);
        listener.Start();
        var port = ((IPEndPoint)listener.LocalEndpoint).Port;
        listener.Stop();
        var url = $"http://127.0.0.1:{port}";
        var contentRoot = Path.Combine(root, "src", "Restaurant.Web");
        var assembly = Path.Combine(contentRoot, "bin", "Debug", "net10.0", "Restaurant.Web.dll");
        var start = new ProcessStartInfo("dotnet")
        {
            UseShellExecute = false, RedirectStandardOutput = true, RedirectStandardError = true,
            WorkingDirectory = contentRoot
        };
        foreach (var argument in new[] { assembly, "--urls", url, "--contentRoot", contentRoot })
            start.ArgumentList.Add(argument);
        start.Environment["APP_ROLE"] = "web";
        start.Environment["ASPNETCORE_ENVIRONMENT"] = "Testing";
        foreach (var key in new[] { "COSMOS_ENDPOINT", "SERVICE_BUS_NAMESPACE", "FOUNDRY_PROJECT_ENDPOINT",
            "APPLICATIONINSIGHTS_CONNECTION_STRING", "STAFF_AUTH_JSON", "STAFF_AUTH_FILE", "CHAT_BASE_URL" })
            start.Environment.Remove(key);
        using var server = Process.Start(start) ?? throw new InvalidOperationException("Local app process did not start.");
        var stdout = server.StandardOutput.ReadToEndAsync();
        var stderr = server.StandardError.ReadToEndAsync();
        var evidence = Path.Combine(root, "evidence", "local-entra-repair-30bc1eeb", "browser");
        Directory.CreateDirectory(evidence);
        try
        {
            using var http = new HttpClient { Timeout = TimeSpan.FromSeconds(2) };
            var responsive = false;
            for (var attempt = 0; attempt < 30 && !server.HasExited; attempt++)
            {
                try { responsive = (await http.GetAsync(url + "/health/live")).IsSuccessStatusCode; }
                catch (HttpRequestException) { await Task.Delay(100); }
                if (responsive) break;
                await Task.Delay(100);
            }
            Assert.True(responsive, "Started local application did not become responsive.");
            using var playwright = await Playwright.CreateAsync();
            await using var browser = await playwright.Chromium.LaunchAsync(new() { Headless = true });
            foreach (var width in new[] { 1440, 390 })
            {
                var page = await browser.NewPageAsync(new() { ViewportSize = new() { Width = width, Height = 1000 } });
                await page.GotoAsync(url);
                await Assertions.Expect(page).ToHaveTitleAsync("Fourth Coffee | Guest journey");
                await Assertions.Expect(page.GetByRole(AriaRole.Heading, new() { Name = "Your visit, from reservation to feedback" }))
                    .ToBeVisibleAsync();
                await Assertions.Expect(page.Locator("#notice")).ToContainTextAsync("required service is unavailable");
                Assert.True(await page.EvaluateAsync<bool>("document.documentElement.scrollWidth <= window.innerWidth"));
                await page.ScreenshotAsync(new() { Path = Path.Combine(evidence, $"guest-{width}.png"), FullPage = true });
                await page.GetByRole(AriaRole.Link, new() { Name = "Staff and kitchen" }).ClickAsync();
                await Assertions.Expect(page).ToHaveTitleAsync("Fourth Coffee | Staff and kitchen");
                await Assertions.Expect(page.GetByRole(AriaRole.Button, new() { Name = "Sign in with Microsoft Entra" }))
                    .ToBeVisibleAsync();
                Assert.Equal(0, await page.Locator("input[type=password]").CountAsync());
                await page.GetByRole(AriaRole.Button, new() { Name = "Sign in with Microsoft Entra" }).ClickAsync();
                await Assertions.Expect(page.Locator("#notice")).ToContainTextAsync("Entra staff sign-in is not configured");
                await Assertions.Expect(page.Locator("#board")).ToContainTextAsync("No staff data loaded");
                Assert.True(await page.EvaluateAsync<bool>("document.documentElement.scrollWidth <= window.innerWidth"));
                await page.ScreenshotAsync(new() { Path = Path.Combine(evidence, $"staff-{width}.png"), FullPage = true });
                await page.CloseAsync();
            }
        }
        finally
        {
            if (!server.HasExited) server.Kill(entireProcessTree: true);
            await server.WaitForExitAsync();
            await File.WriteAllTextAsync(Path.Combine(evidence, "local-server.txt"), await stdout + await stderr);
        }
    }
}
