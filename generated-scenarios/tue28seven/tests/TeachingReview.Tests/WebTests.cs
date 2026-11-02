using System.Net;
using System.Text.Json;
using System.Text.RegularExpressions;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.Extensions.Configuration;
using TeachingReview.Web.Models;
using TeachingReview.Web.Services;
using Xunit;

namespace TeachingReview.Tests;

/// <summary>Checks HTTPS local authentication, antiforgery and account lockout.</summary>
public sealed class WebTests
{
    private sealed class Factory : WebApplicationFactory<Program>
    {
        internal readonly string DirectoryPath = Path.Combine(Path.GetTempPath(), "tue28seven-" + Guid.NewGuid().ToString("N"));
        internal readonly string Password = Guid.NewGuid().ToString("N");

        protected override void ConfigureWebHost(IWebHostBuilder builder)
        {
            Directory.CreateDirectory(DirectoryPath);
            var teacher = new Teacher(1, "author", "Airi Ilves", "Author", string.Empty);
            teacher = teacher with { PasswordHash = new PasswordHasher<Teacher>().HashPassword(teacher, Password) };
            File.WriteAllText(Path.Combine(DirectoryPath, "state.json"),
                JsonSerializer.Serialize(new SchoolState([teacher], [])));
            builder.UseEnvironment("Testing").UseSetting("StorageMode", "Local").UseSetting("PrivateDirectory", DirectoryPath);
        }

        protected override void Dispose(bool disposing)
        {
            base.Dispose(disposing);
            if (disposing && Directory.Exists(DirectoryPath))
            {
                foreach (var file in Directory.GetFiles(DirectoryPath)) File.Delete(file);
                var keys = Path.Combine(DirectoryPath, "keys");
                if (Directory.Exists(keys))
                {
                    foreach (var file in Directory.GetFiles(keys)) File.Delete(file);
                    Directory.Delete(keys);
                }
                Directory.Delete(DirectoryPath);
            }
        }
    }

    private static HttpClient Client(Factory factory) => factory.CreateClient(new WebApplicationFactoryClientOptions
    {
        BaseAddress = new Uri("https://localhost"), AllowAutoRedirect = false
    });

    private static async Task<HttpResponseMessage> Login(HttpClient client, string password)
    {
        var page = await client.GetStringAsync("/Login");
        var token = Regex.Match(page, "name=\"__RequestVerificationToken\"[^>]*value=\"([^\"]+)\"").Groups[1].Value;
        Assert.NotEmpty(token);
        return await client.PostAsync("/Login", new FormUrlEncodedContent(new Dictionary<string, string>
        {
            ["Username"] = "author", ["Password"] = password, ["__RequestVerificationToken"] = token
        }));
    }

    /// <summary>Checks anonymous denial, secure cookie issuance, authenticated access and CSRF rejection.</summary>
    [Fact]
    public async Task AuthenticationAndAntiforgeryAreRequired()
    {
        using var factory = new Factory();
        using var client = Client(factory);
        Assert.Equal(HttpStatusCode.Redirect, (await client.GetAsync("/")).StatusCode);
        var login = await Login(client, factory.Password);
        Assert.Equal(HttpStatusCode.Redirect, login.StatusCode);
        var cookie = string.Join(";", login.Headers.GetValues("Set-Cookie"));
        Assert.Contains("secure", cookie.ToLowerInvariant());
        Assert.Contains("httponly", cookie.ToLowerInvariant());
        Assert.Equal(HttpStatusCode.OK, (await client.GetAsync("/")).StatusCode);
        var mutation = await client.PostAsync("/", new FormUrlEncodedContent(new Dictionary<string, string>
        {
            ["id"] = "1", ["version"] = "1", ["action"] = "Approve"
        }));
        Assert.Equal(HttpStatusCode.BadRequest, mutation.StatusCode);
        var dashboard = await client.GetStringAsync("/");
        var token = Regex.Match(dashboard, "name=\"__RequestVerificationToken\"[^>]*value=\"([^\"]+)\"").Groups[1].Value;
        var logout = await client.PostAsync("/?handler=Logout", new FormUrlEncodedContent(
            new Dictionary<string, string> { ["__RequestVerificationToken"] = token }));
        Assert.Equal(HttpStatusCode.Redirect, logout.StatusCode);
        Assert.Equal(HttpStatusCode.Redirect, (await client.GetAsync("/")).StatusCode);
    }

