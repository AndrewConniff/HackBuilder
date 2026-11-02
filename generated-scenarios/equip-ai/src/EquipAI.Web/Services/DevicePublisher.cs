using System.Diagnostics;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.Text;
using System.Text.Json;
using EquipAI.Web.Models;
using Microsoft.Azure.Devices.Client;

namespace EquipAI.Web.Services;

internal static class DevicePublisher
{
    internal static void Prepare(IConfiguration config)
    {
        var deviceId = AgentContract.Required(config, "DeviceId");
        if (!new Inventory(Directory.GetCurrentDirectory()).Equipment.Any(item => item.DeviceId == deviceId))
            throw new InvalidDataException("Device must belong to this scenario's equipment inventory.");
        var directory = AgentContract.Required(config, "PrivateDeviceDirectory");
        Directory.CreateDirectory(directory);
        var metadata = Path.Combine(directory, $"{deviceId}.json");
        if (File.Exists(metadata)) { Console.WriteLine("Existing private fixture certificate retained."); return; }
        using var key = RSA.Create(2048);
        var request = new CertificateRequest($"CN={deviceId}", key, HashAlgorithmName.SHA256, RSASignaturePadding.Pkcs1);
        request.CertificateExtensions.Add(new X509KeyUsageExtension(X509KeyUsageFlags.DigitalSignature, true));
        request.CertificateExtensions.Add(new X509EnhancedKeyUsageExtension(
            new OidCollection { new Oid("1.3.6.1.5.5.7.3.2") }, false));
        using var certificate = request.CreateSelfSigned(DateTimeOffset.UtcNow.AddMinutes(-5), DateTimeOffset.UtcNow.AddDays(7));
        var password = Convert.ToHexString(RandomNumberGenerator.GetBytes(24));
        var path = Path.Combine(directory, $"{deviceId}.pfx");
        File.WriteAllBytes(path, certificate.Export(X509ContentType.Pfx, password));
        File.WriteAllText(metadata, JsonSerializer.Serialize(new
        {
            deviceId, certificatePath = path, password, thumbprint = certificate.Thumbprint,
            owner = "equip-ai-synthetic-acceptance", expiresAtUtc = certificate.NotAfter.ToUniversalTime()
        }));
        Console.WriteLine(JsonSerializer.Serialize(new { deviceId, thumbprint = certificate.Thumbprint }));
    }

    internal static Reading[] Fixture(string deviceId, DateTimeOffset now, string? mode)
    {
        Reading Create(int age, long sequence, double temperature, double vibration, double pressure) =>
            new(1, Guid.NewGuid().ToString("N"), deviceId, now.AddMinutes(-age), sequence,
                temperature, vibration, pressure, "running");
        return mode switch
        {
            "trend" => [Create(10, 0, 70, 3, 8.2), Create(0, 1, 73, 6.1, 8),
                Create(121, 2, 99, 90, 6)],
            "stale" => [Create(6, 0, 71, 2, 8.2)],
            null or "" => [Create(0, now.ToUnixTimeSeconds(), 73, 6.1, 8.2)],
            _ => throw new InvalidDataException("Unknown fixture mode.")
        };
    }

    internal static async Task PublishAsync(IConfiguration config, CancellationToken token)
    {
        var deviceId = AgentContract.Required(config, "DeviceId");
        var hub = AgentContract.Required(config, "IotHubHostName");
        var certificate = X509CertificateLoader.LoadPkcs12FromFile(
            AgentContract.Required(config, "DeviceCertificate"),
            config["DeviceCertificatePassword"],
            OperatingSystem.IsWindows() ? X509KeyStorageFlags.UserKeySet : X509KeyStorageFlags.EphemeralKeySet);
        using (certificate)
        using (var client = DeviceClient.Create(hub,
            new DeviceAuthenticationWithX509Certificate(deviceId, certificate), TransportType.Mqtt_Tcp_Only))
        {
            await client.OpenAsync(token);
            if (config["FixtureMode"] == "burst")
            {
                await PublishBurstAsync(client, deviceId, token);
                return;
            }
            var readings = Fixture(deviceId, DateTimeOffset.UtcNow, config["FixtureMode"]);
            foreach (var reading in readings)
            {
                using var message = new Message(Encoding.UTF8.GetBytes(JsonSerializer.Serialize(reading, TelemetryEngine.Json)))
                {
                    ContentType = "application/json", ContentEncoding = "utf-8", MessageId = reading.MessageId
                };
                await client.SendEventAsync(message, token);
            }
            Console.WriteLine(JsonSerializer.Serialize(new { status = "published", deviceId, readings }));
        }
    }

    private static async Task PublishBurstAsync(DeviceClient client, string deviceId, CancellationToken token)
    {
        var warmup = new Reading(1, Guid.NewGuid().ToString("N"), deviceId, DateTimeOffset.UtcNow,
            0, 73, 6.1, 8, "running");
        var readings = new List<Reading> { warmup };
        var sends = new List<Task>();
        var buckets = new int[60];
        using var slots = new SemaphoreSlim(128);
        await slots.WaitAsync(token);
        await SendAsync(warmup);
        var timer = Stopwatch.StartNew();
        for (int index = 0; index < 3000; index++)
        {
            await WaitUntilAsync(TimeSpan.FromMilliseconds(index / 50 * 1000 + 200 + index % 50 * 10));
            await slots.WaitAsync(token);
            var bucket = (int)timer.Elapsed.TotalSeconds;
            if (bucket < buckets.Length) buckets[bucket]++;
            var reading = new Reading(1, Guid.NewGuid().ToString("N"), deviceId, DateTimeOffset.UtcNow,
                index, 73, 6.1, 8, "running");
            readings.Add(reading);
            sends.Add(SendAsync(reading));
        }
        await Task.WhenAll(sends);
        await WaitUntilAsync(TimeSpan.FromSeconds(60));
        Console.WriteLine(JsonSerializer.Serialize(new
        {
            status = "published", deviceId, readings, offeredPerSecond = buckets,
            elapsedSeconds = timer.Elapsed.TotalSeconds, acknowledgedMessages = readings.Count - 1,
            warmupAcknowledgedMessages = 1
        }));

        async Task WaitUntilAsync(TimeSpan due)
        {
            TimeSpan delay;
            while ((delay = due - timer.Elapsed) > TimeSpan.Zero)
                await Task.Delay(delay < TimeSpan.FromMilliseconds(1) ? TimeSpan.FromMilliseconds(1) : delay, token);
        }

        async Task SendAsync(Reading reading)
        {
            try
            {
                using var message = new Message(Encoding.UTF8.GetBytes(JsonSerializer.Serialize(reading, TelemetryEngine.Json)))
                {
                    ContentType = "application/json", ContentEncoding = "utf-8", MessageId = reading.MessageId
                };
                await client.SendEventAsync(message, token);
            }
            finally { slots.Release(); }
        }
    }
}
