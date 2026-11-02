using Microsoft.AspNetCore.Mvc.RazorPages;

namespace MobilityCommercial.Web.Pages;

/// <summary>Displays the synthetic Sales-to-Marketing workflow shell.</summary>
public sealed class IndexModel : PageModel
{
    /// <summary>Renders the shell; authenticated API calls load the versioned evidence separately.</summary>
    public void OnGet() { }
}
