using System.Security.Claims;

namespace CoffeeShop.Web.Services;

public sealed class StoreAccess
{
    public string[] Grants(ClaimsPrincipal user)
    {
        if (user.Identity?.IsAuthenticated != true || user.FindFirstValue("oid") is null
            || !user.IsInRole("StoreManager") && !user.IsInRole("AreaManager"))
            throw new UnauthorizedAccessException();
        var stores = user.FindAll("store").Select(claim => claim.Value).Distinct().ToArray();
        // A StoreManager cannot gain multi-store access through a configuration accident.
        if (!user.IsInRole("AreaManager") && stores.Length > 1) throw new UnauthorizedAccessException();
        return stores;
    }

    public void Demand(ClaimsPrincipal user, string storeId)
    {
        if (!System.Text.RegularExpressions.Regex.IsMatch(storeId, "^[0-9]{3}$")
            || !Grants(user).Contains(storeId)) throw new UnauthorizedAccessException();
    }
}
