using System.Net;
using System.Security.Claims;
using System.Text.Json;
using System.Text.RegularExpressions;
using System.Xml.Linq;
using Azure.Core;
using Azure.Core.Pipeline;
using Azure.Data.Tables;
using Azure.Monitor.OpenTelemetry.Exporter;
using Microsoft.AspNetCore.DataProtection;
using Microsoft.AspNetCore.DataProtection.KeyManagement;
using Microsoft.AspNetCore.DataProtection.Repositories;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Microsoft.Extensions.Logging.Abstractions;
using Woodgrove.Web.Models;
using Woodgrove.Web.Services;

namespace Woodgrove.Tests;

/// <summary>HTTP and authentication tests with isolated test-only Table and session-key providers, never model mocks.</summary>
public sealed class HttpTests
{
    /// <summary>Requires authentication and rejects a forged sign-in without a CSRF token.</summary>
    [Fact]
    public async Task AnonymousAndCsrfDenials()
    {
        await using var factory = new Fixture();
        using var client = factory.Client();
        var anonymous = await client.GetAsync("/");
        Assert.Equal(HttpStatusCode.Redirect, anonymous.StatusCode);
        Assert.StartsWith("/Login", anonymous.Headers.Location!.AbsolutePath);
        var forged = await client.PostAsync("/Login", new FormUrlEncodedContent(
            new Dictionary<string, string> { ["Username"] = "customer-001", ["Password"] = factory.Password }));
        Assert.Equal(HttpStatusCode.BadRequest, forged.StatusCode);
    }

    /// <summary>Proves secure local login, customer isolation, wrong-role denial and CSRF-protected logout.</summary>
    [Fact]
    public async Task CustomerLoginIsolationAndLogout()
    {
        await using var factory = new Fixture();
        using var client = factory.Client();
        var signedIn = await SignIn(client, "customer-001", factory.Password);
        Assert.Equal(HttpStatusCode.Redirect, signedIn.StatusCode);
        var cookie = string.Join(";", signedIn.Headers.GetValues("Set-Cookie"));
        Assert.Contains("__Host-Woodgrove=", cookie);
        Assert.Contains("secure", cookie.ToLowerInvariant());
        Assert.Contains("httponly", cookie.ToLowerInvariant());
        Assert.Contains("samesite=strict", cookie.ToLowerInvariant());
        var page = await client.GetStringAsync("/");
        Assert.Contains(Fixture.OwnOrder, page);
        Assert.DoesNotContain(Fixture.OtherOrder, page);
        var forbiddenOrder = await client.GetAsync("/?id=" + Fixture.OtherOrder);
        Assert.Equal(HttpStatusCode.BadRequest, forbiddenOrder.StatusCode);
        Assert.DoesNotContain(Fixture.OtherOrder, await forbiddenOrder.Content.ReadAsStringAsync());
        var wrongRole = await client.PostAsync("/?handler=Disrupt", Form(page,
            ("id", Fixture.OwnOrder), ("kind", "tool-timeout"), ("requestId", "attempt")));
        Assert.Equal(HttpStatusCode.Redirect, wrongRole.StatusCode);
        Assert.Equal("/Denied", wrongRole.Headers.Location!.AbsolutePath);
        Assert.Equal(HttpStatusCode.MethodNotAllowed, (await client.GetAsync("/Logout")).StatusCode);
        Assert.Equal(HttpStatusCode.BadRequest,
            (await client.PostAsync("/Logout", new FormUrlEncodedContent([]))).StatusCode);
        Assert.Equal(HttpStatusCode.Redirect, (await client.PostAsync("/Logout", Form(page))).StatusCode);
        Assert.Equal(HttpStatusCode.Redirect, (await client.GetAsync("/")).StatusCode);
    }

    /// <summary>Only the operator can inject fixture failures; operator accounts cannot create customer carts.</summary>
    [Fact]
    public async Task OperatorControlsDoNotImpersonateCustomers()
    {
        await using var factory = new Fixture();
        using var client = factory.Client();
        await SignIn(client, "operator-001", factory.Password);
        var page = await client.GetStringAsync("/?id=" + Fixture.OwnOrder);
        Assert.Contains(Fixture.OtherOrder, page);
        var injection = await client.PostAsync("/?handler=Disrupt", Form(page,
            ("id", Fixture.OwnOrder), ("kind", "tool-timeout"), ("requestId", "fixture")));
        Assert.Equal(HttpStatusCode.OK, injection.StatusCode);
        var order = JsonSerializer.Deserialize<GroceryOrder>(
            factory.Memory.Rows["order-" + Fixture.OwnOrder].GetString("Json")!)!;
        Assert.Equal("tool-timeout", order.Disruption);
        Assert.Equal("Draft", order.Status);
        Assert.Equal(0, order.Requests);
        var create = await client.PostAsync("/?handler=Create", Form(page));
        Assert.Equal(HttpStatusCode.Redirect, create.StatusCode);
        Assert.Equal("/Denied", create.Headers.Location!.AbsolutePath);
    }

