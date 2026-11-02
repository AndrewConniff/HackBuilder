using System.Text.Json;
using Restaurant.Web.Models;

namespace Restaurant.Web.Services;

/// <summary>Versioned synthetic legacy reservations; never a connector to customer systems.</summary>
public sealed record LegacyDocument(int SchemaVersion, bool Synthetic, string Source, LegacyReservation[] Records);

/// <summary>A legacy reservation with a stable external identity and catalog-backed guest.</summary>
public sealed record LegacyReservation(string LegacyReferenceId, string Slot, int Floor, int Seats, string GuestId);

/// <summary>Durable import identity binding prevents moving one external record to a different slot on retry.</summary>
public sealed record ImportBinding(string id, string aggregateKey, string Type, string Digest);

/// <summary>A retained synthetic reservation result; access codes must remain in private local evidence.</summary>
public sealed record LegacyImportRecord(string LegacyReferenceId, string VisitId, string AccessCode, string Status);

/// <summary>A resumable import receipt distinguishing partial progress from a completed import.</summary>
public sealed record LegacyImportResult(int SchemaVersion, string Source, bool Synthetic, bool Completed,
    LegacyImportRecord[] Records);

/// <summary>Imports synthetic reservations using authoritative capacity, durable identity binding and ordinary outbox projection.</summary>
public sealed class LegacyImport(CosmosStore store, RestaurantService restaurant)
{
    /// <summary>Validates the entire document shape before writing any records.</summary>
    public static void Validate(LegacyDocument document)
    {
        if (document.SchemaVersion != 1 || !document.Synthetic || string.IsNullOrWhiteSpace(document.Source)
            || document.Source.Length > 64 || document.Records is null || document.Records.Length is < 1 or > 1250)
            throw new DomainException(400, "Use schemaVersion 1, synthetic true, a bounded source and 1-1250 records.");
        if (document.Records.Any(record => record is null || string.IsNullOrWhiteSpace(record.LegacyReferenceId)
            || record.LegacyReferenceId.Length > 64
            || document.Source.Length + record.LegacyReferenceId.Length + 1 > 128 || record.GuestId != "guest-001"
            || record.Floor is < 1 or > 5 || record.Seats is < 1 or > 12))
            throw new DomainException(400, "Each record requires a bounded external ID, catalog guest and valid floor/party.");
        if (document.Records.Select(record => record.LegacyReferenceId).Distinct(StringComparer.Ordinal).Count()
            != document.Records.Length)
            throw new DomainException(400, "Duplicate legacy identities in one import document are not allowed.");
        foreach (var record in document.Records) Rules.ValidateSlot(record.Slot);
    }

    /// <summary>Imports each identity idempotently; failures remain explicit and successful earlier records stay committed.</summary>
    public async Task Run(string path, string outputPath, CancellationToken token)
    {
        var document = JsonSerializer.Deserialize<LegacyDocument>(await File.ReadAllTextAsync(path, token),
            new JsonSerializerOptions(JsonSerializerDefaults.Web))
            ?? throw new DomainException(400, "Legacy document is empty.");
        Validate(document);
        var prior = File.Exists(outputPath)
            ? JsonSerializer.Deserialize<LegacyImportResult>(await File.ReadAllTextAsync(outputPath, token))
                ?? throw new InvalidDataException("Existing import receipt is invalid.")
            : new LegacyImportResult(1, document.Source, true, false, []);
        if (prior.SchemaVersion != 1 || prior.Source != document.Source || !prior.Synthetic)
            throw new InvalidDataException("Existing receipt belongs to a different source or schema.");
        var results = prior.Records.ToDictionary(item => item.LegacyReferenceId, StringComparer.Ordinal);
        await Save(false);
        foreach (var record in document.Records)
        {
            var reference = $"{document.Source}:{record.LegacyReferenceId}";
            var id = $"legacy-{Rules.Digest(reference).ToLowerInvariant()}";
            var digest = Rules.Digest(record);
            var binding = await CosmosStore.Read<ImportBinding>(store.Reporting, id, "legacy-import", token);
            if (binding is null)
                await store.Reporting.CreateItemAsync(new ImportBinding(id, "legacy-import", "legacy-binding", digest),
                    new("legacy-import"), cancellationToken: token);
            else if (binding.Value.Item.Digest != digest)
                throw new DomainException(409, $"Legacy record {record.LegacyReferenceId} changed; explicit migration required.");
            ReservationResult reservation;
            try
            {
                reservation = await restaurant.Reserve(new(record.Slot, record.Floor, record.Seats,
                    record.GuestId, id, reference), token);
            }
            catch (DomainException exception)
            {
                throw new DomainException(exception.Status,
                    $"Import stopped at {record.LegacyReferenceId}: {exception.Message} Earlier receipts remain in the output file.");
            }
            var retainedCode = results.GetValueOrDefault(record.LegacyReferenceId)?.AccessCode ?? string.Empty;
            results[record.LegacyReferenceId] = new(record.LegacyReferenceId, reservation.VisitId,
                string.IsNullOrEmpty(reservation.AccessCode) ? retainedCode : reservation.AccessCode, reservation.Status);
            await Save(false);
        }
        await Save(true);

        async Task Save(bool completed)
        {
            var temporary = outputPath + ".tmp";
            await File.WriteAllTextAsync(temporary, JsonSerializer.Serialize(
                new LegacyImportResult(1, document.Source, true, completed, results.Values.ToArray())), token);
            File.Move(temporary, outputPath, overwrite: true);
        }
    }
}
