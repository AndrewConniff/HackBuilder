using System.IdentityModel.Tokens.Jwt;
using System.Net;
using System.Net.Http.Headers;
using System.Security.Claims;
using System.Security.Cryptography;
using HospitalityFeedback.Web.Services;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.IdentityModel.Protocols;
using Microsoft.IdentityModel.Protocols.OpenIdConnect;
using Microsoft.IdentityModel.Tokens;
using Xunit;

namespace HospitalityFeedback.Tests;

/// <summary>Exercise actual JWT middleware and the operator policy using local signing keys.</summary>
public sealed class AuthenticationTests : IDisposable
{
    private const string Tenant = "11111111-1111-1111-1111-111111111111";
    private const string Audience = "22222222-2222-2222-2222-222222222222";
    private const string Operator = "33333333-3333-3333-3333-333333333333";
    private readonly RSA rsa = RSA.Create(2048);

    /// <summary>Verify scope and role access plus all required authentication denial cases.</summary>
    [Theory]
    [InlineData("scope", 400)]
    [InlineData("role", 400)]
    [InlineData("missing", 401)]
    [InlineData("audience", 401)]
    [InlineData("issuer", 401)]
    [InlineData("expired", 401)]
    [InlineData("tenant", 403)]
    [InlineData("operator", 403)]
    [InlineData("permission", 403)]
    [InlineData("signature", 401)]
    public async Task ApiRequiresValidTenantAudienceOperatorAndPermission(string mode, int expected)
    {
        var key = new RsaSecurityKey(rsa) { KeyId = "local-test-key" };
        using var factory = new WebApplicationFactory<Program>().WithWebHostBuilder(builder =>
        {
            builder.UseEnvironment("Development");
            builder.UseSetting("Feedback:UseAzurite", "false");
            builder.UseSetting("Feedback:LocalAnonymous", "false");
            builder.UseSetting("Feedback:TenantId", Tenant);
            builder.UseSetting("Feedback:Audience", Audience);
            builder.UseSetting("Feedback:OperatorObjectIds:0", Operator);
            builder.UseSetting("Feedback:BlobEndpoint", "https://unused.blob.core.windows.net");
            builder.UseSetting("Feedback:QueueEndpoint", "https://unused.queue.core.windows.net");
            builder.ConfigureServices(services =>
            {
                // Isolate JWT/policy evaluation from Storage, Entra discovery and cloud credentials.
                var worker = services.Single(d => d.ServiceType == typeof(IHostedService)
                    && d.ImplementationType == typeof(QueueWorker));
                services.Remove(worker);
                services.PostConfigure<JwtBearerOptions>(JwtBearerDefaults.AuthenticationScheme, options =>
                {
                    options.Configuration = new OpenIdConnectConfiguration
                    {
                        Issuer = $"https://login.microsoftonline.com/{Tenant}/v2.0"
                    };
                    options.Configuration.SigningKeys.Add(key);
                    options.ConfigurationManager =
                        new StaticConfigurationManager<OpenIdConnectConfiguration>(options.Configuration);
                });
            });
        });
        using var client = factory.CreateClient();
        if (mode != "missing")
        {
            using var wrongKey = RSA.Create(2048);
            var credentials = new SigningCredentials(
                mode == "signature" ? new RsaSecurityKey(wrongKey) : key, SecurityAlgorithms.RsaSha256);
            var claims = new List<Claim>
            {
                new("tid", mode == "tenant" ? Guid.Empty.ToString() : Tenant),
                new("oid", mode == "operator" ? Guid.Empty.ToString() : Operator)
            };
            if (mode == "role") claims.Add(new("roles", "Feedback.Operator"));
            else if (mode != "permission") claims.Add(new("scp", "openid access_as_user"));
            var token = new JwtSecurityToken(
                mode == "issuer" ? "https://invalid.example/v2.0" : $"https://login.microsoftonline.com/{Tenant}/v2.0",
                mode == "audience" ? Guid.Empty.ToString() : Audience, claims,
                DateTime.UtcNow.AddHours(-2),
                mode == "expired" ? DateTime.UtcNow.AddHours(-1) : DateTime.UtcNow.AddMinutes(5), credentials);
            client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue(
                "Bearer", new JwtSecurityTokenHandler().WriteToken(token));
        }
        // This route validates its ID before any Storage operation, but after authorization.
        using var response = await client.GetAsync("/api/status/invalid-id");
        Assert.Equal((HttpStatusCode)expected, response.StatusCode);
    }

    /// <summary>Release the local signing key.</summary>
    public void Dispose() => rsa.Dispose();
}
