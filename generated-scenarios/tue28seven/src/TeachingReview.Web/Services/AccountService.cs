using Microsoft.AspNetCore.Identity;
using TeachingReview.Web.Models;

namespace TeachingReview.Web.Services;

internal sealed class AccountService(IStateStore store, ILogger<AccountService> logger)
{
    private readonly PasswordHasher<Teacher> hasher = new();
    private readonly Teacher dummy = new(0, "unavailable", string.Empty, string.Empty, string.Empty);
    private readonly string dummyHash = new PasswordHasher<Teacher>().HashPassword(
        new(0, "unavailable", string.Empty, string.Empty, string.Empty), Guid.NewGuid().ToString("N"));

    internal async Task<Teacher?> LoginAsync(string username, string password, CancellationToken cancellationToken)
    {
        var snapshot = await store.ReadAsync(cancellationToken);
        var teacher = snapshot.State.Teachers.SingleOrDefault(x => x.Username == username);
        if (teacher is null)
        {
            hasher.VerifyHashedPassword(dummy, dummyHash, password);
            logger.LogWarning("Rejected login for unknown account");
            return null;
        }
        if (teacher.LockedUntil > DateTimeOffset.UtcNow)
        {
            logger.LogWarning("Rejected login for locked account {AccountId}", teacher.Id);
            return null;
        }
        var valid = hasher.VerifyHashedPassword(teacher, teacher.PasswordHash, password)
            != PasswordVerificationResult.Failed;
        var failures = teacher.LockedUntil.HasValue ? 0 : teacher.FailedLogins;
        var updated = valid ? teacher with { FailedLogins = 0, LockedUntil = null }
            : teacher with
            {
                FailedLogins = failures + 1,
                LockedUntil = failures + 1 >= 5 ? DateTimeOffset.UtcNow.AddMinutes(15) : null
            };
        snapshot.State.Teachers[snapshot.State.Teachers.IndexOf(teacher)] = updated;
        await store.WriteAsync(snapshot.State, snapshot.Revision, cancellationToken);
        if (!valid) logger.LogWarning("Rejected password for account {AccountId}", teacher.Id);
        return valid ? updated : null;
    }
}