    /// <summary>Five failed logins persist a lockout that also rejects the correct password.</summary>
    [Fact]
    public async Task DurableLockoutAndServerAssignedRole()
    {
        await using var factory = new Fixture();
        var accounts = new LocalAccounts(new MemoryTableService(factory.Memory), NullLogger<LocalAccounts>.Instance);
        var principal = await accounts.AuthenticateAsync("customer-001", factory.Password, CancellationToken.None);
        Assert.Equal("customer-001", principal.FindFirstValue(ClaimTypes.NameIdentifier));
        Assert.True(principal.IsInRole("Customer"));
        Assert.False(principal.IsInRole("Operator"));
        for (var attempt = 0; attempt < 5; attempt++)
            await Assert.ThrowsAsync<PolicyException>(() =>
                accounts.AuthenticateAsync("customer-001", "invalid-test-password", CancellationToken.None));
        Assert.Equal(5, factory.Memory.Rows["customer-001"].GetInt32("Failures"));
        Assert.True(factory.Memory.Rows["customer-001"].GetDateTimeOffset("LockedUntil") > DateTimeOffset.UtcNow);
        var locked = await Assert.ThrowsAsync<PolicyException>(() =>
            accounts.AuthenticateAsync("customer-001", factory.Password, CancellationToken.None));
        Assert.Contains("locked", locked.Message);
    }

    /// <summary>Missing or insecure endpoint configuration fails before constructing a running application.</summary>
    [Theory]
    [InlineData(null, "StorageTableEndpoint is required")]
    [InlineData("http://table.example.invalid", "absolute HTTPS")]
    public async Task MissingAndInsecureConfigurationFailExplicitly(string? endpoint, string expected)
    {
        await using var factory = new Fixture { TableEndpoint = endpoint };
        var error = Assert.Throws<InvalidOperationException>(() => factory.Client());
        Assert.Contains(expected, error.Message);
    }

    /// <summary>An empty order list is legitimate; a missing backend catalog is an explicit error, never a fallback.</summary>
    [Fact]
    public async Task EmptyOrdersAndMissingCatalogAreDifferentStates()
    {
        await using var factory = new Fixture();
        factory.Memory.Rows.Remove("order-" + Fixture.OwnOrder);
        factory.Memory.Rows.Remove("order-" + Fixture.OtherOrder);
        using var client = factory.Client();
        await SignIn(client, "customer-001", factory.Password);
        Assert.Contains("No orders yet.", await client.GetStringAsync("/"));
        factory.Memory.Rows.Remove("product-001");
        var failure = await client.GetAsync("/");
        Assert.Equal(HttpStatusCode.BadRequest, failure.StatusCode);
        Assert.Contains("catalog has not been installed", await failure.Content.ReadAsStringAsync());
    }

    /// <summary>A durable account security-stamp change invalidates a previously authenticated cookie.</summary>
    [Fact]
    public async Task RevokedSessionDoesNotRetainAccess()
    {
        await using var factory = new Fixture();
        using var client = factory.Client();
        await SignIn(client, "customer-001", factory.Password);
        var account = MemoryTable.Clone(factory.Memory.Rows["customer-001"]);
        account["Stamp"] = Guid.NewGuid().ToString("N");
        factory.Memory.Put(account);
        Assert.Equal(HttpStatusCode.Redirect, (await client.GetAsync("/")).StatusCode);
    }

    private static async Task<HttpResponseMessage> SignIn(HttpClient client, string username, string password)
    {
        var login = await client.GetStringAsync("/Login");
        return await client.PostAsync("/Login", Form(login, ("Username", username), ("Password", password)));
    }

