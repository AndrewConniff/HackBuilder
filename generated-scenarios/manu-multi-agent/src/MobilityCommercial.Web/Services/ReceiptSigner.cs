using System.Security.Cryptography;
using System.Text.Json;
using Azure.Security.KeyVault.Keys.Cryptography;
using MobilityCommercial.Web.Models;

namespace MobilityCommercial.Web.Services;

internal interface IReceiptSigner
{
    Task<Receipt> SignAsync(ReviewPacket packet, CancellationToken cancellationToken);
    Task<bool> VerifyAsync(Receipt receipt, CancellationToken cancellationToken);
}

internal static class Canonical
{
    internal static byte[] Bytes<T>(T value)
    {
        using var stream = new MemoryStream();
        using (var writer = new Utf8JsonWriter(stream))
            Write(writer, JsonSerializer.SerializeToElement(value, Json.Options));
        return stream.ToArray();
    }

    private static void Write(Utf8JsonWriter writer, JsonElement element)
    {
        if (element.ValueKind == JsonValueKind.Object)
        {
            writer.WriteStartObject();
            foreach (var property in element.EnumerateObject().OrderBy(p => p.Name, StringComparer.Ordinal))
            {
                writer.WritePropertyName(property.Name);
                Write(writer, property.Value);
            }
            writer.WriteEndObject();
        }
        else if (element.ValueKind == JsonValueKind.Array)
        {
            writer.WriteStartArray();
            foreach (var item in element.EnumerateArray()) Write(writer, item);
            writer.WriteEndArray();
        }
        else element.WriteTo(writer);
    }

    internal static byte[] Digest(Receipt receipt, string expectedKeyId)
    {
        if (receipt.Algorithm != "PS256" || receipt.KeyId != expectedKeyId
            || receipt.CanonicalPayload.Length > 90000 || receipt.Signature.Length > 1000)
            throw new WorkflowException(400, "invalid_receipt");
        var payload = Bytes(receipt.Packet);
        if (Convert.ToBase64String(payload) != receipt.CanonicalPayload
            || Convert.ToHexStringLower(SHA256.HashData(payload)) != receipt.Sha256)
            throw new WorkflowException(400, "receipt_tampered");
        return SHA256.HashData(payload);
    }
}

internal sealed class KeyVaultReceiptSigner(CryptographyClient client, AppSettings settings) : IReceiptSigner
{
    public async Task<Receipt> SignAsync(ReviewPacket packet, CancellationToken cancellationToken)
    {
        var bytes = Canonical.Bytes(packet);
        var digest = SHA256.HashData(bytes);
        var result = await client.SignAsync(SignatureAlgorithm.PS256, digest, cancellationToken);
        if (result.KeyId != settings.KeyUri.AbsoluteUri)
            throw new WorkflowException(503, "signing_key_mismatch");
        return new(packet, Convert.ToBase64String(bytes), Convert.ToHexStringLower(digest),
            Convert.ToBase64String(result.Signature), result.KeyId, "PS256");
    }

    public async Task<bool> VerifyAsync(Receipt receipt, CancellationToken cancellationToken)
    {
        var digest = Canonical.Digest(receipt, settings.KeyUri.AbsoluteUri);
        byte[] signature;
        try { signature = Convert.FromBase64String(receipt.Signature); }
        catch (FormatException) { throw new WorkflowException(400, "invalid_receipt_signature"); }
        if (signature.Length != 256) throw new WorkflowException(400, "invalid_receipt_signature");
        var result = await client.VerifyAsync(SignatureAlgorithm.PS256, digest, signature, cancellationToken);
        return result.IsValid;
    }
}
