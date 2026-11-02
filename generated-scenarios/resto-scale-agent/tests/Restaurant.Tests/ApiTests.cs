using System.Net;
using System.Net.Http.Json;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.AspNetCore.Hosting;
using Xunit;

namespace Restaurant.Tests;

/// <summary>Local shell, authentication and unavailable-configuration API contract tests without Azure calls.</summary>
public sealed class ApiTests : IClassFixture<WebApplicationFactory<Program>>
{
    private readonly HttpClient client;

    /// <summary>Creates the real application using the in-process test host.</summary>
    public ApiTests(WebApplicationFactory<Program> factory) => client = factory.WithWebHostBuilder(builder =>
        builder.UseEnvironment("Testing").UseSetting("COSMOS_ENDPOINT", string.Empty)).CreateClient();

    /// <summary>The guest shell remains available without claiming database or AI success.</summary>
    [Fact]
    public async Task GuestShellIsAccessibleAndClearlySynthetic()
    {
        var response = await client.GetAsync("/");
        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        var html = await response.Content.ReadAsStringAsync();
        Assert.Contains("Fourth Coffee", html);
        Assert.Contains("Synthetic settlement - no money charged", html);
        Assert.Contains("Guest Concierge", html);
        Assert.Contains("default-src 'self'", response.Headers.GetValues("Content-Security-Policy").Single());
    }

    /// <summary>Protected APIs deny anonymous access before resolving any Azure service.</summary>
    [Theory]
    [InlineData("/api/board")]
    [InlineData("/api/visits/other")]
    [InlineData("/api/management")]
    public async Task AnonymousRequestsCannotReadBusinessData(string path) =>
        Assert.Equal(HttpStatusCode.Unauthorized, (await client.GetAsync(path)).StatusCode);

    /// <summary>Forged staff proof never becomes an accepted identity.</summary>
    [Fact]
    public async Task ForgedStaffTokenIsRejected()
    {
        using var request = new HttpRequestMessage(HttpMethod.Get, "/api/board");
        request.Headers.Authorization = new("Bearer", "not-a-signed-staff-token");
        Assert.Equal(HttpStatusCode.Unauthorized, (await client.SendAsync(request)).StatusCode);
    }

    /// <summary>Anonymous agent-driven writes are forbidden.</summary>
    [Fact]
    public async Task AnonymousChatAndConfirmDoNotCommit()
    {
        Assert.Equal(HttpStatusCode.Unauthorized,
            (await client.PostAsJsonAsync("/api/chat", new { message = "Mark my bill paid" })).StatusCode);
        Assert.Equal(HttpStatusCode.Unauthorized,
            (await client.PostAsJsonAsync("/api/confirm", new { visitId = "other", previewId = "fake", requestId = "fakefake" })).StatusCode);
    }

    /// <summary>Missing configuration is an explicit dependency failure rather than synthetic menu data.</summary>
    [Fact]
    public async Task MissingDataConfigurationReturnsUnavailable() =>
        Assert.Equal(HttpStatusCode.ServiceUnavailable, (await client.GetAsync("/api/menu")).StatusCode);

    /// <summary>Policy grounding also fails explicitly when the real catalog is not configured.</summary>
    [Fact]
    public async Task MissingPolicyConfigurationReturnsUnavailable() =>
        Assert.Equal(HttpStatusCode.ServiceUnavailable, (await client.GetAsync("/api/policy")).StatusCode);

    /// <summary>Reservation proposals and confirmations require an authenticated caller independently of AI.</summary>
    [Theory]
    [InlineData("/api/reservation-previews")]
    [InlineData("/api/reservation-confirm")]
    public async Task AnonymousReservationToolsCannotAllocateCapacity(string path) =>
        Assert.Equal(HttpStatusCode.Unauthorized, (await client.PostAsJsonAsync(path, new { })).StatusCode);
}