    private static FormUrlEncodedContent Form(string html, params (string Key, string Value)[] fields)
    {
        var match = Regex.Match(html, "name=\"__RequestVerificationToken\"[^>]*value=\"([^\"]+)\"");
        Assert.True(match.Success, "Razor must emit a CSRF token.");
        var values = fields.ToDictionary(x => x.Key, x => x.Value);
        values["__RequestVerificationToken"] = WebUtility.HtmlDecode(match.Groups[1].Value);
        return new(values);
    }

    private sealed class Fixture : WebApplicationFactory<Program>
    {
        internal const string OwnOrder = "aaaaaaaaaaaaaaaaaaaaaaaa";
        internal const string OtherOrder = "bbbbbbbbbbbbbbbbbbbbbbbb";
        internal readonly MemoryTable Memory = new();
        internal readonly string Password = Guid.NewGuid().ToString("N") + "!aA1";
        internal string? TableEndpoint { get; init; } = "https://table.example.invalid";

        internal Fixture()
        {
            var hasher = new PasswordHasher<string>();
            foreach (var id in new[] { "customer-001", "operator-001" })
                Memory.Put(new TableEntity("accounts", id)
                {
                    ["DisplayName"] = "Isolated HTTP test account", ["Role"] = id.StartsWith("operator") ? "Operator" : "Customer",
                    ["PasswordHash"] = hasher.HashPassword(id, Password), ["Failures"] = 0,
                    ["LockedUntil"] = DateTimeOffset.UnixEpoch, ["Stamp"] = Guid.NewGuid().ToString("N")
                });
            Memory.Put(new TableEntity("store-001", "product-001")
            { ["Json"] = JsonSerializer.Serialize(new Product(1, "Synthetic test groceries", 320, 10, [])) });
            foreach (var (id, customer) in new[] { (OwnOrder, "customer-001"), (OtherOrder, "customer-002") })
                Memory.Put(new TableEntity("store-001", "order-" + id)
                {
                    ["CustomerId"] = customer,
                    ["Json"] = JsonSerializer.Serialize(new GroceryOrder(id, customer, [new(1, 1)],
                        "09:00-11:00", 320, [], "Draft", 0, 0, null, [], DateTimeOffset.UtcNow))
                });
        }

        internal HttpClient Client() => CreateClient(new()
        {
            BaseAddress = new Uri("https://localhost"), AllowAutoRedirect = false
        });

        protected override void ConfigureWebHost(IWebHostBuilder builder)
        {
            builder.UseContentRoot(Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "..",
                "src", "Woodgrove.Web")));
            builder.UseSetting("StorageTableEndpoint", TableEndpoint);
            builder.UseSetting("StorageBlobEndpoint", "https://blob.example.invalid");
            builder.UseSetting("FoundryProjectEndpoint", "https://foundry.example.invalid");
            builder.ConfigureTestServices(services =>
            {
                services.RemoveAll<TableServiceClient>();
                services.AddSingleton<TableServiceClient>(new MemoryTableService(Memory));
                services.RemoveAll<IDataProtectionProvider>();
                services.AddSingleton<IDataProtectionProvider>(new EphemeralDataProtectionProvider());
                services.PostConfigure<KeyManagementOptions>(options => options.XmlRepository = new TestKeyRepository());
                services.PostConfigure<AzureMonitorExporterOptions>(options =>
                {
                    options.ConnectionString =
                        "InstrumentationKey=00000000-0000-0000-0000-000000000000;IngestionEndpoint=https://telemetry.example.invalid";
                    options.Transport = new DiscardTelemetryTransport();
                    options.EnableLiveMetrics = false;
                    options.DisableOfflineStorage = true;
                });
                var worker = services.Single(x => x.ImplementationType == typeof(FulfillmentWorker));
                services.Remove(worker);
            });
        }
    }

    private sealed class DiscardTelemetryTransport : HttpPipelineTransport
    {
        public override Request CreateRequest() => HttpClientTransport.Shared.CreateRequest();
        public override void Process(HttpMessage message) => message.Response = new RawResponse();
        public override ValueTask ProcessAsync(HttpMessage message)
        {
            Process(message);
            return ValueTask.CompletedTask;
        }

    }

    private sealed class TestKeyRepository : IXmlRepository
    {
        private readonly List<XElement> elements = [];
        public IReadOnlyCollection<XElement> GetAllElements()
        {
            lock (elements) return elements.Select(x => new XElement(x)).ToArray();
        }
        public void StoreElement(XElement element, string friendlyName)
        {
            lock (elements) elements.Add(new XElement(element));
        }
    }
}