    /// <summary>Checks five failed attempts lock the durable account.</summary>
    [Fact]
    public async Task FailedLoginLocksAccountWithoutGrantingSession()
    {
        using var factory = new Factory();
        using var client = Client(factory);
        for (var attempt = 0; attempt < 5; attempt++)
            Assert.Equal(HttpStatusCode.OK, (await Login(client, "incorrect-test-password")).StatusCode);
        var blocked = await Login(client, factory.Password);
        Assert.Equal(HttpStatusCode.OK, blocked.StatusCode);
        Assert.Equal(HttpStatusCode.Redirect, (await client.GetAsync("/")).StatusCode);
        var state = JsonSerializer.Deserialize<SchoolState>(
            await File.ReadAllTextAsync(Path.Combine(factory.DirectoryPath, "state.json")))!;
        Assert.True(state.Teachers[0].LockedUntil > DateTimeOffset.UtcNow);
    }

    /// <summary>Verifies private initialization separates roles and stores only salted hashes in durable state.</summary>
    [Fact]
    public async Task LocalInitializationSeparatesPrivateCredentialsAndRefusesOverwrite()
    {
        var directory = Path.Combine(Path.GetTempPath(), "tue28seven-init-" + Guid.NewGuid().ToString("N"));
        var configuration = new ConfigurationBuilder().AddInMemoryCollection(
            new Dictionary<string, string?> { ["PrivateDirectory"] = directory }).Build();
        var names = new[] { "state.json", "participant-access.json", "coach-access.json" };
        try
        {
            await Initialization.RunAsync(AppContext.BaseDirectory, configuration, true);
            var state = JsonSerializer.Deserialize<SchoolState>(
                await File.ReadAllTextAsync(Path.Combine(directory, "state.json")))!;
            using var participant = JsonDocument.Parse(
                await File.ReadAllTextAsync(Path.Combine(directory, "participant-access.json")));
            using var coach = JsonDocument.Parse(
                await File.ReadAllTextAsync(Path.Combine(directory, "coach-access.json")));
            Assert.Equal(2, participant.RootElement.GetArrayLength());
            Assert.Single(coach.RootElement.EnumerateArray());
            Assert.Equal("Lead", coach.RootElement[0].GetProperty("Role").GetString());
            var passwords = participant.RootElement.EnumerateArray().Concat(coach.RootElement.EnumerateArray())
                .Select(x => x.GetProperty("Password").GetString()!).ToArray();
            Assert.Equal(3, passwords.Distinct().Count());
            foreach (var teacher in state.Teachers)
            {
                var access = participant.RootElement.EnumerateArray().Concat(coach.RootElement.EnumerateArray())
                    .Single(x => x.GetProperty("Username").GetString() == teacher.Username);
                var password = access.GetProperty("Password").GetString()!;
                Assert.DoesNotContain(password, await File.ReadAllTextAsync(Path.Combine(directory, "state.json")));
                Assert.NotEqual(PasswordVerificationResult.Failed,
                    new PasswordHasher<Teacher>().VerifyHashedPassword(teacher, teacher.PasswordHash, password));
            }
            await Assert.ThrowsAsync<InvalidOperationException>(() =>
                Initialization.RunAsync(AppContext.BaseDirectory, configuration, true));
        }
        finally
        {
            foreach (var name in names)
            {
                var path = Path.Combine(directory, name);
                if (File.Exists(path)) File.Delete(path);
            }
            if (Directory.Exists(directory)) Directory.Delete(directory);
        }
    }
}
